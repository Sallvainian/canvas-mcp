"""Rubric grading MCP tools for Canvas API."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..core.anonymization import anonymize_response_data
from ..core.cache import get_course_code, get_course_id
from ..core.client import make_canvas_request, poll_canvas_progress
from ..core.dates import format_date, truncate_text
from ..core.logging import log_error
from ..core.validation import validate_params


def build_bulk_grade_form_data(
    grades: dict[str, dict[str, Any]],
) -> list[tuple[str, str]]:
    """Convert a grades dict to Canvas bulk update form-encoded tuples.

    Canvas's bulk update endpoint expects:
        grade_data[<student_id>][posted_grade] = "value"
        grade_data[<student_id>][excuse] = "true"
        grade_data[<student_id>][text_comment] = "comment text"

    Args:
        grades: Dict mapping user IDs to grade info.
                Each value can contain: grade, excused, comment.

    Returns:
        List of (key, value) tuples for form encoding.
    """
    form_tuples: list[tuple[str, str]] = []

    for user_id, grade_info in grades.items():
        prefix = f"grade_data[{user_id}]"

        if grade_info.get("excused"):
            form_tuples.append((f"{prefix}[excuse]", "true"))
        elif "grade" in grade_info:
            form_tuples.append((f"{prefix}[posted_grade]", str(grade_info["grade"])))

        if "comment" in grade_info:
            form_tuples.append((f"{prefix}[text_comment]", str(grade_info["comment"])))

    return form_tuples


def build_rubric_assessment_form_data(
    rubric_assessment: dict[str, Any], comment: str | None = None
) -> dict[str, str]:
    """Convert rubric assessment dict to Canvas form-encoded format.

    Canvas API expects rubric assessment data as form-encoded parameters with
    bracket notation: rubric_assessment[criterion_id][field]=value

    Args:
        rubric_assessment: Dict mapping criterion IDs to assessment data
                          Format: {"criterion_id": {"points": X, "rating_id": Y, "comments": Z}}
        comment: Optional overall comment for the submission

    Returns:
        Flattened dict with Canvas bracket notation keys
    """
    form_data: dict[str, str] = {}

    for criterion_id, assessment in rubric_assessment.items():
        if "points" in assessment:
            form_data[f"rubric_assessment[{criterion_id}][points]"] = str(
                assessment["points"]
            )

        if "rating_id" in assessment:
            form_data[f"rubric_assessment[{criterion_id}][rating_id]"] = str(
                assessment["rating_id"]
            )

        if "comments" in assessment:
            form_data[f"rubric_assessment[{criterion_id}][comments]"] = str(
                assessment["comments"]
            )

    if comment:
        form_data["comment[text_comment]"] = comment

    return form_data


async def _grade_single_submission_individual(
    course_id: str, assignment_id_str: str, user_id: str, grade_info: dict[str, Any]
) -> dict[str, Any]:
    """Grade a single submission via individual PUT request.

    Used for rubric assessments and as fallback when bulk endpoint fails.
    """
    try:
        form_data: dict[str, str] = {}

        if grade_info.get("excused"):
            form_data["submission[excused]"] = "true"
            if "comment" in grade_info:
                form_data["comment[text_comment]"] = grade_info["comment"]
        elif "rubric_assessment" in grade_info and grade_info["rubric_assessment"]:
            form_data = build_rubric_assessment_form_data(
                grade_info["rubric_assessment"], grade_info.get("comment")
            )
        elif "grade" in grade_info:
            form_data["submission[posted_grade]"] = str(grade_info["grade"])
            if "comment" in grade_info:
                form_data["comment[text_comment]"] = grade_info["comment"]
        else:
            return {
                "status": "failed",
                "user_id": user_id,
                "error": "Must provide rubric_assessment, grade, or excused",
            }

        response = await make_canvas_request(
            "put",
            f"/courses/{course_id}/assignments/{assignment_id_str}/submissions/{user_id}",
            data=form_data,
            use_form_data=True,
        )

        if "error" in response:
            return {"status": "failed", "user_id": user_id, "error": response["error"]}

        if response.get("excused"):
            return {
                "status": "success",
                "user_id": user_id,
                "message": "Marked as excused",
            }
        return {
            "status": "success",
            "user_id": user_id,
            "message": f"Graded: {response.get('grade', 'N/A')}",
            "grade": response.get("grade", "N/A"),
        }

    except Exception as e:
        return {"status": "failed", "user_id": user_id, "error": str(e)}


def register_rubric_grading_tools(mcp: FastMCP) -> None:
    """Register rubric grading MCP tools."""

    @mcp.tool()
    @validate_params
    async def get_submission_rubric_assessment(
        course_identifier: str | int, assignment_id: str | int, user_id: str | int
    ) -> str:
        """Get rubric assessment scores for a specific submission.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID of the student
        """
        course_id = await get_course_id(course_identifier)
        assignment_id_str = str(assignment_id)
        user_id_str = str(user_id)

        # Get submission with rubric assessment
        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id_str}/submissions/{user_id_str}",
            params={"include[]": ["rubric_assessment", "full_rubric_assessment"]},
        )

        if "error" in response:
            return f"Error fetching submission rubric assessment: {response['error']}"

        # Anonymize submission data to protect student privacy
        try:
            response = anonymize_response_data(response, data_type="submissions")
        except Exception as e:
            log_error(
                "Failed to anonymize rubric assessment data",
                exc=e,
                course_id=course_id,
                assignment_id=assignment_id,
                user_id=user_id,
            )
            # Continue with original data for functionality

        # Check if submission has rubric assessment
        rubric_assessment = response.get("rubric_assessment")

        if not rubric_assessment:
            # Get user and assignment names for better error message
            assignment_response = await make_canvas_request(
                "get", f"/courses/{course_id}/assignments/{assignment_id_str}"
            )
            assignment_name = (
                assignment_response.get("name", "Unknown Assignment")
                if "error" not in assignment_response
                else "Unknown Assignment"
            )

            course_display = await get_course_code(course_id) or course_identifier
            return f"No rubric assessment found for user {user_id} on assignment '{assignment_name}' in course {course_display}."

        # Get assignment details for context
        assignment_response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id_str}",
            params={"include[]": ["rubric"]},
        )

        assignment_name = (
            assignment_response.get("name", "Unknown Assignment")
            if "error" not in assignment_response
            else "Unknown Assignment"
        )
        rubric_data = (
            assignment_response.get("rubric", [])
            if "error" not in assignment_response
            else []
        )

        # Format rubric assessment
        course_display = await get_course_code(course_id) or course_identifier

        result = f"Rubric Assessment for User {user_id} on '{assignment_name}' in Course {course_display}:\n\n"

        # Submission details
        submitted_at = format_date(response.get("submitted_at"))
        graded_at = format_date(response.get("graded_at"))
        score = response.get("score", "Not graded")

        result += "Submission Details:\n"
        result += f"  Submitted: {submitted_at}\n"
        result += f"  Graded: {graded_at}\n"
        result += f"  Score: {score}\n\n"

        # Rubric assessment details
        result += "Rubric Assessment:\n"
        result += "=" * 30 + "\n"

        total_rubric_points = 0

        for criterion_id, assessment in rubric_assessment.items():
            # Find criterion details from rubric data
            criterion_info = None
            for criterion in rubric_data:
                if str(criterion.get("id")) == str(criterion_id):
                    criterion_info = criterion
                    break

            criterion_description = (
                criterion_info.get("description", f"Criterion {criterion_id}")
                if criterion_info
                else f"Criterion {criterion_id}"
            )
            points = assessment.get("points", 0)
            comments = assessment.get("comments", "")
            rating_id = assessment.get("rating_id")

            result += f"\n{criterion_description}:\n"
            result += f"  Points Awarded: {points}\n"

            if rating_id and criterion_info:
                # Find the rating description
                for rating in criterion_info.get("ratings", []):
                    if str(rating.get("id")) == str(rating_id):
                        result += f"  Rating: {rating.get('description', 'N/A')} ({rating.get('points', 0)} pts)\n"
                        break

            if comments:
                result += f"  Comments: {comments}\n"

            total_rubric_points += points

        result += f"\nTotal Rubric Points: {total_rubric_points}"

        return result

    @mcp.tool()
    @validate_params
    async def grade_with_rubric(
        course_identifier: str | int,
        assignment_id: str | int,
        user_id: str | int,
        rubric_assessment: dict[str, Any],
        comment: str | None = None,
    ) -> str:
        """Submit grades using rubric criteria.

        This tool submits grades for individual rubric criteria. The rubric must already be
        associated with the assignment and configured for grading (use_for_grading=true).

        IMPORTANT NOTES:
        - Criterion IDs often start with underscore (e.g., "_8027")
        - Use list_assignment_rubrics or get_rubric_details to find criterion IDs and rating IDs
        - Points must be within the range defined by the rubric criterion
        - The rubric must be attached to the assignment before grading

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
            user_id: The Canvas user ID of the student
            rubric_assessment: Dict mapping criterion IDs to assessment data
                             Format: {
                               "criterion_id": {
                                 "points": <number>,           # Required: points awarded
                                 "rating_id": "<string>",      # Optional: specific rating ID
                                 "comments": "<string>"        # Optional: feedback comments
                               }
                             }
            comment: Optional overall comment for the submission

        Example Usage:
            {
              "course_identifier": "60366",
              "assignment_id": "1440586",
              "user_id": "9824",
              "rubric_assessment": {
                "_8027": {
                  "points": 2,
                  "rating_id": "blank",
                  "comments": "Great work!"
                }
              },
              "comment": "Nice job on this assignment"
            }
        """
        course_id = await get_course_id(course_identifier)
        if course_id is None:
            return f"Error: Could not resolve course '{course_identifier}'"
        assignment_id_str = str(assignment_id)
        user_id_str = str(user_id)

        # CRITICAL: Verify rubric is configured for grading BEFORE submitting
        assignment_check = await make_canvas_request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id_str}",
            params={"include[]": ["rubric_settings"]},
        )

        if "error" not in assignment_check:
            use_rubric_for_grading = assignment_check.get(
                "use_rubric_for_grading", False
            )
            if not use_rubric_for_grading:
                return (
                    "⚠️  ERROR: Rubric is not configured for grading!\n\n"
                    "The rubric exists but 'use_for_grading' is set to FALSE.\n"
                    "Grades will NOT be saved to the gradebook.\n\n"
                    "To fix this:\n"
                    "1. Use list_assignment_rubrics to verify rubric settings\n"
                    "2. Use associate_rubric_with_assignment with use_for_grading=True\n"
                    "3. Or configure the rubric in Canvas UI: Assignment Settings → Rubric → Use for Grading\n\n"
                    f"Assignment: {assignment_check.get('name', 'Unknown')}\n"
                    f"Course ID: {course_id}\n"
                    f"Assignment ID: {assignment_id}\n"
                )

        # Build form data in Canvas's expected format
        form_data = build_rubric_assessment_form_data(rubric_assessment, comment)

        # Submit the grade with rubric assessment using form encoding
        response = await make_canvas_request(
            "put",
            f"/courses/{course_id}/assignments/{assignment_id_str}/submissions/{user_id_str}",
            data=form_data,
            use_form_data=True,
        )

        if "error" in response:
            return f"Error submitting rubric grade: {response['error']}"

        # Get assignment details for confirmation
        assignment_response = await make_canvas_request(
            "get", f"/courses/{course_id}/assignments/{assignment_id_str}"
        )
        assignment_name = (
            assignment_response.get("name", "Unknown Assignment")
            if "error" not in assignment_response
            else "Unknown Assignment"
        )

        # Calculate total points from rubric assessment
        total_points = sum(
            criterion.get("points", 0) for criterion in rubric_assessment.values()
        )

        course_display = await get_course_code(course_id) or course_identifier

        result = "Rubric Grade Submitted Successfully!\n\n"
        result += f"Course: {course_display}\n"
        result += f"Assignment: {assignment_name}\n"
        result += f"Student ID: {user_id}\n"
        result += f"Total Rubric Points: {total_points}\n"
        result += f"Grade: {response.get('grade', 'N/A')}\n"
        result += f"Score: {response.get('score', 'N/A')}\n"
        result += f"Graded At: {format_date(response.get('graded_at'))}\n"

        if comment:
            result += f"Overall Comment: {comment}\n"

        result += "\nRubric Assessment Summary:\n"
        for criterion_id, assessment in rubric_assessment.items():
            points = assessment.get("points", 0)
            rating_id = assessment.get("rating_id", "")
            comments = assessment.get("comments", "")
            result += f"  Criterion {criterion_id}: {points} points"
            if rating_id:
                result += f" (Rating: {rating_id})"
            if comments:
                result += f"\n    Comment: {truncate_text(comments, 100)}"
            result += "\n"

        return result

    @mcp.tool()
    @validate_params
    async def bulk_grade_submissions(
        course_identifier: str | int,
        assignment_id: str | int,
        grades: dict[str, Any],
        dry_run: bool = False,
        max_concurrent: int = 5,
        rate_limit_delay: float = 1.0,
    ) -> str:
        """Grade multiple submissions efficiently using Canvas's native bulk endpoint.

        Uses a single API call for simple grades (points, percentages, letter grades,
        excused) via Canvas's bulk update endpoint. Rubric-based grades automatically
        fall back to individual API calls since the bulk endpoint doesn't support them.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            assignment_id: The Canvas assignment ID
            grades: Dictionary mapping user IDs to grade information
                   Format: {
                     "user_id": {
                       "rubric_assessment": {...},  # Optional: rubric-based grading (individual calls)
                       "grade": <number|string>,    # Optional: points, "85%", "A-", "pass", "fail", etc.
                       "excused": true,             # Optional: mark as excused (no grade impact)
                       "comment": "<string>"        # Optional: feedback comment
                     }
                   }
            dry_run: If True, analyze but don't actually submit grades (for testing)
            max_concurrent: Maximum concurrent operations for rubric fallback (default: 5)
            rate_limit_delay: Delay between rubric batches in seconds (default: 1.0)

        Example Usage - Simple Grading (uses bulk endpoint - 1 API call):
            {
              "course_identifier": "60366",
              "assignment_id": "1440586",
              "grades": {
                "9824": {"grade": 100, "comment": "Perfect!"},
                "9825": {"grade": 85, "comment": "Very good"}
              }
            }

        Example Usage - Rubric Grading (uses individual calls):
            {
              "course_identifier": "60366",
              "assignment_id": "1440586",
              "grades": {
                "9824": {
                  "rubric_assessment": {
                    "_8027": {"points": 100, "comments": "Excellent work!"}
                  },
                  "comment": "Great job!"
                }
              },
              "dry_run": true
            }

        Example Usage - Excused:
            {
              "course_identifier": "60366",
              "assignment_id": "1440586",
              "grades": {
                "9824": {"excused": true},
                "9825": {"grade": "incomplete", "comment": "Did not submit"}
              }
            }
        """
        import asyncio

        course_id = await get_course_id(course_identifier)
        if course_id is None:
            return f"Error: Could not resolve course '{course_identifier}'"
        assignment_id_str = str(assignment_id)

        if not grades:
            return "Error: No grades provided. The grades dictionary is empty."

        # Partition grades: bulk-eligible vs rubric-requiring
        bulk_grades: dict[str, dict[str, Any]] = {}
        rubric_grades: dict[str, dict[str, Any]] = {}

        for user_id, grade_info in grades.items():
            if "rubric_assessment" in grade_info and grade_info["rubric_assessment"]:
                rubric_grades[user_id] = grade_info
            else:
                bulk_grades[user_id] = grade_info

        # Validate rubric config if needed
        if rubric_grades:
            assignment_check = await make_canvas_request(
                "get",
                f"/courses/{course_id}/assignments/{assignment_id_str}",
                params={"include[]": ["rubric_settings"]},
            )
            if "error" not in assignment_check:
                use_rubric_for_grading = assignment_check.get(
                    "use_rubric_for_grading", False
                )
                if not use_rubric_for_grading and not dry_run:
                    return (
                        "ERROR: Rubric is not configured for grading!\n\n"
                        "The rubric exists but 'use_for_grading' is set to FALSE.\n"
                        "Grades will NOT be saved to the gradebook.\n\n"
                        "To fix this:\n"
                        "1. Use list_assignment_rubrics to verify rubric settings\n"
                        "2. Use associate_rubric_with_assignment with use_for_grading=True\n"
                        "3. Or set dry_run=True to test without submitting\n"
                    )

        # Statistics tracking
        stats = {"total": len(grades), "graded": 0, "failed": 0}
        failed_results: list[dict[str, str]] = []
        result_lines: list[str] = []

        result_lines.append(f"{'=' * 60}")
        result_lines.append(
            f"Bulk Grading {'(DRY RUN) ' if dry_run else ''}for Assignment {assignment_id}"
        )
        result_lines.append(f"{'=' * 60}")
        result_lines.append(
            f"Course: {await get_course_code(course_id) or course_identifier}"
        )
        result_lines.append(f"Total submissions: {stats['total']}")
        if bulk_grades:
            result_lines.append(f"  Via bulk endpoint: {len(bulk_grades)}")
        if rubric_grades:
            result_lines.append(
                f"  Via individual calls (rubric): {len(rubric_grades)}"
            )
        result_lines.append("")

        # --- Process bulk-eligible grades ---
        if bulk_grades:
            if dry_run:
                for user_id, grade_info in bulk_grades.items():
                    if grade_info.get("excused"):
                        result_lines.append(
                            f"  DRY RUN User {user_id}: Would mark as excused"
                        )
                        stats["graded"] += 1
                    elif "grade" in grade_info:
                        result_lines.append(
                            f"  DRY RUN User {user_id}: Would grade with {grade_info['grade']}"
                        )
                        stats["graded"] += 1
                    else:
                        result_lines.append(
                            f"  DRY RUN User {user_id}: No grade or excused provided"
                        )
                        stats["failed"] += 1
                        failed_results.append(
                            {"user_id": user_id, "error": "No grade or excused"}
                        )
            else:
                form_data = build_bulk_grade_form_data(bulk_grades)
                result_lines.append(
                    f"Submitting {len(bulk_grades)} grades via bulk endpoint..."
                )

                response = await make_canvas_request(
                    "post",
                    f"/courses/{course_id}/assignments/{assignment_id_str}/submissions/update_grades",
                    data=form_data,
                    use_form_data=True,
                )

                if isinstance(response, dict) and "error" in response:
                    # Bulk endpoint failed — fall back to individual calls
                    result_lines.append(f"  Bulk endpoint error: {response['error']}")
                    result_lines.append("  Falling back to individual API calls...")

                    for user_id, grade_info in bulk_grades.items():
                        individual_result = await _grade_single_submission_individual(
                            course_id, assignment_id_str, user_id, grade_info
                        )
                        if individual_result["status"] == "success":
                            stats["graded"] += 1
                            result_lines.append(
                                f"  [ok] User {user_id}: {individual_result.get('message', 'Graded')}"
                            )
                        else:
                            stats["failed"] += 1
                            failed_results.append(
                                {
                                    "user_id": user_id,
                                    "error": individual_result["error"],
                                }
                            )
                            result_lines.append(
                                f"  [fail] User {user_id}: {individual_result['error']}"
                            )
                else:
                    # Got a Progress object — poll for completion
                    progress_url = response.get("url") or response.get("id")
                    if progress_url:
                        result_lines.append(
                            f"  Bulk request accepted (Progress ID: {response.get('id')})"
                        )
                        result_lines.append("  Polling for completion...")

                        progress_result = await poll_canvas_progress(progress_url)

                        if (
                            progress_result["completed"]
                            and progress_result["workflow_state"] == "completed"
                        ):
                            stats["graded"] += len(bulk_grades)
                            result_lines.append(
                                f"  Bulk grading completed! ({len(bulk_grades)} submissions)"
                            )
                        elif progress_result["workflow_state"] == "failed":
                            result_lines.append(
                                f"  Bulk grading FAILED: {progress_result.get('error', 'unknown')}"
                            )
                            result_lines.append(
                                "  Falling back to individual API calls..."
                            )
                            for uid in bulk_grades:
                                individual_result = (
                                    await _grade_single_submission_individual(
                                        course_id,
                                        assignment_id_str,
                                        uid,
                                        bulk_grades[uid],
                                    )
                                )
                                if individual_result["status"] == "success":
                                    stats["graded"] += 1
                                    result_lines.append(
                                        f"  [ok] User {uid}: {individual_result.get('message', 'Graded')}"
                                    )
                                else:
                                    stats["failed"] += 1
                                    failed_results.append(
                                        {
                                            "user_id": uid,
                                            "error": individual_result["error"],
                                        }
                                    )
                                    result_lines.append(
                                        f"  [fail] User {uid}: {individual_result['error']}"
                                    )
                        else:
                            # Timeout — operation still in progress
                            result_lines.append(
                                "  Bulk grading still in progress after timeout."
                            )
                            result_lines.append(
                                f"  Progress ID: {progress_result['progress_id']}"
                            )
                            # Count as graded since Canvas is processing
                            stats["graded"] += len(bulk_grades)
                    else:
                        stats["failed"] += len(bulk_grades)
                        result_lines.append(
                            f"  Unexpected response from bulk endpoint: {response}"
                        )
                        for uid in bulk_grades:
                            failed_results.append(
                                {"user_id": uid, "error": "Unexpected response"}
                            )

        # --- Process rubric-requiring grades (individual PUT calls) ---
        if rubric_grades:
            if dry_run:
                for user_id, grade_info in rubric_grades.items():
                    total_points = sum(
                        criterion.get("points", 0)
                        for criterion in grade_info["rubric_assessment"].values()
                    )
                    result_lines.append(
                        f"  DRY RUN User {user_id}: Would grade with {total_points} rubric points"
                    )
                    stats["graded"] += 1
            else:
                result_lines.append(
                    f"\nProcessing {len(rubric_grades)} rubric grades via individual calls..."
                )
                user_ids = list(rubric_grades.keys())
                total_batches = (len(user_ids) + max_concurrent - 1) // max_concurrent

                for i in range(0, len(user_ids), max_concurrent):
                    batch = user_ids[i : i + max_concurrent]
                    batch_num = (i // max_concurrent) + 1
                    result_lines.append(
                        f"  Rubric batch {batch_num}/{total_batches} ({len(batch)} submissions)..."
                    )

                    tasks = [
                        _grade_single_submission_individual(
                            course_id, assignment_id_str, uid, rubric_grades[uid]
                        )
                        for uid in batch
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for raw_result in results:
                        if isinstance(raw_result, BaseException):
                            stats["failed"] += 1
                            failed_results.append(
                                {"user_id": "unknown", "error": str(raw_result)}
                            )
                            continue
                        result = raw_result
                        if result["status"] == "success":
                            stats["graded"] += 1
                            result_lines.append(
                                f"    [ok] User {result['user_id']}: {result.get('message', 'Graded')}"
                            )
                        else:
                            stats["failed"] += 1
                            failed_results.append(
                                {"user_id": result["user_id"], "error": result["error"]}
                            )
                            result_lines.append(
                                f"    [fail] User {result['user_id']}: {result['error']}"
                            )

                    if i + max_concurrent < len(user_ids):
                        await asyncio.sleep(rate_limit_delay)

        # Summary
        result_lines.append(f"\n{'=' * 60}")
        result_lines.append(f"Bulk Grading {'(DRY RUN) ' if dry_run else ''}Complete!")
        result_lines.append(f"{'=' * 60}")
        result_lines.append(f"Total:   {stats['total']}")
        result_lines.append(f"Graded:  {stats['graded']}")
        result_lines.append(f"Failed:  {stats['failed']}")
        if bulk_grades and not dry_run:
            result_lines.append(
                f"\nMethod: {len(bulk_grades)} via bulk endpoint, "
                f"{len(rubric_grades)} via individual API calls"
            )

        if failed_results:
            result_lines.append("\nFailed Submissions:")
            for failure in failed_results[:10]:
                result_lines.append(f"  User {failure['user_id']}: {failure['error']}")
            if len(failed_results) > 10:
                result_lines.append(
                    f"  ... and {len(failed_results) - 10} more failures"
                )

        if dry_run:
            result_lines.append("\nDRY RUN MODE: No grades were actually submitted")
            result_lines.append("Set dry_run=false to apply grades")

        return "\n".join(result_lines)
