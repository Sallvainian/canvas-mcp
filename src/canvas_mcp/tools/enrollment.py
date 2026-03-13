"""Enrollment and user management MCP tools for Canvas API."""

import mimetypes
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..core.anonymization import anonymize_response_data
from ..core.cache import get_course_code, get_course_id
from ..core.client import (
    fetch_all_paginated_results,
    make_canvas_request,
    upload_file_multipart,
)
from ..core.logging import log_warning
from ..core.response_formatter import (
    Verbosity,
    format_header,
    format_response,
    get_verbosity,
)
from ..core.validation import validate_params


def register_enrollment_tools(mcp: FastMCP) -> None:
    """Register enrollment and user management MCP tools."""

    @mcp.tool()
    @validate_params
    async def create_user(
        account_id: str | int,
        name: str,
        email: str,
        login_id: str | None = None,
        sis_user_id: str | None = None,
        send_confirmation: bool = False,
        skip_confirmation: bool = True,
    ) -> str:
        """Create a new user in a Canvas account.

        Args:
            account_id: The Canvas account ID (e.g., 15, or "self" for the default account)
            name: Full name of the user
            email: Email address for the user
            login_id: Login identifier (defaults to email if not provided)
            sis_user_id: Optional SIS ID for the user
            send_confirmation: Whether to send a registration confirmation email
            skip_confirmation: Whether to skip the confirmation step (mark user as pre-confirmed)
        """
        user_data: dict[str, Any] = {
            "user": {
                "name": name,
                "skip_registration": skip_confirmation,
            },
            "pseudonym": {
                "unique_id": login_id or email,
                "send_confirmation": send_confirmation,
            },
            "communication_channel": {
                "type": "email",
                "address": email,
                "skip_confirmation": skip_confirmation,
            },
        }

        if sis_user_id:
            user_data["pseudonym"]["sis_user_id"] = sis_user_id

        response = await make_canvas_request(
            "post",
            f"/accounts/{account_id}/users",
            data=user_data,
            skip_anonymization=True,
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error creating user: {response['error']}"

        user_id = response.get("id")
        user_name = response.get("name")
        return f"User created successfully.\nID: {user_id}\nName: {user_name}\nEmail: {email}"

    @mcp.tool()
    @validate_params
    async def enroll_user(
        course_identifier: str | int,
        user_id: str | int,
        enrollment_type: str = "StudentEnrollment",
        enrollment_state: str = "active",
        notify: bool = False,
    ) -> str:
        """Enroll a user in a Canvas course.

        Args:
            course_identifier: The Canvas course code or ID
            user_id: The Canvas user ID to enroll
            enrollment_type: Type of enrollment - StudentEnrollment, TeacherEnrollment,
                TaEnrollment, ObserverEnrollment, DesignerEnrollment
            enrollment_state: Initial state - active, invited, creation_pending, inactive
            notify: Whether to send an enrollment notification email
        """
        valid_types = [
            "StudentEnrollment",
            "TeacherEnrollment",
            "TaEnrollment",
            "ObserverEnrollment",
            "DesignerEnrollment",
        ]
        if enrollment_type not in valid_types:
            return f"Invalid enrollment_type '{enrollment_type}'. Must be one of: {', '.join(valid_types)}"

        valid_states = ["active", "invited", "creation_pending", "inactive"]
        if enrollment_state not in valid_states:
            return f"Invalid enrollment_state '{enrollment_state}'. Must be one of: {', '.join(valid_states)}"

        course_id = await get_course_id(course_identifier)

        enrollment_data = {
            "enrollment": {
                "user_id": str(user_id),
                "type": enrollment_type,
                "enrollment_state": enrollment_state,
                "notify": notify,
            }
        }

        response = await make_canvas_request(
            "post",
            f"/courses/{course_id}/enrollments",
            data=enrollment_data,
            skip_anonymization=True,
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error enrolling user: {response['error']}"

        enrollment_id = response.get("id")
        role = response.get("type", enrollment_type)
        state = response.get("enrollment_state", enrollment_state)
        return (
            f"User {user_id} enrolled successfully.\n"
            f"Enrollment ID: {enrollment_id}\n"
            f"Role: {role}\n"
            f"State: {state}\n"
            f"Course: {course_id}"
        )

    @mcp.tool()
    @validate_params
    async def submit_file_for_student(
        course_identifier: str | int,
        assignment_id: str | int,
        user_id: str | int,
        file_path: str,
        content_type: str | None = None,
        comment: str | None = None,
    ) -> str:
        """Submit a file on behalf of a student (requires act-as permissions or admin role).

        Uses Canvas's 3-step file upload process:
        1. Request an upload slot
        2. Upload the file to the returned URL
        3. Create the submission with the uploaded file ID

        Args:
            course_identifier: The Canvas course code or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID to submit for
            file_path: Local path to the file to upload
            content_type: MIME type (auto-detected from extension if not provided)
            comment: Optional text comment to include with the submission
        """
        from pathlib import Path

        course_id = await get_course_id(course_identifier)
        assignment_id_str = str(assignment_id)
        user_id_str = str(user_id)

        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found at {file_path}"

        if content_type is None:
            content_type = (
                mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            )

        # Step 1: Request upload slot
        slot_response = await make_canvas_request(
            "post",
            f"/courses/{course_id}/assignments/{assignment_id_str}/submissions/{user_id_str}/files",
            data={
                "name": path.name,
                "size": path.stat().st_size,
                "content_type": content_type,
            },
            skip_anonymization=True,
        )

        if isinstance(slot_response, dict) and "error" in slot_response:
            return f"Error requesting upload slot: {slot_response['error']}"

        upload_url = slot_response.get("upload_url")
        upload_params = slot_response.get("upload_params", {})

        if not upload_url:
            return (
                f"Error: No upload_url returned from Canvas. Response: {slot_response}"
            )

        # Step 2: Upload the file
        upload_response = await upload_file_multipart(
            upload_url, upload_params, file_path
        )

        if isinstance(upload_response, dict) and "error" in upload_response:
            return f"Error uploading file: {upload_response['error']}"

        file_id = upload_response.get("id")
        if not file_id:
            return f"Error: No file ID in upload response. Response: {upload_response}"

        # Step 3: Create the submission
        submission_data: dict[str, Any] = {
            "submission": {
                "submission_type": "online_upload",
                "file_ids": [file_id],
                "user_id": user_id_str,
            }
        }

        if comment:
            submission_data["comment"] = {"text_comment": comment}

        submission_response = await make_canvas_request(
            "post",
            f"/courses/{course_id}/assignments/{assignment_id_str}/submissions",
            data=submission_data,
            skip_anonymization=True,
        )

        if isinstance(submission_response, dict) and "error" in submission_response:
            return f"Error creating submission: {submission_response['error']}"

        sub_id = submission_response.get("id")
        return (
            f"File submitted successfully for user {user_id_str}.\n"
            f"Submission ID: {sub_id}\n"
            f"File: {path.name} (ID: {file_id})\n"
            f"Assignment: {assignment_id_str}\n"
            f"Course: {course_id}"
        )

    @mcp.tool()
    @validate_params
    async def list_groups(course_identifier: str | int) -> str:
        """List all groups and their members for a specific course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
        """
        course_id = await get_course_id(course_identifier)

        groups = await fetch_all_paginated_results(
            f"/courses/{course_id}/groups", {"per_page": 100}
        )

        if isinstance(groups, dict) and "error" in groups:
            return f"Error fetching groups: {groups['error']}"

        if not groups:
            return f"No groups found for course {course_identifier}."

        course_display = await get_course_code(course_id) or course_identifier
        output = f"Groups for Course {course_display}:\n\n"

        for group in groups:
            group_id = group.get("id")
            group_name = group.get("name", "Unnamed group")
            group_category = group.get("group_category_id", "Uncategorized")
            member_count = group.get("members_count", 0)

            output += f"Group: {group_name}\n"
            output += f"ID: {group_id}\n"
            output += f"Category ID: {group_category}\n"
            output += f"Member Count: {member_count}\n"

            members = await fetch_all_paginated_results(
                f"/groups/{group_id}/users", {"per_page": 100}
            )

            if isinstance(members, dict) and "error" in members:
                output += f"Error fetching members: {members['error']}\n"
            elif not members:
                output += "No members in this group.\n"
            else:
                try:
                    members = anonymize_response_data(members, data_type="users")
                except Exception as e:
                    log_warning(f"Failed to anonymize group member data: {str(e)}")
                output += "Members:\n"
                for member in members:
                    member_id = member.get("id")
                    member_name = member.get("name", "Unnamed user")
                    member_email = member.get("email", "No email")
                    output += (
                        f"  - {member_name} (ID: {member_id}, Email: {member_email})\n"
                    )

            output += "\n"

        return output

    @mcp.tool()
    async def list_users(course_identifier: str, verbosity: str | None = None) -> str:
        """List users enrolled in a specific course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            verbosity: Output format - "compact" (default), "standard", or "verbose"
        """
        if verbosity:
            try:
                v = Verbosity(verbosity.lower())
            except ValueError:
                v = get_verbosity()
        else:
            v = get_verbosity()

        course_id = await get_course_id(course_identifier)

        params = {"include[]": ["enrollments", "email"], "per_page": 100}

        users = await fetch_all_paginated_results(f"/courses/{course_id}/users", params)

        if isinstance(users, dict) and "error" in users:
            return f"Error fetching users: {users['error']}"

        if not users:
            return f"No users found for course {course_identifier}."

        try:
            users = anonymize_response_data(users, data_type="users")
        except Exception as e:
            log_warning(f"Failed to anonymize user data: {str(e)}")

        course_display = await get_course_code(course_id) or course_identifier

        if v == Verbosity.COMPACT:
            header = format_header("users", course_display, v)
            items = []
            role_abbrev_map = {
                "StudentEnrollment": "S",
                "TeacherEnrollment": "T",
                "TaEnrollment": "TA",
                "ObserverEnrollment": "O",
                "DesignerEnrollment": "D",
            }
            for user in users:
                user_id = user.get("id")
                name = user.get("name", "Unknown")
                enrollments = user.get("enrollments", [])
                roles = []
                for enrollment in enrollments:
                    role_value = enrollment.get("role") or "StudentEnrollment"
                    role_str_full = str(role_value)
                    abbrev = role_abbrev_map.get(role_str_full)
                    if not abbrev:
                        normalized = role_str_full.strip()
                        abbrev = normalized[:2].upper() if normalized else "S"
                    roles.append(abbrev)
                role_str = "/".join(sorted(set(roles))) if roles else "S"
                items.append(f"{user_id}|{name}|{role_str}")

            body = "\n".join(items)
            return format_response(header, body, v)

        else:
            users_info = []
            for user in users:
                user_id = user.get("id")
                name = user.get("name", "Unknown")
                email = user.get("email", "No email")
                enrollments = user.get("enrollments", [])
                roles = [
                    enrollment.get("role", "Student") for enrollment in enrollments
                ]
                role_list = ", ".join(set(roles)) if roles else "Student"
                users_info.append(
                    f"ID: {user_id}\nName: {name}\nEmail: {email}\nRoles: {role_list}\n"
                )

            return f"Users in Course {course_display}:\n\n" + "\n".join(users_info)
