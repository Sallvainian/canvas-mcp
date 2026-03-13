"""Assignment-related MCP tools for Canvas API."""

import re

import markdown as _markdown  # type: ignore[import-untyped]
from mcp.server.fastmcp import FastMCP

from ..core.anonymization import anonymize_response_data
from ..core.cache import get_course_code, get_course_id
from ..core.client import fetch_all_paginated_results, make_canvas_request
from ..core.dates import (
    format_date,
    format_date_smart,
    parse_date,
    parse_to_iso8601,
)
from ..core.logging import log_error
from ..core.response_formatter import (
    Verbosity,
    format_header,
    format_response,
    get_verbosity,
)
from ..core.validation import validate_params


def description_to_html(text: str) -> str:
    """Convert a description to Canvas-ready HTML.

    Accepts either plain markdown or raw HTML.
    - If the text already contains HTML tags, it is returned as-is.
    - Otherwise, markdown is converted to HTML (supports **bold**, *italic*,
      # headings, - lists, numbered lists, and plain paragraphs).

    This means you can write descriptions naturally in markdown without
    needing to hand-craft HTML, and existing HTML descriptions still work.

    Examples:
        "**Bold** and *italic*"          -> "<p><strong>Bold</strong> and <em>italic</em></p>"
        "- item one\\n- item two"         -> "<ul><li>item one</li><li>item two</li></ul>"
        "<p><strong>Bold</strong></p>"   -> "<p><strong>Bold</strong></p>"  (unchanged)
    """
    if re.search(r"<[a-zA-Z][^>]*>", text):
        # Already contains HTML tags — pass through unchanged
        return text
    return str(_markdown.markdown(text, extensions=["nl2br"]))


def register_assignment_tools(mcp: FastMCP) -> None:
    """Register all assignment-related MCP tools."""

    @mcp.tool()
    @validate_params
    async def list_grading_periods(
        course_identifier: str | int,
        verbosity: str | None = None
    ) -> str:
        """List grading periods (marking periods) for a specific course.

        Use this to get grading period IDs which can then be used to filter
        assignments by marking period using the list_assignments tool.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            verbosity: Output format - "compact" (default), "standard", or "verbose"
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

        response = await make_canvas_request(
            "get", f"/courses/{course_id}/grading_periods"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching grading periods: {response['error']}"

        # The response contains a "grading_periods" key
        grading_periods = response.get("grading_periods", [])

        if not grading_periods:
            return f"No grading periods found for course {course_identifier}. This course may not use grading periods."

        # Try to get the course code for display
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)

        if v == Verbosity.COMPACT:
            # Token-efficient format: pipe-delimited
            header = format_header("gp", course_display, v)
            items = []
            for gp in grading_periods:
                gp_id = gp.get("id")
                title = gp.get("title", "Unnamed")
                start = format_date_smart(gp.get("start_date"), "compact")
                end = format_date_smart(gp.get("end_date"), "compact")
                is_closed = "closed" if gp.get("is_closed") else "open"
                items.append(f"{gp_id}|{title}|{start}-{end}|{is_closed}")

            body = "\n".join(items)
            return format_response(header, body, v)

        else:
            # Standard/verbose format with labels
            output_lines = [f"Grading Periods for Course {course_display}:\n"]

            for gp in grading_periods:
                gp_id = gp.get("id")
                title = gp.get("title", "Unnamed Period")
                start_date = format_date(gp.get("start_date")) if gp.get("start_date") else "Not set"
                end_date = format_date(gp.get("end_date")) if gp.get("end_date") else "Not set"
                close_date = format_date(gp.get("close_date")) if gp.get("close_date") else "Not set"
                is_closed = gp.get("is_closed", False)
                weight = gp.get("weight")

                output_lines.append(f"ID: {gp_id}")
                output_lines.append(f"Title: {title}")
                output_lines.append(f"Start: {start_date}")
                output_lines.append(f"End: {end_date}")
                output_lines.append(f"Close Date: {close_date}")
                output_lines.append(f"Status: {'Closed' if is_closed else 'Open'}")
                if weight is not None:
                    output_lines.append(f"Weight: {weight}%")
                output_lines.append("")

            return "\n".join(output_lines)

    @mcp.tool()
    @validate_params
    async def list_assignments(
        course_identifier: str | int,
        grading_period_id: int | None = None,
        verbosity: str | None = None
    ) -> str:
        """List assignments for a specific course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            grading_period_id: Optional grading period (marking period) ID to filter assignments.
                             Use list_grading_periods to get available period IDs.
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

        # If grading_period_id is provided, use assignment_groups endpoint with grading period filter
        if grading_period_id:
            params = {
                "per_page": 100,
                "include[]": ["assignments"],
                "grading_period_id": grading_period_id
            }

            assignment_groups = await fetch_all_paginated_results(
                f"/courses/{course_id}/assignment_groups", params
            )

            if isinstance(assignment_groups, dict) and "error" in assignment_groups:
                return f"Error fetching assignments: {assignment_groups['error']}"

            # Extract assignments from all groups
            all_assignments = []
            for group in assignment_groups:
                assignments = group.get("assignments", [])
                all_assignments.extend(assignments)
        else:
            # Standard endpoint without grading period filter
            params = {
                "per_page": 100,
                "include[]": ["all_dates", "submission"]
            }

            all_assignments = await fetch_all_paginated_results(f"/courses/{course_id}/assignments", params)

            if isinstance(all_assignments, dict) and "error" in all_assignments:
                return f"Error fetching assignments: {all_assignments['error']}"

        if not all_assignments:
            msg = f"No assignments found for course {course_identifier}"
            if grading_period_id:
                msg += f" in grading period {grading_period_id}"
            return msg + "."

        # Try to get the course code for display
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)

        if v == Verbosity.COMPACT:
            # Token-efficient format: pipe-delimited, abbreviated
            header = format_header("asgn", course_display, v)
            items = []
            for assignment in all_assignments:
                assignment_id = assignment.get("id")
                name = assignment.get("name", "Unnamed")
                due_at = format_date_smart(assignment.get("due_at"), "compact")
                points = assignment.get("points_possible", 0)
                items.append(f"{assignment_id}|{name}|{due_at}|{points}")

            body = "\n".join(items)
            return format_response(header, body, v)

        else:
            # Standard/verbose format with labels
            assignments_info = []
            for assignment in all_assignments:
                assignment_id = assignment.get("id")
                name = assignment.get("name", "Unnamed assignment")
                due_at = format_date(assignment.get("due_at")) if assignment.get("due_at") else "No due date"
                points = assignment.get("points_possible", 0)

                assignments_info.append(
                    f"ID: {assignment_id}\nName: {name}\nDue: {due_at}\nPoints: {points}\n"
                )

            header = f"Assignments for Course {course_display}"
            if grading_period_id:
                header += f" (Grading Period {grading_period_id})"
            return header + ":\n\n" + "\n".join(assignments_info)

    @mcp.tool()
    @validate_params
    async def get_assignment_details(course_identifier: str | int, assignment_id: str | int) -> str:
        """Get detailed information about a specific assignment.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
        """
        course_id = await get_course_id(course_identifier)

        # Ensure assignment_id is a string
        assignment_id_str = str(assignment_id)

        response = await make_canvas_request(
            "get", f"/courses/{course_id}/assignments/{assignment_id_str}"
        )

        if "error" in response:
            return f"Error fetching assignment details: {response['error']}"

        details = [
            f"Name: {response.get('name', 'N/A')}",
            f"Description: {response.get('description', 'N/A')}",
            f"Due Date: {format_date(response.get('due_at'))}",
            f"Points Possible: {response.get('points_possible', 'N/A')}",
            f"Submission Types: {', '.join(response.get('submission_types', ['N/A']))}",
            f"Published: {response.get('published', False)}",
            f"Locked: {response.get('locked_for_user', False)}"
        ]

        if response.get("external_tool_tag_attributes"):
            ext = response["external_tool_tag_attributes"]
            details.append(f"External Tool URL: {ext.get('url', 'N/A')}")
            details.append(f"External Tool New Tab: {ext.get('new_tab', False)}")

        # Try to get the course code for display
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)
        return f"Assignment Details for ID {assignment_id} in course {course_display}:\n\n" + "\n".join(details)

    @mcp.tool()
    @validate_params
    async def update_assignment(
        course_identifier: str | int,
        assignment_id: str | int,
        due_at: str | None = None,
        name: str | None = None,
        description: str | None = None,
        points_possible: float | None = None,
        published: bool | None = None,
        lock_at: str | None = None,
        unlock_at: str | None = None,
        submission_types: str | None = None,
        external_tool_url: str | None = None
    ) -> str:
        """Update an assignment's properties.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
            due_at: Due date (e.g., '12/10/2025', 'Dec 10, 2025', '2025-12-10')
            name: Assignment name
            description: Assignment description — accepts markdown OR raw HTML.
                Markdown (**bold**, *italic*, # headings, - lists) is auto-converted
                to HTML. Raw HTML is passed through unchanged.
            points_possible: Point value for the assignment
            published: Whether the assignment is published
            lock_at: Date to lock submissions (same format as due_at)
            unlock_at: Date to unlock the assignment (same format as due_at)
            submission_types: Comma-separated list of submission types (e.g., "external_tool", "online_upload,online_text_entry")
            external_tool_url: URL for external tool submissions (used with submission_types="external_tool")
        """
        course_id = await get_course_id(course_identifier)
        assignment_id_str = str(assignment_id)

        # Build update data - only include fields that are provided
        assignment_data: dict = {}

        if due_at is not None:
            try:
                assignment_data["due_at"] = parse_to_iso8601(due_at)
            except ValueError as e:
                return f"Error parsing due date: {e}"

        if name is not None:
            assignment_data["name"] = name

        if description is not None:
            assignment_data["description"] = description_to_html(description)

        if points_possible is not None:
            assignment_data["points_possible"] = points_possible

        if published is not None:
            assignment_data["published"] = published

        if lock_at is not None:
            try:
                assignment_data["lock_at"] = parse_to_iso8601(lock_at)
            except ValueError as e:
                return f"Error parsing lock date: {e}"

        if unlock_at is not None:
            try:
                assignment_data["unlock_at"] = parse_to_iso8601(unlock_at, end_of_day=False)
            except ValueError as e:
                return f"Error parsing unlock date: {e}"

        if submission_types is not None:
            types_list = [s.strip() for s in submission_types.split(",")]
            assignment_data["submission_types"] = types_list

        if external_tool_url is not None:
            assignment_data["external_tool_tag_attributes"] = {"url": external_tool_url}

        # Validate that at least one field is being updated
        if not assignment_data:
            return "Error: No update data provided. Please specify at least one field to update."

        # Make the API request
        response = await make_canvas_request(
            "put",
            f"/courses/{course_id}/assignments/{assignment_id_str}",
            data={"assignment": assignment_data}
        )

        if "error" in response:
            return f"Error updating assignment: {response['error']}"

        # Build confirmation message
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)
        updated_fields = list(assignment_data.keys())
        assignment_name = response.get("name", f"ID {assignment_id}")

        confirmation = f"Successfully updated assignment '{assignment_name}' in course {course_display}.\n\n"
        confirmation += "Updated fields:\n"
        for field in updated_fields:
            value = assignment_data[field]
            confirmation += f"  - {field}: {value}\n"

        return confirmation

    @mcp.tool()
    @validate_params
    async def delete_assignment(
        course_identifier: str | int,
        assignment_id: str | int
    ) -> str:
        """Delete an assignment from a course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID to delete
        """
        course_id = await get_course_id(course_identifier)
        assignment_id_str = str(assignment_id)

        # Fetch assignment name before deleting for confirmation
        assignment = await make_canvas_request(
            "get", f"/courses/{course_id}/assignments/{assignment_id_str}"
        )
        assignment_name = assignment.get("name", f"ID {assignment_id}") if "error" not in assignment else f"ID {assignment_id}"

        response = await make_canvas_request(
            "delete", f"/courses/{course_id}/assignments/{assignment_id_str}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error deleting assignment: {response['error']}"

        course_display = await get_course_code(course_id) if course_id else str(course_identifier)
        return f"Successfully deleted assignment '{assignment_name}' (ID {assignment_id}) from course {course_display}."

    @mcp.tool()
    async def assign_peer_review(course_identifier: str, assignment_id: str, reviewer_id: str, reviewee_id: str) -> str:
        """Manually assign a peer review to a student for a specific assignment.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
            reviewer_id: The Canvas user ID of the student who will do the review
            reviewee_id: The Canvas user ID of the student whose submission will be reviewed
        """
        course_id = await get_course_id(course_identifier)

        # First, we need to get the submission ID for the reviewee
        submissions = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions",
            params={"per_page": 100}
        )

        if "error" in submissions:
            return f"Error fetching submissions: {submissions['error']}"

        # Find the submission for the reviewee
        reviewee_submission = None
        for submission in submissions:
            if str(submission.get("user_id")) == str(reviewee_id):
                reviewee_submission = submission
                break

        # If no submission exists, we need to create a placeholder submission
        if not reviewee_submission:
            # Create a placeholder submission for the reviewee
            placeholder_data = {
                "submission": {
                    "user_id": reviewee_id,
                    "submission_type": "online_text_entry",
                    "body": "Placeholder submission for peer review"
                }
            }

            reviewee_submission = await make_canvas_request(
                "post",
                f"/courses/{course_id}/assignments/{assignment_id}/submissions",
                data=placeholder_data
            )

            if "error" in reviewee_submission:
                return f"Error creating placeholder submission: {reviewee_submission['error']}"

        # Now assign the peer review using the submission ID
        submission_id = reviewee_submission.get("id")

        # Data for the peer review assignment
        data = {
            "user_id": reviewer_id  # The user who will do the review
        }

        # Make the API request to create the peer review
        response = await make_canvas_request(
            "post",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/peer_reviews",
            data=data
        )

        if "error" in response:
            return f"Error assigning peer review: {response['error']}"

        # Try to get the course code for display
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)

        return f"Successfully assigned peer review in course {course_display}:\n" + \
               f"Assignment ID: {assignment_id}\n" + \
               f"Reviewer ID: {reviewer_id}\n" + \
               f"Reviewee ID: {reviewee_id}\n" + \
               f"Submission ID: {submission_id}"

    @mcp.tool()
    async def list_peer_reviews(course_identifier: str, assignment_id: str) -> str:
        """List all peer review assignments for a specific assignment.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
        """
        course_id = await get_course_id(course_identifier)

        # Get all submissions for this assignment
        submissions = await fetch_all_paginated_results(
            f"/courses/{course_id}/assignments/{assignment_id}/submissions",
            {"include[]": "submission_comments", "per_page": 100}
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
                "Failed to anonymize submission data in peer reviews",
                exc=e,
                course_id=course_id,
                assignment_id=assignment_id
            )
            # Continue with original data for functionality

        # Get all users in the course for name lookups
        users = await fetch_all_paginated_results(
            f"/courses/{course_id}/users",
            {"per_page": 100}
        )

        if isinstance(users, dict) and "error" in users:
            return f"Error fetching users: {users['error']}"

        # Anonymize user data to protect student privacy
        try:
            users = anonymize_response_data(users, data_type="users")
        except Exception as e:
            log_error(
                "Failed to anonymize user data in peer reviews",
                exc=e,
                course_id=course_id,
                assignment_id=assignment_id
            )
            # Continue with original data for functionality

        # Create a mapping of user IDs to names
        user_map = {}
        for user in users:
            user_id = str(user.get("id"))
            user_name = user.get("name", "Unknown")
            user_map[user_id] = user_name

        # Collect peer review data
        peer_reviews_by_submission = {}

        for submission in submissions:
            submission_id = submission.get("id")
            user_id = str(submission.get("user_id"))
            user_name = user_map.get(user_id, f"User {user_id}")

            # Get peer reviews for this submission
            peer_reviews = await make_canvas_request(
                "get",
                f"/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/peer_reviews"
            )

            if "error" in peer_reviews:
                continue  # Skip if error

            if peer_reviews:
                peer_reviews_by_submission[submission_id] = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "peer_reviews": peer_reviews
                }

        # Format the output
        course_display = await get_course_code(course_id) if course_id else str(course_identifier)
        output = f"Peer Reviews for Assignment {assignment_id} in course {course_display}:\n\n"

        if not peer_reviews_by_submission:
            output += "No peer reviews found for this assignment."
            return output

        # Display peer reviews grouped by reviewee
        for _submission_id, data in peer_reviews_by_submission.items():
            reviewee_name = data["user_name"]
            reviewee_id = data["user_id"]
            reviews = data["peer_reviews"]

            output += f"Reviews for {reviewee_name} (ID: {reviewee_id}):\n"

            if not reviews:
                output += "  No peer reviews assigned.\n\n"
                continue

            for review in reviews:
                reviewer_id = str(review.get("user_id"))
                reviewer_name = user_map.get(reviewer_id, f"User {reviewer_id}")
                workflow_state = review.get("workflow_state", "Unknown")

                output += f"  Reviewer: {reviewer_name} (ID: {reviewer_id})\n"
                output += f"  Status: {workflow_state}\n"

                # Add assessment details if available
                if "assessment" in review and review["assessment"]:
                    assessment = review["assessment"]
                    score = assessment.get("score")
                    if score is not None:
                        output += f"  Score: {score}\n"

                output += "\n"

        return output

    @mcp.tool()
    @validate_params
    async def create_assignment(
        course_identifier: str | int,
        name: str,
        description: str | None = None,
        submission_types: str | None = None,
        due_at: str | None = None,
        unlock_at: str | None = None,
        lock_at: str | None = None,
        points_possible: float | None = None,
        grading_type: str | None = None,
        published: bool = False,
        assignment_group_id: str | int | None = None,
        peer_reviews: bool = False,
        automatic_peer_reviews: bool = False,
        allowed_extensions: str | None = None
    ) -> str:
        """Create a new assignment in a course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            name: The name/title of the assignment (required)
            description: Assignment description — accepts markdown OR raw HTML.
                Markdown (**bold**, *italic*, # headings, - lists) is auto-converted
                to HTML. Raw HTML is passed through unchanged.
            submission_types: Comma-separated list of allowed submission types:
                online_text_entry, online_url, online_upload, discussion_topic,
                none, on_paper, external_tool
            due_at: Due date in ISO 8601 format (e.g., "2026-01-26T23:59:00Z")
            unlock_at: Date when assignment becomes available (ISO 8601)
            lock_at: Date when assignment locks (ISO 8601)
            points_possible: Maximum points for the assignment
            grading_type: One of: points, letter_grade, pass_fail, percent, not_graded
            published: Whether to publish immediately (default: False for safety)
            assignment_group_id: ID of the assignment group to place this in
            peer_reviews: Whether to enable peer reviews
            automatic_peer_reviews: Whether to automatically assign peer reviews
            allowed_extensions: Comma-separated list of file extensions for online_upload
                (e.g., "pdf,docx,txt")
        """
        course_id = await get_course_id(course_identifier)

        # Validate grading_type if provided
        valid_grading_types = ["points", "letter_grade", "pass_fail", "percent", "not_graded"]
        if grading_type and grading_type not in valid_grading_types:
            return f"Invalid grading_type '{grading_type}'. Must be one of: {', '.join(valid_grading_types)}"

        # Validate submission_types if provided
        valid_submission_types = [
            "online_text_entry", "online_url", "online_upload",
            "discussion_topic", "none", "on_paper", "external_tool"
        ]
        submission_types_list = []
        if submission_types:
            submission_types_list = [s.strip() for s in submission_types.split(",")]
            for st in submission_types_list:
                if st not in valid_submission_types:
                    return f"Invalid submission_type '{st}'. Must be one of: {', '.join(valid_submission_types)}"

        # Build assignment data
        assignment_data = {
            "name": name,
            "published": published
        }

        if description:
            assignment_data["description"] = description_to_html(description)

        if submission_types_list:
            assignment_data["submission_types"] = submission_types_list

        # Validate and parse date fields
        if due_at:
            parsed_due = parse_date(due_at)
            if not parsed_due:
                return f"Invalid date format for due_at: '{due_at}'. Use ISO 8601 format (e.g., '2026-01-26T23:59:00Z')."
            assignment_data["due_at"] = parsed_due.isoformat()

        if unlock_at:
            parsed_unlock = parse_date(unlock_at)
            if not parsed_unlock:
                return f"Invalid date format for unlock_at: '{unlock_at}'. Use ISO 8601 format (e.g., '2026-01-26T00:00:00Z')."
            assignment_data["unlock_at"] = parsed_unlock.isoformat()

        if lock_at:
            parsed_lock = parse_date(lock_at)
            if not parsed_lock:
                return f"Invalid date format for lock_at: '{lock_at}'. Use ISO 8601 format (e.g., '2026-02-01T23:59:00Z')."
            assignment_data["lock_at"] = parsed_lock.isoformat()

        if points_possible is not None:
            assignment_data["points_possible"] = points_possible

        if grading_type:
            assignment_data["grading_type"] = grading_type

        if assignment_group_id:
            assignment_data["assignment_group_id"] = assignment_group_id

        # Validate peer review settings
        if automatic_peer_reviews and not peer_reviews:
            return "Invalid configuration: automatic_peer_reviews requires peer_reviews=True. Set peer_reviews=True to enable automatic peer review assignment."

        if peer_reviews:
            assignment_data["peer_reviews"] = peer_reviews

        if automatic_peer_reviews:
            assignment_data["automatic_peer_reviews"] = automatic_peer_reviews

        if allowed_extensions:
            extensions_list = [ext.strip() for ext in allowed_extensions.split(",")]
            assignment_data["allowed_extensions"] = extensions_list

        # Make the API request
        response = await make_canvas_request(
            "post",
            f"/courses/{course_id}/assignments",
            data={"assignment": assignment_data}
        )

        if "error" in response:
            return f"Error creating assignment: {response['error']}"

        # Format success response
        assignment_id = response.get("id")
        assignment_name = response.get("name", name)
        assignment_points = response.get("points_possible")
        assignment_published = response.get("published", False)
        assignment_due = response.get("due_at")
        assignment_types = response.get("submission_types", [])
        html_url = response.get("html_url", "")

        course_display = await get_course_code(course_id) if course_id else str(course_identifier)

        result = "✅ Assignment created successfully!\n\n"
        result += f"**{assignment_name}**\n"
        result += f"  Course: {course_display}\n"
        result += f"  Assignment ID: {assignment_id}\n"

        if assignment_points is not None:
            result += f"  Points: {assignment_points}\n"

        if assignment_due:
            result += f"  Due: {format_date(assignment_due)}\n"

        result += f"  Published: {'Yes' if assignment_published else 'No'}\n"

        if assignment_types:
            result += f"  Submission Types: {', '.join(assignment_types)}\n"

        if html_url:
            result += f"  URL: {html_url}\n"

        return result
