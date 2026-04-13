"""
Tests for grading_export MCP tool.

Includes tests for:
- grading_export (bulk submission export with filters)
- _load_gender_map (CSV loading)
- _resolve_courses (period code resolution)
- _parse_grade_filter (grade range parsing)
"""

import json
from unittest.mock import patch

import pytest

from canvas_mcp.tools.grading_export import (
    PERIOD_COURSE_MAP,
    _load_gender_map,
    _parse_grade_filter,
    _resolve_courses,
)

# --- Helper to capture tool functions ---


def get_tool_function(tool_name: str):
    """Get a tool function by name from the registered tools."""
    from mcp.server.fastmcp import FastMCP

    from canvas_mcp.tools.grading_export import register_grading_export_tools

    mcp = FastMCP("test")
    captured_functions = {}

    original_tool = mcp.tool

    def capturing_tool(*args, **kwargs):
        decorator = original_tool(*args, **kwargs)

        def wrapper(fn):
            captured_functions[fn.__name__] = fn
            return decorator(fn)

        return wrapper

    mcp.tool = capturing_tool
    register_grading_export_tools(mcp)

    return captured_functions.get(tool_name)


# --- Fixtures ---

SAMPLE_STUDENTS = [
    {"id": 2146, "name": "Orien Amede"},
    {"id": 2200, "name": "Sophia Garcia"},
    {"id": 2300, "name": "Liam Chen"},
]

SAMPLE_ASSIGNMENT_GROUPS = [
    {"id": 100, "name": "Classwork"},
    {"id": 200, "name": "Tests"},
]

SAMPLE_ASSIGNMENTS = [
    {
        "id": 12345,
        "name": "Genetics L6 - 3 Day Classwork",
        "assignment_group_id": 100,
        "due_at": "2026-03-10T23:59:00Z",
        "points_possible": 10,
        "grading_type": "points",
        "submission_types": ["online_upload"],
        "published": True,
    },
    {
        "id": 12346,
        "name": "Unit Test - Genetics",
        "assignment_group_id": 200,
        "due_at": "2026-03-15T23:59:00Z",
        "points_possible": 100,
        "grading_type": "points",
        "submission_types": ["online_upload"],
        "published": True,
    },
]

SAMPLE_SUBMISSIONS = [
    {
        "user_id": 2146,
        "assignment_id": 12345,
        "submitted_at": "2026-03-10T14:30:00Z",
        "workflow_state": "submitted",
        "score": None,
        "grade": None,
        "late": False,
        "missing": False,
        "excused": False,
        "submission_type": "online_upload",
        "attempt": 1,
        "graded_at": None,
    },
    {
        "user_id": 2200,
        "assignment_id": 12345,
        "submitted_at": "2026-03-11T10:00:00Z",
        "workflow_state": "graded",
        "score": 8,
        "grade": "8",
        "late": True,
        "missing": False,
        "excused": False,
        "submission_type": "online_upload",
        "attempt": 1,
        "graded_at": "2026-03-12T09:00:00Z",
    },
    {
        "user_id": 2300,
        "assignment_id": 12345,
        "submitted_at": None,
        "workflow_state": "unsubmitted",
        "score": None,
        "grade": None,
        "late": False,
        "missing": True,
        "excused": False,
        "submission_type": None,
        "attempt": 0,
        "graded_at": None,
    },
]

SAMPLE_GENDER_CSV = (
    "real_name,real_id,real_email,anonymous_id,gender\n"
    "Orien Amede,2146,orien@example.com,Student_2570ce03,M\n"
    "Sophia Garcia,2200,sophia@example.com,Student_abc12345,F\n"
    "Liam Chen,2300,liam@example.com,Student_def67890,M\n"
)


@pytest.fixture
def mock_canvas_api():
    """Fixture to mock Canvas API calls for grading_export."""
    with (
        patch(
            "canvas_mcp.tools.grading_export.fetch_all_paginated_results"
        ) as mock_fetch,
        patch("canvas_mcp.tools.grading_export.make_canvas_request") as mock_request,
    ):
        yield {
            "fetch_all_paginated_results": mock_fetch,
            "make_canvas_request": mock_request,
        }


@pytest.fixture
def mock_gender_csv(tmp_path):
    """Create a temporary gender CSV file and patch the path."""
    csv_path = tmp_path / "anonymization_map_P1-Science8-Cottone.csv"
    csv_path.write_text(SAMPLE_GENDER_CSV)
    return tmp_path


# --- Unit tests for helper functions ---


class TestResolveCourses:
    """Tests for _resolve_courses helper."""

    def test_single_period(self):
        result = _resolve_courses("P1")
        assert result == [("P1", 8668)]

    def test_single_period_lowercase(self):
        result = _resolve_courses("p3")
        assert result == [("P3", 8670)]

    def test_all_courses(self):
        result = _resolve_courses("all")
        assert len(result) == len(PERIOD_COURSE_MAP)
        assert ("P1", 8668) in result

    def test_all_courses_case_insensitive(self):
        result = _resolve_courses("ALL")
        assert len(result) == len(PERIOD_COURSE_MAP)

    def test_unknown_period(self):
        with pytest.raises(ValueError, match="Unknown course"):
            _resolve_courses("P2")

    def test_whitespace_handling(self):
        result = _resolve_courses("  P1  ")
        assert result == [("P1", 8668)]


class TestParseGradeFilter:
    """Tests for _parse_grade_filter helper."""

    def test_single_value(self):
        assert _parse_grade_filter("70") == (70.0, 70.0)

    def test_range(self):
        assert _parse_grade_filter("0-70") == (0.0, 70.0)

    def test_high_range(self):
        assert _parse_grade_filter("80-100") == (80.0, 100.0)

    def test_zero(self):
        assert _parse_grade_filter("0") == (0.0, 0.0)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_grade_filter("abc")


class TestLoadGenderMap:
    """Tests for _load_gender_map helper."""

    def test_loads_csv_correctly(self, mock_gender_csv):
        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            result = _load_gender_map(["P1"])
        assert result[2146] == "M"
        assert result[2200] == "F"
        assert result[2300] == "M"

    def test_missing_csv_returns_empty(self, tmp_path):
        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", tmp_path):
            result = _load_gender_map(["P1"])
        assert result == {}

    def test_multiple_periods(self, mock_gender_csv):
        # Create a second CSV
        csv2 = mock_gender_csv / "anonymization_map_P3-Science8-Cottone.csv"
        csv2.write_text(
            "real_name,real_id,real_email,anonymous_id,gender\n"
            "Extra Student,9999,extra@example.com,Student_zzz,F\n"
        )
        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            result = _load_gender_map(["P1", "P3"])
        assert 2146 in result
        assert 9999 in result
        assert result[9999] == "F"


# --- Integration tests for grading_export tool ---


class TestGradingExport:
    """Tests for grading_export tool."""

    @pytest.mark.asyncio
    async def test_single_course_single_assignment(
        self, mock_canvas_api, mock_gender_csv
    ):
        """Test basic export with one course and one assignment filter."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            # assignment_groups
            SAMPLE_ASSIGNMENT_GROUPS,
            # assignments
            SAMPLE_ASSIGNMENTS,
            # students
            SAMPLE_STUDENTS,
            # submissions batch
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(course="P1", assignment="Genetics L6")

        data = json.loads(result)
        assert data["export_meta"]["total_assignments"] == 1
        assert data["export_meta"]["total_submissions"] == 3
        assert data["export_meta"]["courses_included"] == ["P1"]
        assert (
            data["assignments"][0]["assignment_name"] == "Genetics L6 - 3 Day Classwork"
        )
        assert data["assignments"][0]["period"] == "P1"

    @pytest.mark.asyncio
    async def test_ungraded_only_filter(self, mock_canvas_api, mock_gender_csv):
        """Test that ungraded_only filters to submissions with no score."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", ungraded_only=True
            )

        data = json.loads(result)
        # Only student 2146 has score=None and submitted_at is not None
        assert data["export_meta"]["total_submissions"] == 1
        sub = data["assignments"][0]["submissions"][0]
        assert sub["student_id"] == 2146
        assert sub["score"] is None

    @pytest.mark.asyncio
    async def test_late_only_filter(self, mock_canvas_api, mock_gender_csv):
        """Test that late_only filters to late submissions."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", late_only=True
            )

        data = json.loads(result)
        assert data["export_meta"]["total_submissions"] == 1
        assert data["assignments"][0]["submissions"][0]["student_id"] == 2200
        assert data["assignments"][0]["submissions"][0]["late"] is True

    @pytest.mark.asyncio
    async def test_gender_filter(self, mock_canvas_api, mock_gender_csv):
        """Test that gender filter cross-references CSV data."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", gender="F"
            )

        data = json.loads(result)
        # Only Sophia Garcia (2200) is F
        assert data["export_meta"]["total_submissions"] == 1
        assert data["assignments"][0]["submissions"][0]["student_id"] == 2200
        assert data["assignments"][0]["submissions"][0]["gender"] == "F"

    @pytest.mark.asyncio
    async def test_assignment_group_filter(self, mock_canvas_api, mock_gender_csv):
        """Test filtering by assignment group name."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,  # Only one batch since only 1 assignment matches
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(course="P1", assignment_group="Classwork")

        data = json.loads(result)
        # Only "Genetics L6" is in the Classwork group
        for a in data["assignments"]:
            assert a["assignment_group"] == "Classwork"

    @pytest.mark.asyncio
    async def test_grade_range_filter(self, mock_canvas_api, mock_gender_csv):
        """Test filtering by grade percentage range."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", grade="70-100"
            )

        data = json.loads(result)
        # Student 2200 has score=8/10 = 80%, which is in range 70-100
        assert data["export_meta"]["total_submissions"] == 1
        assert data["assignments"][0]["submissions"][0]["score_percentage"] == 80

    @pytest.mark.asyncio
    async def test_excused_filter(self, mock_canvas_api, mock_gender_csv):
        """Test filtering for excused submissions."""
        excused_submissions = [
            {**SAMPLE_SUBMISSIONS[0], "excused": True, "score": None, "grade": None},
            SAMPLE_SUBMISSIONS[1],
        ]
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            excused_submissions,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", excused=True
            )

        data = json.loads(result)
        assert data["export_meta"]["total_submissions"] == 1
        assert data["assignments"][0]["submissions"][0]["excused"] is True

    @pytest.mark.asyncio
    async def test_student_filter_by_name(self, mock_canvas_api, mock_gender_csv):
        """Test filtering by student name substring."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", student="Sophia"
            )

        data = json.loads(result)
        assert data["export_meta"]["total_submissions"] == 1
        assert (
            data["assignments"][0]["submissions"][0]["student_name"] == "Sophia Garcia"
        )

    @pytest.mark.asyncio
    async def test_resubmissions_filter(self, mock_canvas_api, mock_gender_csv):
        """Test filtering for resubmissions (submitted_at > graded_at)."""
        resub_submissions = [
            {
                "user_id": 2146,
                "assignment_id": 12345,
                "submitted_at": "2026-03-14T10:00:00Z",
                "workflow_state": "graded",
                "score": 0,
                "grade": "0",
                "late": False,
                "missing": False,
                "excused": False,
                "submission_type": "online_upload",
                "attempt": 2,
                "graded_at": "2026-03-12T09:00:00Z",  # graded BEFORE resubmission
            },
            SAMPLE_SUBMISSIONS[1],  # normal graded, not resubmitted
        ]
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            resub_submissions,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", resubmissions=True
            )

        data = json.loads(result)
        assert data["export_meta"]["total_submissions"] == 1
        assert data["assignments"][0]["submissions"][0]["resubmitted"] is True

    @pytest.mark.asyncio
    async def test_submission_state_filter(self, mock_canvas_api, mock_gender_csv):
        """Test filtering by workflow state."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", submission_state="graded"
            )

        data = json.loads(result)
        assert data["export_meta"]["total_submissions"] == 1
        assert data["assignments"][0]["submissions"][0]["workflow_state"] == "graded"

    @pytest.mark.asyncio
    async def test_derived_fields(self, mock_canvas_api, mock_gender_csv):
        """Test that derived fields (days_late, score_percentage, resubmitted) are correct."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(course="P1", assignment="Genetics L6")

        data = json.loads(result)
        subs = {s["student_id"]: s for s in data["assignments"][0]["submissions"]}

        # Student 2200: score=8, max_points=10 → 80%
        assert subs[2200]["score_percentage"] == 80
        # Student 2200: submitted 2026-03-11, due 2026-03-10 → 1 day late
        assert subs[2200]["days_late"] == 1
        # Student 2200: graded_at > submitted_at → not resubmitted
        assert subs[2200]["resubmitted"] is False
        # Student 2146: no score → null percentage
        assert subs[2146]["score_percentage"] is None

    @pytest.mark.asyncio
    async def test_gender_null_for_unknown_student(self, mock_canvas_api, tmp_path):
        """Test that students not in CSV get gender=null."""
        # Empty CSV directory
        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", tmp_path):
            mock_canvas_api["fetch_all_paginated_results"].side_effect = [
                SAMPLE_ASSIGNMENT_GROUPS,
                [SAMPLE_ASSIGNMENTS[0]],  # one assignment
                SAMPLE_STUDENTS,
                [SAMPLE_SUBMISSIONS[0]],  # one submission
            ]

            grading_export = get_tool_function("grading_export")
            result = await grading_export(course="P1", assignment="Genetics L6")

        data = json.loads(result)
        assert data["assignments"][0]["submissions"][0]["gender"] is None

    @pytest.mark.asyncio
    async def test_unknown_course_returns_error(self, mock_canvas_api, mock_gender_csv):
        """Test that an unknown course returns a JSON error."""
        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(course="P2")

        data = json.loads(result)
        assert "error" in data
        assert "Unknown course" in data["error"]

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_canvas_api, mock_gender_csv):
        """Test that no matching data returns empty assignments list."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            [],  # no submissions
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(course="P1", assignment="Genetics L6")

        data = json.loads(result)
        assert data["export_meta"]["total_assignments"] == 0
        assert data["export_meta"]["total_submissions"] == 0
        assert data["assignments"] == []

    @pytest.mark.asyncio
    async def test_output_to_file(self, mock_canvas_api, mock_gender_csv, tmp_path):
        """Test writing output to a file."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            [SAMPLE_ASSIGNMENTS[0]],
            SAMPLE_STUDENTS,
            [SAMPLE_SUBMISSIONS[0]],
        ]

        output_path = tmp_path / "export.json"
        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", assignment="Genetics L6", output=str(output_path)
            )

        assert "Exported" in result
        assert "1 submissions" in result

        # Verify file was written with valid JSON
        written_data = json.loads(output_path.read_text())
        assert "export_meta" in written_data
        assert "assignments" in written_data

    @pytest.mark.asyncio
    async def test_api_error_produces_warning(self, mock_canvas_api, mock_gender_csv):
        """Test that API errors are captured as warnings, not crashes."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            {"error": "Rate limit exceeded"},  # assignments fetch fails
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(course="P1")

        data = json.loads(result)
        assert data["export_meta"]["total_assignments"] == 0
        assert "warnings" in data["export_meta"]
        assert any("Rate limit" in w for w in data["export_meta"]["warnings"])

    @pytest.mark.asyncio
    async def test_grading_period_filter(self, mock_canvas_api, mock_gender_csv):
        """Test that grading period filter resolves via API."""
        mock_canvas_api["make_canvas_request"].return_value = {
            "grading_periods": [
                {
                    "id": 501,
                    "title": "Q3 - Third Quarter",
                    "start_date": "2026-01-20",
                    "end_date": "2026-03-28",
                },
            ]
        }
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            await grading_export(course="P1", grading_period="Q3")

        # Verify grading_period_id was passed to assignment fetch
        fetch_calls = mock_canvas_api["fetch_all_paginated_results"].call_args_list
        # Second call is assignments — check params include grading_period_id
        assignment_call_params = fetch_calls[1][0][1]  # second positional arg
        assert assignment_call_params.get("grading_period_id") == 501

    @pytest.mark.asyncio
    async def test_filters_applied_in_metadata(self, mock_canvas_api, mock_gender_csv):
        """Test that applied filters are recorded in export metadata."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            result = await grading_export(
                course="P1", late_only=True, ungraded_only=True
            )

        data = json.loads(result)
        filters = data["export_meta"]["filters_applied"]
        assert filters["course"] == "P1"
        assert filters["late_only"] is True
        assert filters["ungraded_only"] is True

    @pytest.mark.asyncio
    async def test_combined_filters(self, mock_canvas_api, mock_gender_csv):
        """Test that multiple filters combine with AND logic."""
        mock_canvas_api["fetch_all_paginated_results"].side_effect = [
            SAMPLE_ASSIGNMENT_GROUPS,
            SAMPLE_ASSIGNMENTS,
            SAMPLE_STUDENTS,
            SAMPLE_SUBMISSIONS,
        ]

        with patch("canvas_mcp.tools.grading_export.GENDER_CSV_BASE", mock_gender_csv):
            grading_export = get_tool_function("grading_export")
            # late_only=True AND gender=M — no male students are late in our sample
            result = await grading_export(
                course="P1", assignment="Genetics L6", late_only=True, gender="M"
            )

        data = json.loads(result)
        # Student 2200 is late but female, student 2146 is male but not late
        assert data["export_meta"]["total_submissions"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
