"""Content migration tools for Canvas API.

Provides tools for copying content (modules, assignments, files, etc.)
between Canvas courses using the Content Migrations API.
"""

import asyncio
from typing import Union

from mcp.server.fastmcp import FastMCP

from ..core.cache import get_course_code, get_course_id
from ..core.client import make_canvas_request, poll_canvas_progress
from ..core.validation import validate_params

VALID_CONTENT_TYPES = {
    "folders",
    "files",
    "attachments",
    "quizzes",
    "assignments",
    "announcements",
    "calendar_events",
    "discussion_topics",
    "modules",
    "module_items",
    "pages",
    "rubrics",
}


def register_content_migration_tools(mcp: FastMCP):
    """Register content migration tools."""

    @mcp.tool()
    @validate_params
    async def copy_course_content(
        source_course: Union[str, int],
        destination_courses: str,
        content_type: str,
        content_ids: str,
    ) -> str:
        """Copy specific content from one course to one or more destination courses.

        Uses the Canvas Content Migrations API with course_copy_importer to
        selectively copy modules, assignments, files, pages, etc.

        Args:
            source_course: Source course ID or course code
            destination_courses: Comma-separated destination course IDs or codes
            content_type: Type of content to copy. One of: modules, assignments,
                files, attachments, folders, quizzes, announcements,
                calendar_events, discussion_topics, module_items, pages, rubrics
            content_ids: Comma-separated IDs of the specific items to copy
        """
        if content_type not in VALID_CONTENT_TYPES:
            return (
                f"Invalid content_type '{content_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_CONTENT_TYPES))}"
            )

        source_id = await get_course_id(source_course)
        source_display = await get_course_code(source_id) or source_course

        ids_list = [s.strip() for s in str(content_ids).split(",") if s.strip()]
        if not ids_list:
            return "No content_ids provided."

        dest_strings = [s.strip() for s in str(destination_courses).split(",") if s.strip()]
        if not dest_strings:
            return "No destination_courses provided."

        # Resolve all destination course IDs
        dest_courses = []
        for d in dest_strings:
            dest_id = await get_course_id(d)
            dest_display = await get_course_code(dest_id) or d
            dest_courses.append((dest_id, dest_display))

        # Build the migration payload
        payload = {
            "migration_type": "course_copy_importer",
            "settings": {"source_course_id": str(source_id)},
            "select": {content_type: ids_list},
        }

        # Start migrations concurrently
        async def start_migration(dest_id, dest_display):
            response = await make_canvas_request(
                "post",
                f"/courses/{dest_id}/content_migrations",
                data=payload,
            )
            if isinstance(response, dict) and "error" in response:
                return {
                    "dest_id": dest_id,
                    "dest_display": dest_display,
                    "error": response["error"],
                }

            migration_id = response.get("id")
            progress_url = response.get("progress_url", "")

            # Extract progress ID from URL
            progress_id = None
            if progress_url:
                progress_id = progress_url.rstrip("/").split("/")[-1]
            elif migration_id:
                # Fall back to polling the migration endpoint
                progress_id = None

            return {
                "dest_id": dest_id,
                "dest_display": dest_display,
                "migration_id": migration_id,
                "progress_id": progress_id,
            }

        migration_tasks = [
            start_migration(dest_id, dest_display)
            for dest_id, dest_display in dest_courses
        ]
        migration_results = await asyncio.gather(*migration_tasks)

        # Separate successes from immediate failures
        to_poll = []
        errors = []
        for r in migration_results:
            if "error" in r:
                errors.append(r)
            elif r.get("progress_id"):
                to_poll.append(r)
            else:
                # No progress_id available, poll the migration endpoint directly
                to_poll.append(r)

        # Poll all migrations concurrently
        async def poll_migration(info):
            if info.get("progress_id"):
                result = await poll_canvas_progress(
                    info["progress_id"], max_wait_seconds=180.0
                )
                info["poll_result"] = result
            else:
                # Poll via migration endpoint
                migration_id = info.get("migration_id")
                dest_id = info["dest_id"]
                import time

                start = time.monotonic()
                while time.monotonic() - start < 180.0:
                    resp = await make_canvas_request(
                        "get",
                        f"/courses/{dest_id}/content_migrations/{migration_id}",
                    )
                    state = resp.get("workflow_state", "")
                    if state in ("completed", "failed"):
                        info["poll_result"] = {
                            "completed": state == "completed",
                            "workflow_state": state,
                            "message": resp.get("migration_issues", []),
                        }
                        break
                    await asyncio.sleep(3)
                else:
                    info["poll_result"] = {
                        "completed": False,
                        "workflow_state": "timeout",
                        "message": "Polling timed out after 180s",
                    }
            return info

        if to_poll:
            poll_tasks = [poll_migration(info) for info in to_poll]
            polled = await asyncio.gather(*poll_tasks)
        else:
            polled = []

        # Build result summary
        result_lines = [
            f"Content Migration: {content_type} from {source_display}",
            f"Items: {', '.join(ids_list)}",
            f"Destinations: {len(dest_courses)}",
            "",
        ]

        succeeded = 0
        failed = 0

        for info in polled:
            pr = info.get("poll_result", {})
            status = "completed" if pr.get("completed") else pr.get("workflow_state", "unknown")
            if pr.get("completed"):
                succeeded += 1
                result_lines.append(f"  {info['dest_display']}: completed")
            else:
                failed += 1
                msg = pr.get("message", "")
                result_lines.append(f"  {info['dest_display']}: {status} - {msg}")

        for info in errors:
            failed += 1
            result_lines.append(f"  {info['dest_display']}: ERROR - {info['error']}")

        result_lines.append("")
        result_lines.append(f"Summary: {succeeded} succeeded, {failed} failed")

        return "\n".join(result_lines)
