"""Assignment analytics MCP tools for Canvas API."""

import datetime
import re
from statistics import StatisticsError, mean, median, stdev
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..core.anonymization import anonymize_response_data
from ..core.cache import get_course_code, get_course_id
from ..core.client import fetch_all_paginated_results, make_canvas_request
from ..core.dates import format_date, format_datetime_compact
from ..core.logging import log_error
from ..core.response_formatter import (
    Verbosity,
    format_header,
    format_response,
    format_stats,
    get_verbosity,
)
from ..core.validation import validate_params


def register_assignment_analytics_tools(mcp: FastMCP) -> None:
    """Register assignment analytics MCP tools."""

    @mcp.tool()
    @validate_params
    async def list_submissions(
        course_identifier: str | int,
        assignment_id: str | int,
        verbosity: str | None = None
    ) -> str:
        """List submissions for a specific assignment.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
            verbosity: Output format - "compact" (default, token-efficient), "standard" (readable), or "verbose" (detailed)
        """
        course_id = await get_course_id(course_identifier)

        # Determine verbosity level
        if verbosity:
            try:
                v = Verbosity(verbosity.lower())
            except ValueError:
                v = get_verbosity()
        else:
            v = get_verbosity()

        # Ensure assignment_id is a string
        assignment_id_str = str(assignment_id)

        params = {
            "per_page": 100,
            "include[]": "submission_comments"
        }

        submissions = await fetch_all_paginated_results(
            f"/courses/{course_id}/assignments/{assignment_id_str}/submissions", params
        )

        if isinstance(submissions, dict) and "error" in submissions:
            return f"Error fetching submissions: {submissions['error']}"

        if not submissions:
            return f"No submissions found for assignment {assignment_id}."

        # Anonymize submission data to protect student privacy
        try:
            submissions = anonymize_response_data(submissions, data_type="submissions")
        except Exception as e:
            log_error(
                "Failed to anonymize submission data",
                exc=e,
                course_id=course_id,
                assignment_id=assignment_id
            )
            # Continue with original data for functionality

        # Try to get the course code for display
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)

        if v == Verbosity.COMPACT:
            # Token-efficient format: pipe-delimited
            header = format_header("sub", f"{assignment_id}|{course_display}", v)
            items = []
            for submission in submissions:
                user_id = submission.get("user_id")
                submitted_at = format_datetime_compact(submission.get("submitted_at"))
                score = submission.get("score")
                score_str = f"{score:.1f}" if score is not None else "-"
                late = "L" if submission.get("late") else ""
                missing = "M" if submission.get("missing") else ""
                attempt = submission.get("attempt") or 0
                redo = "R" if submission.get("redo_request") else ""
                flags = "".join(filter(None, [late, missing, redo]))
                comments = submission.get("submission_comments", [])
                comment_count = len(comments) if comments else 0
                items.append(f"{user_id}|{submitted_at}|{score_str}|att:{attempt}|{flags}|c:{comment_count}")

            body = "\n".join(items)
            return format_response(header, body, v)

        else:
            # Standard/verbose format with labels
            submissions_info = []
            for submission in submissions:
                user_id = submission.get("user_id")
                submitted_at = submission.get("submitted_at", "Not submitted")
                score = submission.get("score", "Not graded")
                grade = submission.get("grade", "Not graded")
                late = submission.get("late", False)
                missing = submission.get("missing", False)
                attempt = submission.get("attempt") or 0
                redo_request = submission.get("redo_request", False)
                late_policy = submission.get("late_policy_status") or "none"
                comments = submission.get("submission_comments", [])
                comment_count = len(comments) if comments else 0

                lines = [
                    f"User ID: {user_id}",
                    f"Submitted: {submitted_at}",
                    f"Score: {score}",
                    f"Grade: {grade}",
                    f"Attempt: {attempt}",
                ]
                if late:
                    lines.append("Late: Yes")
                if missing:
                    lines.append("Missing: Yes")
                if redo_request:
                    lines.append("Redo Requested: Yes")
                if late_policy != "none":
                    lines.append(f"Late Policy: {late_policy}")
                if comment_count > 0:
                    lines.append(f"Comments: {comment_count}")
                lines.append("")  # blank separator
                submissions_info.append("\n".join(lines))

            return f"Submissions for Assignment {assignment_id} in course {course_display}:\n\n" + "\n".join(submissions_info)

    @mcp.tool()
    @validate_params
    async def get_submission_content(
        course_identifier: str | int,
        assignment_id: str | int,
        user_id: str | int
    ) -> str:
        """Get the content/details of a specific student's submission to verify they actually submitted work.

        Returns submission type, body text (or preview), URL, attachment filenames, and submitted_at.
        Useful for verifying a student actually submitted content before grading.

        Args:
            course_identifier: The Canvas course code or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID of the student
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching submission: {response['error']}"

        submission_type = response.get("submission_type", "none")
        submitted_at = response.get("submitted_at")
        body = response.get("body")
        url = response.get("url")
        attachments = response.get("attachments", [])
        score = response.get("score")
        grade = response.get("grade")
        workflow_state = response.get("workflow_state", "unsubmitted")

        lines = []
        lines.append(f"User ID: {user_id}")
        lines.append(f"Assignment ID: {assignment_id}")
        lines.append(f"Workflow State: {workflow_state}")
        lines.append(f"Submission Type: {submission_type or 'none'}")
        lines.append(f"Submitted At: {submitted_at or 'Not submitted'}")
        lines.append(f"Score: {score if score is not None else 'Not graded'}")
        lines.append(f"Grade: {grade or 'Not graded'}")

        # Content details
        has_content = False

        if body:
            has_content = True
            preview = body[:300].strip()
            # Strip HTML tags for preview
            import re
            preview = re.sub(r'<[^>]+>', '', preview)
            lines.append(f"Body ({len(body)} chars): {preview}...")

        if url:
            has_content = True
            lines.append(f"URL: {url}")

        if attachments:
            has_content = True
            att_names = [f"{a.get('display_name', 'unnamed')} ({a.get('size', 0)} bytes)" for a in attachments]
            lines.append(f"Attachments: {', '.join(att_names)}")

        if not has_content and submission_type not in (None, "none"):
            lines.append("Content: (external tool or other type - no inline content)")
            has_content = True

        lines.append(f"Has Content: {'Yes' if has_content else 'No'}")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_submission_comments(
        course_identifier: str | int,
        assignment_id: str | int,
        user_id: str | int
    ) -> str:
        """Get all comments on a specific student's submission.

        Returns teacher comments, student comments, and peer review comments
        with author info and timestamps.

        Args:
            course_identifier: The Canvas course code or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID of the student
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}",
            params={"include[]": "submission_comments"}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching submission comments: {response['error']}"

        comments = response.get("submission_comments", [])

        if not comments:
            return f"No comments on submission for user {user_id} on assignment {assignment_id}."

        lines = [f"Comments on submission (user {user_id}, assignment {assignment_id}):"]
        lines.append(f"Total comments: {len(comments)}\n")

        for c in comments:
            author = c.get("author_name", "Unknown")
            created = format_date(c.get("created_at"))
            text = c.get("comment", "")
            comment_id = c.get("id")
            lines.append(f"[{comment_id}] {author} ({created}):")
            lines.append(f"  {text}")
            if c.get("attachments"):
                att_names = [a.get("display_name", "file") for a in c["attachments"]]
                lines.append(f"  Attachments: {', '.join(att_names)}")
            lines.append("")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def post_submission_comment(
        course_identifier: str | int,
        assignment_id: str | int,
        user_id: str | int,
        comment_text: str,
        group_comment: bool = False
    ) -> str:
        """Post a teacher comment on a student's submission without changing the grade.

        Use this to leave feedback, ask for revisions, or communicate about the submission.
        Does NOT affect the score or grade.

        Args:
            course_identifier: The Canvas course code or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID of the student
            comment_text: The comment text to post
            group_comment: If True, post comment to all group members (default False)
        """
        course_id = await get_course_id(course_identifier)

        data = {
            "comment": {
                "text_comment": comment_text,
            }
        }
        if group_comment:
            data["comment"]["group_comment"] = "true"

        response = await make_canvas_request(
            "put",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}",
            data=data
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error posting comment: {response['error']}"

        return f"Comment posted successfully on submission (user {user_id}, assignment {assignment_id}).\nComment: {comment_text}"

    @mcp.tool()
    @validate_params
    async def get_submission_history(
        course_identifier: str | int,
        assignment_id: str | int,
        user_id: str | int
    ) -> str:
        """Get the full submission history showing all prior attempts for a student.

        Shows when and how many times a student submitted/resubmitted, what changed
        between attempts, and the content of each attempt.

        Args:
            course_identifier: The Canvas course code or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID of the student
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}",
            params={"include[]": "submission_history"}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching submission history: {response['error']}"

        history = response.get("submission_history", [])

        if not history:
            return f"No submission history found for user {user_id} on assignment {assignment_id}."

        lines = [f"Submission History (user {user_id}, assignment {assignment_id}):"]
        lines.append(f"Total attempts: {len(history)}\n")

        for entry in history:
            attempt_num = entry.get("attempt", "?")
            submitted_at = format_date(entry.get("submitted_at"))
            sub_type = entry.get("submission_type", "none")
            score = entry.get("score")
            body = entry.get("body")
            url = entry.get("url")
            attachments = entry.get("attachments", [])

            lines.append(f"--- Attempt {attempt_num} ---")
            lines.append(f"  Submitted: {submitted_at}")
            lines.append(f"  Type: {sub_type}")
            if score is not None:
                lines.append(f"  Score: {score}")

            if body:
                preview = re.sub(r'<[^>]+>', '', body[:300]).strip()
                lines.append(f"  Body ({len(body)} chars): {preview}...")
            if url:
                lines.append(f"  URL: {url}")
            if attachments:
                att_names = [f"{a.get('display_name', 'unnamed')} ({a.get('size', 0)} bytes)" for a in attachments]
                lines.append(f"  Attachments: {', '.join(att_names)}")

            lines.append("")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def download_submission_attachment(
        course_identifier: str | int,
        assignment_id: str | int,
        user_id: str | int,
        attachment_id: str | int | None = None
    ) -> str:
        """Download and return the content of a text-based submission attachment.

        For text files (txt, html, csv, py, etc.), returns the file content.
        For binary files (pdf, docx, images), returns metadata only.
        If attachment_id is not provided, returns the first attachment.

        Args:
            course_identifier: The Canvas course code or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID of the student
            attachment_id: Optional specific attachment ID (default: first attachment)
        """
        import os

        from ..core.client import _get_http_client

        course_id = await get_course_id(course_identifier)

        # First, get the submission to find attachments
        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching submission: {response['error']}"

        attachments = response.get("attachments", [])
        if not attachments:
            return f"No attachments found on submission for user {user_id}, assignment {assignment_id}."

        # Find the target attachment
        target = None
        if attachment_id:
            attachment_id_int = int(attachment_id)
            for att in attachments:
                if att.get("id") == attachment_id_int:
                    target = att
                    break
            if not target:
                att_list = ", ".join(f"{a['id']} ({a.get('display_name', '?')})" for a in attachments)
                return f"Attachment {attachment_id} not found. Available: {att_list}"
        else:
            target = attachments[0]

        filename = target.get("display_name", "unknown")
        content_type = target.get("content-type", "application/octet-stream")
        size = target.get("size", 0)
        download_url = target.get("url")

        if not download_url:
            return f"No download URL for attachment {filename}."

        # Determine if this is a text file we can read
        TEXT_TYPES = {"text/", "application/json", "application/csv", "application/xml",
                      "application/javascript", "application/x-python"}
        TEXT_EXTENSIONS = {".txt", ".html", ".htm", ".csv", ".json", ".xml", ".py",
                          ".java", ".js", ".ts", ".css", ".md", ".yaml", ".yml", ".toml"}

        is_text = any(content_type.startswith(t) for t in TEXT_TYPES)
        if not is_text:
            _, ext = os.path.splitext(filename)
            is_text = ext.lower() in TEXT_EXTENSIONS

        if not is_text:
            # Binary file -- return metadata only
            result_lines = [
                f"Attachment: {filename}",
                f"Size: {size} bytes ({size / 1024:.1f} KB)",
                f"Content-Type: {content_type}",
                f"Attachment ID: {target.get('id')}",
                "",
                "Binary file -- content cannot be displayed as text.",
                "Use Canvas UI to download and view this file."
            ]
            return "\n".join(result_lines)

        # Text file -- download content using authenticated client
        client = _get_http_client()

        try:
            dl_response = await client.get(download_url, follow_redirects=True)
            dl_response.raise_for_status()
            text_content = dl_response.text

            # Limit output size to prevent overwhelming the context
            MAX_CHARS = 10000
            truncated = len(text_content) > MAX_CHARS
            if truncated:
                text_content = text_content[:MAX_CHARS]

            result_lines = [
                f"Attachment: {filename}",
                f"Size: {size} bytes",
                f"Content-Type: {content_type}",
                "",
                "--- Content ---",
                text_content,
            ]
            if truncated:
                result_lines.append(f"\n... (truncated, showing first {MAX_CHARS} of {size} chars)")

            return "\n".join(result_lines)

        except Exception as e:
            return f"Error downloading attachment {filename}: {str(e)}"

    @mcp.tool()
    @validate_params
    async def list_ungraded_submissions(
        course_identifier: str | int,
        assignment_ids: list[str | int] | None = None
    ) -> str:
        """List all ungraded (submitted but not scored) submissions across assignments.

        Useful for finding all work that still needs grading in a course.
        Optionally filter to specific assignments.

        Note: This tool does NOT catch students who resubmitted after being
        graded as 0. Use list_resubmitted_after_grading for that case.

        Args:
            course_identifier: The Canvas course code or ID
            assignment_ids: Optional list of assignment IDs to filter (default: all assignments)
        """
        from collections import defaultdict

        course_id = await get_course_id(course_identifier)

        params: dict[str, Any] = {
            "student_ids[]": "all",
            "workflow_state": "submitted",
            "per_page": 100,
        }

        if assignment_ids:
            params["assignment_ids[]"] = [str(aid) for aid in assignment_ids]

        submissions = await fetch_all_paginated_results(
            f"/courses/{course_id}/students/submissions",
            params
        )

        if isinstance(submissions, dict) and "error" in submissions:
            return f"Error fetching ungraded submissions: {submissions['error']}"

        if not submissions:
            return "No ungraded submissions found. All submitted work has been graded."

        # Filter to only truly ungraded: submitted but score is None
        ungraded = [
            s for s in submissions
            if s.get("workflow_state") in ("submitted", "pending_review")
            and s.get("score") is None
            and s.get("submitted_at") is not None
        ]

        if not ungraded:
            return "No ungraded submissions found. All submitted work has been graded."

        # Group by assignment for readability
        by_assignment: dict[str, list] = defaultdict(list)
        for s in ungraded:
            aid = str(s.get("assignment_id", "unknown"))
            by_assignment[aid].append(s)

        course_display = await get_course_code(str(course_id)) or str(course_identifier)

        lines = [f"Ungraded Submissions for {course_display}:"]
        lines.append(f"Total ungraded: {len(ungraded)}\n")

        for aid, subs in sorted(by_assignment.items()):
            lines.append(f"Assignment {aid} ({len(subs)} ungraded):")
            for s in subs:
                user_id = s.get("user_id")
                submitted_at = format_date(s.get("submitted_at"))
                lines.append(f"  User {user_id} - submitted {submitted_at}")
            lines.append("")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def list_resubmitted_after_grading(
        course_identifier: str | int,
        assignment_ids: list[str | int] | None = None,
        score_threshold: float = 0.0
    ) -> str:
        """Find submissions where a student resubmitted AFTER being graded.

        Catches the common case where a student was graded as 0 (missing work),
        then later submitted. Canvas marks these as workflow_state="graded" so
        list_ungraded_submissions won't find them.

        Detects resubmissions by comparing submitted_at vs graded_at timestamps.

        Args:
            course_identifier: The Canvas course code or ID
            assignment_ids: Optional list of assignment IDs to filter (default: all assignments)
            score_threshold: Only flag resubmissions where the current score is at or below
                             this value (default: 0.0, meaning only zero-scored submissions)
        """
        from collections import defaultdict

        course_id = await get_course_id(course_identifier)

        # If no assignment_ids provided, fetch them first to query in batches
        # (querying all graded submissions at once can exceed Canvas pagination limits)
        if not assignment_ids:
            assignments_resp = await fetch_all_paginated_results(
                f"/courses/{course_id}/assignments",
                {"per_page": 100}
            )
            if isinstance(assignments_resp, dict) and "error" in assignments_resp:
                return f"Error fetching assignments: {assignments_resp['error']}"
            assignment_ids = [a["id"] for a in assignments_resp if isinstance(a, dict) and "id" in a]

        if not assignment_ids:
            return "No assignments found in this course."

        # Query both "graded" and "submitted" workflow states in batches
        # Canvas sometimes keeps workflow_state="submitted" even after scoring
        all_submissions: list[Any] = []
        batch_size = 10
        for workflow_state in ("graded", "submitted"):
            for i in range(0, len(assignment_ids), batch_size):
                batch = assignment_ids[i:i + batch_size]
                params: dict[str, Any] = {
                    "student_ids[]": "all",
                    "workflow_state": workflow_state,
                    "assignment_ids[]": [str(aid) for aid in batch],
                    "per_page": 100,
                }
                submissions = await fetch_all_paginated_results(
                    f"/courses/{course_id}/students/submissions",
                    params
                )
                if isinstance(submissions, dict) and "error" in submissions:
                    continue
                if isinstance(submissions, list):
                    all_submissions.extend(submissions)

        if not all_submissions:
            return "No submissions found."

        # Find submissions that need re-review:
        # Case 1: workflow_state="graded", submitted_at > graded_at (resubmitted after grading)
        # Case 2: workflow_state="submitted", score is set and <= threshold (scored but not fully graded)
        resubmitted = []
        for s in all_submissions:
            submitted_at = s.get("submitted_at")
            graded_at = s.get("graded_at")
            score = s.get("score")
            state = s.get("workflow_state")

            if not submitted_at or score is None or score > score_threshold:
                continue

            if state == "graded" and graded_at:
                sub_dt = datetime.datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                grade_dt = datetime.datetime.fromisoformat(graded_at.replace("Z", "+00:00"))
                if sub_dt > grade_dt:
                    resubmitted.append(s)
            elif state == "submitted" and score <= score_threshold:
                # Scored but Canvas kept as "submitted" — needs review
                resubmitted.append(s)

        if not resubmitted:
            return "No resubmissions found after grading."

        try:
            resubmitted = anonymize_response_data(resubmitted, data_type="submissions")
        except Exception:
            pass

        # Group by assignment
        by_assignment: dict[str, list] = defaultdict(list)
        for s in resubmitted:
            aid = str(s.get("assignment_id", "unknown"))
            by_assignment[aid].append(s)

        course_display = await get_course_code(str(course_id)) or str(course_identifier)

        lines = [f"Resubmitted After Grading for {course_display}:"]
        lines.append(f"Total found: {len(resubmitted)}\n")

        for aid, subs in sorted(by_assignment.items()):
            lines.append(f"Assignment {aid} ({len(subs)} resubmission{'s' if len(subs) != 1 else ''}):")
            for s in subs:
                user_id = s.get("user_id")
                score = s.get("score")
                graded = format_date(s.get("graded_at"))
                submitted = format_date(s.get("submitted_at"))
                lines.append(f"  User {user_id} - graded {score} on {graded}, resubmitted {submitted}")
            lines.append("")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_assignment_analytics(
        course_identifier: str | int,
        assignment_id: str | int,
        summary_only: bool = False,
        verbosity: str | None = None
    ) -> str:
        """Get detailed analytics about student performance on a specific assignment.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
            summary_only: If True, returns only summary stats (~90% token savings)
            verbosity: Output format - "compact" (default), "standard", or "verbose"
        """
        course_id = await get_course_id(course_identifier)

        # Ensure assignment_id is a string
        assignment_id_str = str(assignment_id)

        # Get assignment details
        assignment = await make_canvas_request(
            "get", f"/courses/{course_id}/assignments/{assignment_id_str}"
        )

        if isinstance(assignment, dict) and "error" in assignment:
            return f"Error fetching assignment: {assignment['error']}"

        # Get all students in the course
        params = {
            "enrollment_type[]": "student",
            "per_page": 100
        }

        students = await fetch_all_paginated_results(
            f"/courses/{course_id}/users", params
        )

        if isinstance(students, dict) and "error" in students:
            return f"Error fetching students: {students['error']}"

        if not students:
            return f"No students found for course {course_identifier}."

        # Anonymize student data to protect privacy
        try:
            students = anonymize_response_data(students, data_type="users")
        except Exception as e:
            log_error(
                "Failed to anonymize student data in analytics",
                exc=e,
                course_id=course_id,
                assignment_id=assignment_id
            )
            # Continue with original data for functionality

        # Get submissions for this assignment
        submissions = await fetch_all_paginated_results(
            f"/courses/{course_id}/assignments/{assignment_id}/submissions",
            {"per_page": 100, "include[]": ["user"]}
        )

        if isinstance(submissions, dict) and "error" in submissions:
            return f"Error fetching submissions: {submissions['error']}"

        # Anonymize submission data to protect student privacy
        try:
            submissions = anonymize_response_data(submissions, data_type="submissions")
        except Exception as e:
            log_error(
                "Failed to anonymize submission data in analytics",
                exc=e,
                course_id=course_id,
                assignment_id=assignment_id
            )
            # Continue with original data for functionality

        # Extract assignment details
        assignment_name = assignment.get("name", "Unknown Assignment")
        due_date = assignment.get("due_at")
        points_possible = assignment.get("points_possible", 0)
        is_published = assignment.get("published", False)

        # Format the due date
        due_date_str = "No due date"
        if due_date:
            try:
                due_date_obj = datetime.datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                due_date_str = due_date_obj.strftime("%Y-%m-%d %H:%M")
                now = datetime.datetime.now(datetime.UTC)
                is_past_due = due_date_obj < now
            except (ValueError, AttributeError):
                due_date_str = due_date
                is_past_due = False
        else:
            is_past_due = False

        # Process submissions
        total_students = len(students)
        submitted_count = 0
        missing_count = 0
        late_count = 0
        graded_count = 0
        excused_count = 0
        scores: list[float] = []
        status_counts: dict[str, int] = {
            "submitted": 0,
            "unsubmitted": 0,
            "graded": 0,
            "pending_review": 0,
        }

        # Student status tracking
        student_status = []
        missing_students = []
        low_scoring_students = []
        high_scoring_students = []

        # Track which students have submissions
        student_ids_with_submissions = set()

        for submission in submissions:
            student_id = submission.get("user_id")
            student_ids_with_submissions.add(student_id)

            # Find student name
            student_name = "Unknown"
            for student in students:
                if student.get("id") == student_id:
                    student_name = student.get("name", "Unknown")
                    break

            # Process submission data
            score = submission.get("score")
            is_submitted = submission.get("submitted_at") is not None
            is_late = submission.get("late", False)
            is_missing = submission.get("missing", False)
            is_excused = submission.get("excused", False)
            is_graded = score is not None
            status = submission.get("workflow_state", "unsubmitted")
            submitted_at = submission.get("submitted_at")

            if submitted_at:
                try:
                    submitted_at = datetime.datetime.fromisoformat(
                        submitted_at.replace('Z', '+00:00')
                    ).strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    pass

            # Update statistics
            if is_submitted:
                submitted_count += 1
            if is_late:
                late_count += 1
            if is_missing:
                missing_count += 1
                missing_students.append(student_name)
            if is_excused:
                excused_count += 1
            if is_graded:
                graded_count += 1
                scores.append(score)

                # Track high/low scoring students
                if points_possible > 0:
                    percentage = (score / points_possible) * 100
                    if percentage < 70:
                        low_scoring_students.append((student_name, score, percentage))
                    if percentage > 90:
                        high_scoring_students.append((student_name, score, percentage))

            # Update status counts
            if status in status_counts:
                status_counts[status] += 1

            # Add to student status
            student_status.append({
                "name": student_name,
                "submitted": is_submitted,
                "submitted_at": submitted_at,
                "late": is_late,
                "missing": is_missing,
                "excused": is_excused,
                "score": score,
                "status": status
            })

        # Find students with no submissions
        for student in students:
            if student.get("id") not in student_ids_with_submissions:
                student_name = student.get("name", "Unknown")
                missing_students.append(student_name)

                # Add to student status
                student_status.append({
                    "name": student_name,
                    "submitted": False,
                    "submitted_at": None,
                    "late": False,
                    "missing": True,
                    "excused": False,
                    "score": None,
                    "status": "unsubmitted"
                })

        # Compute grade statistics
        scores = scores
        avg_score = mean(scores) if scores else 0
        median_score = median(scores) if scores else 0

        try:
            std_dev = stdev(scores) if len(scores) > 1 else 0
        except StatisticsError:
            std_dev = 0

        if points_possible > 0:
            avg_percentage = (avg_score / points_possible) * 100
        else:
            avg_percentage = 0

        # Determine verbosity level
        if verbosity:
            try:
                v = Verbosity(verbosity.lower())
            except ValueError:
                v = get_verbosity()
        else:
            v = get_verbosity()

        # Calculate key statistics
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)
        # total_students already set above
        submitted = submitted_count
        graded = graded_count
        missing = missing_count + (total_students - len(submissions))
        late = late_count

        # Summary-only mode: return minimal stats (~90% token savings)
        if summary_only or v == Verbosity.COMPACT:
            header = format_header("analytics", f"{assignment_name}|{course_display}", Verbosity.COMPACT)
            stats_line = format_stats({
                "submitted": submitted,
                "missing": missing,
                "average": avg_score if scores else 0,
                "median": median_score if scores else 0,
                "late": late,
            }, Verbosity.COMPACT)
            counts_line = f"<70%:{len(low_scoring_students)}|>90%:{len(high_scoring_students)}"
            body = f"{stats_line}\n{counts_line}"
            return format_response(header, body, Verbosity.COMPACT)

        # Full output format
        output = f"Assignment Analytics for '{assignment_name}' in Course {course_display}\n\n"

        # Assignment details
        output += "Assignment Details:\n"
        output += f"  Due: {due_date_str}"
        if is_past_due:
            output += " (Past Due)"
        output += "\n"

        output += f"  Points Possible: {points_possible}\n"
        output += f"  Published: {'Yes' if is_published else 'No'}\n\n"

        # Submission statistics
        output += "Submission Statistics:\n"

        # Calculate percentages
        submitted_pct = (submitted / total_students * 100) if total_students > 0 else 0
        graded_pct = (graded / total_students * 100) if total_students > 0 else 0
        missing_pct = (missing / total_students * 100) if total_students > 0 else 0
        late_pct = (late / submitted * 100) if submitted > 0 else 0

        output += f"  Submitted: {submitted}/{total_students} ({round(submitted_pct, 1)}%)\n"
        output += f"  Graded: {graded}/{total_students} ({round(graded_pct, 1)}%)\n"
        output += f"  Missing: {missing}/{total_students} ({round(missing_pct, 1)}%)\n"
        if submitted > 0:
            output += f"  Late: {late}/{submitted} ({round(late_pct, 1)}% of submissions)\n"
        output += f"  Excused: {excused_count}\n\n"

        # Grade statistics
        if scores:
            output += "Grade Statistics:\n"
            output += f"  Average Score: {round(avg_score, 2)}/{points_possible} ({round(avg_percentage, 1)}%)\n"
            output += f"  Median Score: {round(median_score, 2)}/{points_possible} ({round((median_score/points_possible)*100, 1)}%)\n"
            output += f"  Standard Deviation: {round(std_dev, 2)}\n"

            # High/Low scores
            if low_scoring_students:
                output += "\nStudents Scoring Below 70%:\n"
                for name, score, percentage in sorted(low_scoring_students, key=lambda x: x[2]):
                    output += f"  {name}: {round(score, 1)}/{points_possible} ({round(percentage, 1)}%)\n"

            if high_scoring_students:
                output += "\nStudents Scoring Above 90%:\n"
                for name, score, percentage in sorted(high_scoring_students, key=lambda x: x[2], reverse=True):
                    output += f"  {name}: {round(score, 1)}/{points_possible} ({round(percentage, 1)}%)\n"

        # Missing students
        if missing_students:
            output += "\nStudents Missing Submission:\n"
            # Sort alphabetically and show first 10
            for name in sorted(missing_students)[:10]:
                output += f"  {name}\n"
            if len(missing_students) > 10:
                output += f"  ...and {len(missing_students) - 10} more\n"

        return output

