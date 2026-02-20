"""Discussion analytics MCP tools for Canvas API."""

import csv
import io
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..core.cache import get_course_code, get_course_id
from ..core.client import fetch_all_paginated_results, make_canvas_request
from ..core.dates import format_date
from ..core.logging import log_warning
from ..core.validation import validate_params


def register_discussion_analytics_tools(mcp: FastMCP) -> None:
    """Register discussion analytics MCP tools."""

    @mcp.tool()
    @validate_params
    async def get_discussion_participation_summary(
        course_identifier: str | int,
        topic_id: str | int
    ) -> str:
        """Get a participation summary for a discussion topic, showing who posted, replied, and who is silent.

        Cross-references enrolled students with discussion entries to identify
        participation levels. Returns student IDs ready for bulk messaging.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            topic_id: The Canvas discussion topic ID
        """
        course_id = await get_course_id(course_identifier)

        # Fetch enrolled students
        students = await fetch_all_paginated_results(
            f"/courses/{course_id}/users",
            {"enrollment_type[]": "student", "per_page": 100}
        )

        if isinstance(students, dict) and "error" in students:
            return f"Error fetching students: {students['error']}"

        # Fetch discussion entries
        entries = await fetch_all_paginated_results(
            f"/courses/{course_id}/discussion_topics/{topic_id}/entries",
            {"per_page": 100}
        )

        if isinstance(entries, dict) and "error" in entries:
            return f"Error fetching discussion entries: {entries['error']}"

        # Fetch topic details for context
        topic_response = await make_canvas_request(
            "get", f"/courses/{course_id}/discussion_topics/{topic_id}"
        )
        topic_title = "Unknown Topic"
        if not isinstance(topic_response, dict) or "error" not in topic_response:
            topic_title = topic_response.get("title", "Unknown Topic")

        # Build participation map: user_id -> {posts: int, replies: int}
        participation: dict[str, dict[str, int]] = {}
        entries_list = entries if isinstance(entries, list) else []

        for entry in entries_list:
            user_id = str(entry.get("user_id", ""))
            if not user_id:
                continue
            if user_id not in participation:
                participation[user_id] = {"posts": 0, "replies": 0}
            participation[user_id]["posts"] += 1

            # Count replies to this entry
            replies = entry.get("recent_replies", [])
            for reply in replies:
                reply_user_id = str(reply.get("user_id", ""))
                if not reply_user_id:
                    continue
                if reply_user_id not in participation:
                    participation[reply_user_id] = {"posts": 0, "replies": 0}
                participation[reply_user_id]["replies"] += 1

        # Also fetch replies via the view endpoint for more complete data
        try:
            view_response = await make_canvas_request(
                "get", f"/courses/{course_id}/discussion_topics/{topic_id}/view"
            )
            if not isinstance(view_response, dict) or "error" not in view_response:
                for view_entry in view_response.get("view", []):
                    for reply in view_entry.get("replies", []):
                        reply_user_id = str(reply.get("user_id", ""))
                        if not reply_user_id:
                            continue
                        if reply_user_id not in participation:
                            participation[reply_user_id] = {"posts": 0, "replies": 0}
                        # Only count if not already counted
                        if participation[reply_user_id]["replies"] == 0:
                            participation[reply_user_id]["replies"] += 1
        except Exception as e:
            log_warning("Failed to fetch discussion view for participation", exc=e)

        # Categorize students
        student_list = students if isinstance(students, list) else []
        student_map = {str(s.get("id", "")): s.get("name", "Unknown") for s in student_list}

        full_participants = []  # Posted AND replied
        posters_only = []       # Posted but no replies
        repliers_only = []      # Replied but no posts
        silent = []             # No participation at all

        for student_id, student_name in student_map.items():
            p = participation.get(student_id, {"posts": 0, "replies": 0})
            has_posts = p["posts"] > 0
            has_replies = p["replies"] > 0

            if has_posts and has_replies:
                full_participants.append((student_id, student_name, p))
            elif has_posts:
                posters_only.append((student_id, student_name, p))
            elif has_replies:
                repliers_only.append((student_id, student_name, p))
            else:
                silent.append((student_id, student_name))

        # Format output
        course_display = await get_course_code(course_id) or course_identifier
        total_students = len(student_map)
        total_participants = total_students - len(silent)

        result = f"Discussion Participation Summary\n"
        result += f"Course: {course_display}\n"
        result += f"Discussion: {topic_title} (ID: {topic_id})\n\n"

        result += f"Overview: {total_participants}/{total_students} students participated "
        result += f"({total_participants / total_students * 100:.0f}%)\n" if total_students > 0 else "(0%)\n"
        result += f"  Full participation (post + reply): {len(full_participants)}\n"
        result += f"  Posted only: {len(posters_only)}\n"
        result += f"  Replied only: {len(repliers_only)}\n"
        result += f"  Silent (no participation): {len(silent)}\n\n"

        if full_participants:
            result += "Full Participants:\n"
            for sid, name, p in full_participants:
                result += f"  - {name} (ID: {sid}) - {p['posts']} posts, {p['replies']} replies\n"
            result += "\n"

        if posters_only:
            result += "Posted Only (no replies):\n"
            for sid, name, p in posters_only:
                result += f"  - {name} (ID: {sid}) - {p['posts']} posts\n"
            result += "\n"

        if repliers_only:
            result += "Replied Only (no original post):\n"
            for sid, name, p in repliers_only:
                result += f"  - {name} (ID: {sid}) - {p['replies']} replies\n"
            result += "\n"

        if silent:
            result += "Silent Students (no participation):\n"
            silent_ids = []
            for sid, name in silent:
                result += f"  - {name} (ID: {sid})\n"
                silent_ids.append(sid)
            result += f"\nSilent student IDs (for bulk messaging): {','.join(silent_ids)}\n"

        return result

    @mcp.tool()
    @validate_params
    async def grade_discussion_participation(
        course_identifier: str | int,
        topic_id: str | int,
        assignment_id: str | int,
        points_for_post: float = 5.0,
        points_for_reply: float = 3.0,
        max_points: float | None = None,
        dry_run: bool = True
    ) -> str:
        """Auto-grade discussion participation based on post and reply counts.

        Calculates grades based on participation and posts them to an assignment.
        Set dry_run=False to actually submit grades.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            topic_id: The Canvas discussion topic ID
            assignment_id: The assignment ID to post grades to
            points_for_post: Points awarded per original post (default: 5.0)
            points_for_reply: Points awarded per reply (default: 3.0)
            max_points: Maximum total points (default: use assignment's points_possible)
            dry_run: If True (default), preview grades without submitting
        """
        course_id = await get_course_id(course_identifier)

        # Get assignment details for max points
        assignment = await make_canvas_request(
            "get", f"/courses/{course_id}/assignments/{assignment_id}"
        )
        if isinstance(assignment, dict) and "error" in assignment:
            return f"Error fetching assignment: {assignment['error']}"

        points_possible = max_points or assignment.get("points_possible", 10)

        # Fetch enrolled students
        students = await fetch_all_paginated_results(
            f"/courses/{course_id}/users",
            {"enrollment_type[]": "student", "per_page": 100}
        )
        if isinstance(students, dict) and "error" in students:
            return f"Error fetching students: {students['error']}"

        # Fetch discussion entries
        entries = await fetch_all_paginated_results(
            f"/courses/{course_id}/discussion_topics/{topic_id}/entries",
            {"per_page": 100}
        )
        if isinstance(entries, dict) and "error" in entries:
            return f"Error fetching entries: {entries['error']}"

        # Build participation counts
        participation: dict[str, dict[str, int]] = {}
        entries_list = entries if isinstance(entries, list) else []

        for entry in entries_list:
            user_id = str(entry.get("user_id", ""))
            if not user_id:
                continue
            if user_id not in participation:
                participation[user_id] = {"posts": 0, "replies": 0}
            participation[user_id]["posts"] += 1

            for reply in entry.get("recent_replies", []):
                reply_user_id = str(reply.get("user_id", ""))
                if not reply_user_id:
                    continue
                if reply_user_id not in participation:
                    participation[reply_user_id] = {"posts": 0, "replies": 0}
                participation[reply_user_id]["replies"] += 1

        # Calculate grades
        student_list = students if isinstance(students, list) else []
        grades: dict[str, dict[str, Any]] = {}

        for student in student_list:
            student_id = str(student.get("id", ""))
            student_name = student.get("name", "Unknown")
            p = participation.get(student_id, {"posts": 0, "replies": 0})

            raw_score = (p["posts"] * points_for_post) + (p["replies"] * points_for_reply)
            capped_score = min(raw_score, points_possible)

            grades[student_id] = {
                "name": student_name,
                "posts": p["posts"],
                "replies": p["replies"],
                "raw_score": raw_score,
                "final_score": capped_score
            }

        # Format results
        course_display = await get_course_code(course_id) or course_identifier
        result = f"{'DRY RUN - ' if dry_run else ''}Discussion Participation Grading\n"
        result += f"Course: {course_display}\n"
        result += f"Assignment: {assignment.get('name', 'Unknown')} (ID: {assignment_id})\n"
        result += f"Points: {points_for_post}/post, {points_for_reply}/reply, max {points_possible}\n\n"

        result += f"{'Name':<30} {'Posts':<6} {'Replies':<8} {'Score':<8}\n"
        result += "-" * 55 + "\n"

        for _sid, g in sorted(grades.items(), key=lambda x: x[1]["final_score"], reverse=True):
            result += f"{g['name']:<30} {g['posts']:<6} {g['replies']:<8} {g['final_score']:<8.1f}\n"

        if dry_run:
            result += f"\nDry run complete. Set dry_run=False to submit {len(grades)} grades."
            return result

        # Submit grades
        successful = 0
        failed = 0
        for student_id, g in grades.items():
            response = await make_canvas_request(
                "put",
                f"/courses/{course_id}/assignments/{assignment_id}/submissions/{student_id}",
                data={
                    "submission": {
                        "posted_grade": str(g["final_score"])
                    },
                    "comment": {
                        "text_comment": f"Discussion participation: {g['posts']} posts, {g['replies']} replies"
                    }
                }
            )
            if isinstance(response, dict) and "error" in response:
                failed += 1
            else:
                successful += 1

        result += f"\nGrading complete: {successful} submitted, {failed} failed."
        return result

    @mcp.tool()
    @validate_params
    async def export_discussion_data(
        course_identifier: str | int,
        topic_id: str | int,
        format: str = "csv"
    ) -> str:
        """Export discussion data including all entries and replies.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            topic_id: The Canvas discussion topic ID
            format: Export format - "csv" (default) or "summary"
        """
        course_id = await get_course_id(course_identifier)

        # Fetch topic details
        topic = await make_canvas_request(
            "get", f"/courses/{course_id}/discussion_topics/{topic_id}"
        )
        topic_title = "Unknown"
        if not isinstance(topic, dict) or "error" not in topic:
            topic_title = topic.get("title", "Unknown")

        # Fetch all entries
        entries = await fetch_all_paginated_results(
            f"/courses/{course_id}/discussion_topics/{topic_id}/entries",
            {"per_page": 100}
        )
        if isinstance(entries, dict) and "error" in entries:
            return f"Error fetching entries: {entries['error']}"

        entries_list = entries if isinstance(entries, list) else []

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["entry_id", "user_id", "user_name", "type", "parent_entry_id", "created_at", "message_preview"])

            for entry in entries_list:
                msg = entry.get("message", "")
                msg_clean = re.sub(r'<[^>]+>', '', msg)[:200] if msg else ""

                writer.writerow([
                    entry.get("id"),
                    entry.get("user_id"),
                    entry.get("user_name", "Unknown"),
                    "post",
                    "",
                    entry.get("created_at", ""),
                    msg_clean
                ])

                for reply in entry.get("recent_replies", []):
                    reply_msg = reply.get("message", "")
                    reply_clean = re.sub(r'<[^>]+>', '', reply_msg)[:200] if reply_msg else ""

                    writer.writerow([
                        reply.get("id"),
                        reply.get("user_id"),
                        reply.get("user_name", "Unknown"),
                        "reply",
                        entry.get("id"),
                        reply.get("created_at", ""),
                        reply_clean
                    ])

            course_display = await get_course_code(course_id) or course_identifier
            return f"Discussion Export: '{topic_title}' in {course_display}\n\n{output.getvalue()}"

        else:
            # Summary format
            total_entries = len(entries_list)
            total_replies = sum(len(e.get("recent_replies", [])) for e in entries_list)
            unique_users = set()
            for e in entries_list:
                if e.get("user_id"):
                    unique_users.add(str(e["user_id"]))
                for r in e.get("recent_replies", []):
                    if r.get("user_id"):
                        unique_users.add(str(r["user_id"]))

            course_display = await get_course_code(course_id) or course_identifier
            result = f"Discussion Summary: '{topic_title}' in {course_display}\n\n"
            result += f"Total posts: {total_entries}\n"
            result += f"Total replies: {total_replies}\n"
            result += f"Total interactions: {total_entries + total_replies}\n"
            result += f"Unique participants: {len(unique_users)}\n"
            return result
