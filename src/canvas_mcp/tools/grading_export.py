"""Grading export MCP tool for Canvas API.

Bulk-fetches submission data across courses with flexible filters,
cross-references gender from anonymization CSVs, and outputs structured
JSON for grading workflows.
"""

import csv
import datetime
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..core.client import fetch_all_paginated_results, make_canvas_request
from ..core.dates import parse_date
from ..core.logging import log_warning

# Period code → Canvas course ID mapping (Science 8 - Cottone, roselleschools)
PERIOD_COURSE_MAP: dict[str, int] = {
    "P1": 8668,
    "P3": 8670,
    "P4": 8673,
    "P6": 11587,
    "P7": 8692,
    "P9": 8697,
}

# Reverse lookup: course ID → period code
COURSE_PERIOD_MAP: dict[int, str] = {v: k for k, v in PERIOD_COURSE_MAP.items()}

GENDER_CSV_BASE = Path(
    "/Users/sallvain/Projects/Teaching/Student-Anonymization-Maps-Canvas"
)
GENDER_CSV_PATTERN = "anonymization_map_{period}-Science8-Cottone.csv"


def _load_gender_map(periods: list[str]) -> dict[int, str]:
    """Load gender data from anonymization CSVs for the given periods.

    Returns a dict mapping Canvas student ID (int) → gender string ("M"/"F").
    Students not found in any CSV will be absent from the dict.
    Missing CSV files are silently skipped.
    """
    gender_map: dict[int, str] = {}
    for period in periods:
        filename = GENDER_CSV_PATTERN.format(period=period)
        csv_path = GENDER_CSV_BASE / filename
        if not csv_path.exists():
            log_warning(f"Gender CSV not found: {csv_path}")
            continue
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        student_id = int(row["real_id"])
                        gender = row.get("gender", "").strip()
                        if gender:
                            gender_map[student_id] = gender
                    except (ValueError, KeyError):
                        continue
        except OSError as e:
            log_warning(f"Error reading gender CSV {csv_path}: {e}")
    return gender_map


def _resolve_courses(course_filter: str) -> list[tuple[str, int]]:
    """Resolve course filter to list of (period_code, course_id) tuples.

    Args:
        course_filter: "all" or a period code like "P1", "P3", etc.

    Returns:
        List of (period, course_id) tuples.

    Raises:
        ValueError: If the course filter is not recognized.
    """
    course_upper = course_filter.strip().upper()
    if course_upper == "ALL":
        return list(PERIOD_COURSE_MAP.items())
    if course_upper in PERIOD_COURSE_MAP:
        return [(course_upper, PERIOD_COURSE_MAP[course_upper])]
    raise ValueError(
        f"Unknown course '{course_filter}'. "
        f"Valid values: {', '.join(PERIOD_COURSE_MAP.keys())}, or 'all'"
    )


def _parse_grade_filter(grade_str: str) -> tuple[float, float]:
    """Parse a grade filter string into a (min, max) range.

    Accepts single values ("0", "100") or ranges ("0-70", "80-100").
    """
    grade_str = grade_str.strip()
    if "-" in grade_str and not grade_str.startswith("-"):
        parts = grade_str.split("-", 1)
        return float(parts[0]), float(parts[1])
    val = float(grade_str)
    return val, val


async def _fetch_grading_period_id(course_id: int, period_name: str) -> int | None:
    """Resolve a grading period name (e.g., 'Q3') to a Canvas grading period ID.

    Uses case-insensitive substring matching against period titles.
    Returns None if no match found.
    """
    response = await make_canvas_request(
        "get", f"/courses/{course_id}/grading_periods", skip_anonymization=True
    )
    if isinstance(response, dict) and "error" in response:
        log_warning(
            f"Could not fetch grading periods for course {course_id}: {response['error']}"
        )
        return None

    periods = response.get("grading_periods", []) if isinstance(response, dict) else []
    search = period_name.strip().lower()
    for p in periods:
        title = p.get("title", "").lower()
        if search in title:
            return p.get("id")
    return None


async def _fetch_course_data(
    course_id: int,
    period: str,
    *,
    assignment_filter: str | None,
    assignment_group_filter: str | None,
    grading_period_filter: str | None,
    date_range_filter: str | None,
    student_filter: str | None,
    gender_filter: str | None,
    submission_state_filter: str | None,
    ungraded_only: bool,
    resubmissions_only: bool,
    late_only: bool,
    submission_type_filter: str | None,
    grade_filter: str | None,
    excused_filter: bool | None,
    gender_map: dict[int, str],
    warnings: list[str],
) -> list[dict[str, Any]]:
    """Fetch and filter all data for a single course. Returns list of assignment dicts."""

    # --- Grading period resolution ---
    grading_period_id = None
    if grading_period_filter:
        grading_period_id = await _fetch_grading_period_id(
            course_id, grading_period_filter
        )
        if grading_period_id is None:
            warnings.append(
                f"Grading period '{grading_period_filter}' not found in course {period} ({course_id})"
            )

    # --- Assignment groups ---
    groups_resp = await fetch_all_paginated_results(
        f"/courses/{course_id}/assignment_groups",
        {"per_page": 100},
        skip_anonymization=True,
    )
    group_name_map: dict[int, str] = {}
    if isinstance(groups_resp, list):
        group_name_map = {g["id"]: g.get("name", "") for g in groups_resp if "id" in g}

    # --- Assignments ---
    assignment_params: dict[str, Any] = {"per_page": 100}
    if grading_period_id:
        assignment_params["grading_period_id"] = grading_period_id

    assignments_resp = await fetch_all_paginated_results(
        f"/courses/{course_id}/assignments",
        assignment_params,
        skip_anonymization=True,
    )
    if isinstance(assignments_resp, dict) and "error" in assignments_resp:
        warnings.append(
            f"Error fetching assignments for {period}: {assignments_resp['error']}"
        )
        return []

    assignments: list[dict[str, Any]] = (
        assignments_resp if isinstance(assignments_resp, list) else []
    )

    # --- Assignment-level filters ---
    if assignment_filter:
        # Check if it looks like a Canvas ID (all digits)
        if assignment_filter.strip().isdigit():
            target_id = int(assignment_filter.strip())
            assignments = [a for a in assignments if a.get("id") == target_id]
        else:
            query = assignment_filter.strip().lower()
            assignments = [a for a in assignments if query in a.get("name", "").lower()]

    if assignment_group_filter:
        q = assignment_group_filter.strip()
        if q.isdigit():
            target_gid = int(q)
            assignments = [
                a for a in assignments if a.get("assignment_group_id") == target_gid
            ]
        else:
            query = q.lower()
            matching_group_ids = {
                gid for gid, name in group_name_map.items() if query in name.lower()
            }
            assignments = [
                a for a in assignments if a.get("assignment_group_id") in matching_group_ids
            ]

    if date_range_filter:
        try:
            parts = date_range_filter.split(",", 1)
            range_start = parse_date(parts[0].strip())
            range_end = parse_date(parts[1].strip()) if len(parts) > 1 else None
            filtered = []
            for a in assignments:
                due = parse_date(a.get("due_at"))
                if due is None:
                    continue
                if range_start and due < range_start:
                    continue
                if range_end and due > range_end:
                    continue
                filtered.append(a)
            assignments = filtered
        except (ValueError, IndexError):
            warnings.append(f"Invalid date_range format: {date_range_filter}")

    if not assignments:
        return []

    # --- Students ---
    students_resp = await fetch_all_paginated_results(
        f"/courses/{course_id}/users",
        {"enrollment_type[]": "student", "per_page": 100},
        skip_anonymization=True,
    )
    student_name_map: dict[int, str] = {}
    if isinstance(students_resp, list):
        student_name_map = {
            s["id"]: s.get("name", "Unknown") for s in students_resp if "id" in s
        }

    # --- Student-level pre-filter (for student and gender filters) ---
    allowed_student_ids: set[int] | None = None

    if student_filter:
        if student_filter.strip().isdigit():
            allowed_student_ids = {int(student_filter.strip())}
        else:
            query = student_filter.strip().lower()
            allowed_student_ids = {
                sid for sid, name in student_name_map.items() if query in name.lower()
            }

    if gender_filter:
        gender_upper = gender_filter.strip().upper()
        gender_matches = {
            sid for sid, g in gender_map.items() if g.upper() == gender_upper
        }
        if allowed_student_ids is not None:
            allowed_student_ids &= gender_matches
        else:
            allowed_student_ids = gender_matches

    # --- Submissions (per-assignment fetch) ---
    # Uses the per-assignment endpoint which supports page-based pagination,
    # unlike /students/submissions which requires cursor-based pagination
    # that fetch_all_paginated_results doesn't support.
    assignment_ids = [a["id"] for a in assignments if "id" in a]
    subs_by_assignment: dict[int, list[dict[str, Any]]] = {
        aid: [] for aid in assignment_ids
    }

    for aid in assignment_ids:
        subs = await fetch_all_paginated_results(
            f"/courses/{course_id}/assignments/{aid}/submissions",
            {"per_page": 100},
            skip_anonymization=True,
        )
        if isinstance(subs, dict) and "error" in subs:
            warnings.append(
                f"Error fetching submissions for assignment {aid} in {period}: {subs['error']}"
            )
            continue
        if isinstance(subs, list):
            subs_by_assignment[aid] = subs

    # --- Parse grade filter once ---
    grade_range: tuple[float, float] | None = None
    if grade_filter:
        try:
            grade_range = _parse_grade_filter(grade_filter)
        except ValueError:
            warnings.append(f"Invalid grade filter: {grade_filter}")

    # --- Build output ---
    result_assignments: list[dict[str, Any]] = []

    for assignment in assignments:
        aid = assignment["id"]
        max_points = assignment.get("points_possible") or 0
        due_at_str = assignment.get("due_at")
        due_at_dt = parse_date(due_at_str)
        group_id: int | None = assignment.get("assignment_group_id")

        submissions = subs_by_assignment.get(aid, [])
        result_submissions: list[dict[str, Any]] = []

        for sub in submissions:
            student_id = sub.get("user_id")
            if student_id is None:
                continue

            # Student filter
            if (
                allowed_student_ids is not None
                and student_id not in allowed_student_ids
            ):
                continue

            # Submission-level fields
            workflow_state = sub.get("workflow_state", "unsubmitted")
            submitted_at_str = sub.get("submitted_at")
            submitted_at_dt = parse_date(submitted_at_str)
            graded_at_str = sub.get("graded_at")
            graded_at_dt = parse_date(graded_at_str)
            score = sub.get("score")
            grade = sub.get("grade")
            is_late = sub.get("late", False)
            is_missing = sub.get("missing", False)
            is_excused = sub.get("excused", False)
            sub_type = sub.get("submission_type")
            attempt = sub.get("attempt") or 0

            # Derived: score_percentage
            score_pct: int | None = None
            if score is not None and max_points > 0:
                score_pct = round(score / max_points * 100)

            # Derived: resubmitted
            resubmitted = False
            if submitted_at_dt and graded_at_dt and submitted_at_dt > graded_at_dt:
                resubmitted = True

            # Derived: days_late (calendar days, not fractional)
            days_late = 0
            if submitted_at_dt and due_at_dt and submitted_at_dt > due_at_dt:
                sub_date = submitted_at_dt.date()
                due_date = due_at_dt.date()
                days_late = max(0, (sub_date - due_date).days)

            # --- Submission-level filters ---
            if submission_state_filter:
                if workflow_state != submission_state_filter.strip().lower():
                    continue

            if ungraded_only:
                if not (
                    score is None and submitted_at_str is not None and not is_excused
                ):
                    continue

            if resubmissions_only:
                if not resubmitted:
                    continue

            if late_only:
                if not is_late:
                    continue

            if submission_type_filter:
                if sub_type != submission_type_filter.strip().lower():
                    continue

            if grade_range is not None:
                if score_pct is None:
                    continue
                if not (grade_range[0] <= score_pct <= grade_range[1]):
                    continue

            if excused_filter is not None:
                if is_excused != excused_filter:
                    continue

            # --- Build submission record ---
            result_submissions.append(
                {
                    "student_id": student_id,
                    "student_name": student_name_map.get(student_id, "Unknown"),
                    "gender": gender_map.get(student_id),
                    "submitted_at": submitted_at_str,
                    "workflow_state": workflow_state,
                    "days_late": days_late,
                    "grade": grade,
                    "score": score,
                    "score_percentage": score_pct,
                    "submission_type": sub_type,
                    "attempt": attempt,
                    "graded_at": graded_at_str,
                    "resubmitted": resubmitted,
                    "missing": is_missing,
                    "late": is_late,
                    "excused": is_excused,
                }
            )

        # Only include assignments that have matching submissions
        if result_submissions:
            group_name = (
                group_name_map.get(group_id, "Unknown")
                if group_id is not None
                else "Unknown"
            )
            result_assignments.append(
                {
                    "assignment_id": aid,
                    "assignment_name": assignment.get("name", "Unknown"),
                    "assignment_group_id": group_id,
                    "assignment_group": group_name,
                    "course_id": course_id,
                    "period": period,
                    "due_at": due_at_str,
                    "max_points": max_points,
                    "grading_type": assignment.get("grading_type", "points"),
                    "submission_types": assignment.get("submission_types", []),
                    "submissions": result_submissions,
                }
            )

    return result_assignments


def register_grading_export_tools(mcp: FastMCP) -> None:
    """Register grading export MCP tools."""

    @mcp.tool()
    async def grading_export(
        course: str = "all",
        assignment: str | None = None,
        assignment_group: str | None = None,
        student: str | None = None,
        gender: str | None = None,
        submission_state: str | None = None,
        ungraded_only: bool = False,
        resubmissions: bool = False,
        late_only: bool = False,
        date_range: str | None = None,
        grading_period: str | None = None,
        submission_type: str | None = None,
        output: str | None = None,
        grade: str | None = None,
        excused: bool | None = None,
    ) -> str:
        """Bulk-export submission data as JSON for grading workflows.

        Fetches assignments and submissions across courses with flexible,
        combinable filters (AND logic). Cross-references student gender
        from anonymization map CSVs.

        Args:
            course: Period code (P1, P3, P4, P6, P7, P9) or "all". Default: all.
            assignment: Assignment name (fuzzy match) or Canvas ID.
            assignment_group: Assignment group name (e.g., "Classwork", "Tests") or numeric group ID.
            student: Student name (fuzzy match) or Canvas ID.
            gender: M or F. Cross-references anonymization map CSVs.
            submission_state: submitted, graded, unsubmitted, or pending_review.
            ungraded_only: Only submissions awaiting grades.
            resubmissions: Only submissions resubmitted after grading.
            late_only: Only late submissions.
            date_range: Filter assignments by due date. Format: start_date,end_date (ISO 8601).
            grading_period: Q1, Q2, Q3, or Q4. Uses Canvas grading periods API.
            submission_type: online_text_entry, online_upload, or external_tool.
            output: File path to write JSON output. Default: return as tool response.
            grade: Score percentage filter. Single value ("0", "100") or range ("0-70", "80-100").
            excused: Filter for excused (true) or non-excused (false) submissions.
        """
        # Resolve courses
        try:
            courses = _resolve_courses(course)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        # Load gender data
        periods = [p for p, _ in courses]
        gender_map = _load_gender_map(periods)

        # Track filters applied and warnings
        filters_applied: dict[str, Any] = {}
        if course != "all":
            filters_applied["course"] = course
        if assignment:
            filters_applied["assignment"] = assignment
        if assignment_group:
            filters_applied["assignment_group"] = assignment_group
        if student:
            filters_applied["student"] = student
        if gender:
            filters_applied["gender"] = gender
        if submission_state:
            filters_applied["submission_state"] = submission_state
        if ungraded_only:
            filters_applied["ungraded_only"] = True
        if resubmissions:
            filters_applied["resubmissions"] = True
        if late_only:
            filters_applied["late_only"] = True
        if date_range:
            filters_applied["date_range"] = date_range
        if grading_period:
            filters_applied["grading_period"] = grading_period
        if submission_type:
            filters_applied["submission_type"] = submission_type
        if grade:
            filters_applied["grade"] = grade
        if excused is not None:
            filters_applied["excused"] = excused

        warnings: list[str] = []
        all_assignments: list[dict[str, Any]] = []

        for period_code, course_id in courses:
            course_assignments = await _fetch_course_data(
                course_id,
                period_code,
                assignment_filter=assignment,
                assignment_group_filter=assignment_group,
                grading_period_filter=grading_period,
                date_range_filter=date_range,
                student_filter=student,
                gender_filter=gender,
                submission_state_filter=submission_state,
                ungraded_only=ungraded_only,
                resubmissions_only=resubmissions,
                late_only=late_only,
                submission_type_filter=submission_type,
                grade_filter=grade,
                excused_filter=excused,
                gender_map=gender_map,
                warnings=warnings,
            )
            all_assignments.extend(course_assignments)

        # Build output
        total_submissions = sum(len(a["submissions"]) for a in all_assignments)

        result: dict[str, Any] = {
            "export_meta": {
                "timestamp": datetime.datetime.now(datetime.UTC).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "filters_applied": filters_applied,
                "courses_included": [p for p, _ in courses],
                "total_assignments": len(all_assignments),
                "total_submissions": total_submissions,
            },
            "assignments": all_assignments,
        }

        if warnings:
            result["export_meta"]["warnings"] = warnings

        json_output = json.dumps(result, indent=2)

        # Write to file if output path specified
        if output:
            try:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json_output, encoding="utf-8")
                return (
                    f"Exported {total_submissions} submissions across "
                    f"{len(all_assignments)} assignments to {output}"
                )
            except OSError as e:
                return json.dumps({"error": f"Failed to write output file: {e}"})

        return json_output
