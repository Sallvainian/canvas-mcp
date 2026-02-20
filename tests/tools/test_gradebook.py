"""
Tests for gradebook management MCP tools.

Includes tests for:
- export_grades
- get_assignment_groups
- create_assignment_group
- update_assignment_group
- configure_late_policy
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_canvas_api():
    """Fixture to mock Canvas API calls for gradebook tools."""
    with patch('canvas_mcp.tools.gradebook.get_course_id') as mock_get_id, \
         patch('canvas_mcp.tools.gradebook.get_course_code') as mock_get_code, \
         patch('canvas_mcp.tools.gradebook.fetch_all_paginated_results') as mock_fetch, \
         patch('canvas_mcp.tools.gradebook.make_canvas_request') as mock_request:

        mock_get_id.return_value = "12345"
        mock_get_code.return_value = "CS101"

        yield {
            'get_course_id': mock_get_id,
            'get_course_code': mock_get_code,
            'fetch_all_paginated_results': mock_fetch,
            'make_canvas_request': mock_request
        }


def get_tool_function(tool_name: str):
    """Get a tool function by name from the registered tools."""
    from mcp.server.fastmcp import FastMCP
    from canvas_mcp.tools.gradebook import register_gradebook_tools

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
    register_gradebook_tools(mcp)

    return captured_functions.get(tool_name)


class TestExportGrades:
    """Tests for export_grades tool."""

    @pytest.mark.asyncio
    async def test_export_grades_csv_format(self, mock_canvas_api):
        """Test that CSV export has correct headers and data."""
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            # Students
            [
                {"id": 1001, "name": "Alice Smith"},
                {"id": 1002, "name": "Bob Jones"}
            ],
            # Assignments
            [
                {"id": 100, "name": "Homework 1", "points_possible": 50, "published": True},
                {"id": 101, "name": "Midterm", "points_possible": 100, "published": True}
            ],
            # Submissions for assignment 100
            [
                {"user_id": 1001, "score": 45},
                {"user_id": 1002, "score": 48}
            ],
            # Submissions for assignment 101
            [
                {"user_id": 1001, "score": 85},
                {"user_id": 1002, "score": 92}
            ]
        ]

        export_grades = get_tool_function('export_grades')
        result = await export_grades(course_identifier="12345", format="csv")

        assert "Student ID,Student Name" in result
        assert "Homework 1 (50 pts)" in result or "Homework 1" in result
        assert "Midterm (100 pts)" in result or "Midterm" in result
        assert "Alice Smith" in result
        assert "Bob Jones" in result
        assert "45" in result
        assert "85" in result

    @pytest.mark.asyncio
    async def test_export_grades_summary_format(self, mock_canvas_api):
        """Test that summary shows student count and assignment count."""
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}, {"id": 1002, "name": "Bob"}],
            [
                {"id": 100, "name": "HW1", "points_possible": 50, "published": True},
                {"id": 101, "name": "HW2", "points_possible": 50, "published": True}
            ],
            # Submissions for assignment 100
            [{"user_id": 1001, "score": 45}],
            # Submissions for assignment 101
            [{"user_id": 1001, "score": 48}]
        ]

        export_grades = get_tool_function('export_grades')
        result = await export_grades(course_identifier="12345", format="summary")

        assert "Students: 2" in result
        assert "Published Assignments: 2" in result
        assert "Total Points Available: 100" in result

    @pytest.mark.asyncio
    async def test_export_grades_error_handling_students(self, mock_canvas_api):
        """Test error handling when fetching students fails."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Access denied"}

        export_grades = get_tool_function('export_grades')
        result = await export_grades(course_identifier="12345")

        assert "Error fetching students" in result
        assert "Access denied" in result

    @pytest.mark.asyncio
    async def test_export_grades_error_handling_assignments(self, mock_canvas_api):
        """Test error handling when fetching assignments fails."""
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}],  # Students succeed
            {"error": "Not found"}  # Assignments fail
        ]

        export_grades = get_tool_function('export_grades')
        result = await export_grades(course_identifier="12345")

        assert "Error fetching assignments" in result
        assert "Not found" in result


class TestGetAssignmentGroups:
    """Tests for get_assignment_groups tool."""

    @pytest.mark.asyncio
    async def test_assignment_groups_list_shows_weights(self, mock_canvas_api):
        """Test that assignment groups list shows weights and rules."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {
                "id": 1,
                "name": "Homework",
                "group_weight": 30,
                "position": 1,
                "rules": {
                    "drop_lowest": 2,
                    "drop_highest": 0
                }
            },
            {
                "id": 2,
                "name": "Exams",
                "group_weight": 50,
                "position": 2,
                "rules": {}
            }
        ]

        get_groups = get_tool_function('get_assignment_groups')
        result = await get_groups(course_identifier="12345")

        assert "Homework" in result
        assert "Weight: 30%" in result
        assert "Drop Lowest: 2" in result
        assert "Exams" in result
        assert "Weight: 50%" in result

    @pytest.mark.asyncio
    async def test_assignment_groups_error_handling(self, mock_canvas_api):
        """Test error handling when fetching assignment groups fails."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Unauthorized"}

        get_groups = get_tool_function('get_assignment_groups')
        result = await get_groups(course_identifier="12345")

        assert "Error fetching assignment groups" in result
        assert "Unauthorized" in result


class TestCreateAssignmentGroup:
    """Tests for create_assignment_group tool."""

    @pytest.mark.asyncio
    async def test_create_assignment_group_sends_correct_data(self, mock_canvas_api):
        """Test that create_assignment_group sends correct data."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 10,
            "name": "Participation",
            "group_weight": 20
        }

        create_group = get_tool_function('create_assignment_group')
        result = await create_group(
            course_identifier="12345",
            name="Participation",
            weight=20,
            drop_lowest=1
        )

        call_args = mock_canvas_api['make_canvas_request'].call_args
        assert call_args[0][0] == "post"
        group_data = call_args[1]['data']
        assert group_data['name'] == "Participation"
        assert group_data['group_weight'] == 20
        assert group_data['rules']['drop_lowest'] == 1

        assert "Assignment group created" in result
        assert "ID: 10" in result

    @pytest.mark.asyncio
    async def test_create_assignment_group_error_handling(self, mock_canvas_api):
        """Test error handling when creation fails."""
        mock_canvas_api['make_canvas_request'].return_value = {"error": "Invalid name"}

        create_group = get_tool_function('create_assignment_group')
        result = await create_group(course_identifier="12345", name="Test")

        assert "Error creating assignment group" in result
        assert "Invalid name" in result


class TestUpdateAssignmentGroup:
    """Tests for update_assignment_group tool."""

    @pytest.mark.asyncio
    async def test_update_assignment_group(self, mock_canvas_api):
        """Test updating assignment group settings."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 1,
            "name": "Updated Homework",
            "group_weight": 35
        }

        update_group = get_tool_function('update_assignment_group')
        result = await update_group(
            course_identifier="12345",
            group_id="1",
            name="Updated Homework",
            weight=35
        )

        call_args = mock_canvas_api['make_canvas_request'].call_args
        assert call_args[0][0] == "put"
        group_data = call_args[1]['data']
        assert group_data['name'] == "Updated Homework"
        assert group_data['group_weight'] == 35

        assert "updated" in result

    @pytest.mark.asyncio
    async def test_update_assignment_group_no_parameters(self, mock_canvas_api):
        """Test that update with no parameters returns error message."""
        update_group = get_tool_function('update_assignment_group')
        result = await update_group(course_identifier="12345", group_id="1")

        assert "No update parameters provided" in result
        mock_canvas_api['make_canvas_request'].assert_not_called()


class TestConfigureLatePolicy:
    """Tests for configure_late_policy tool."""

    @pytest.mark.asyncio
    async def test_configure_late_policy_creates_new(self, mock_canvas_api):
        """Test that late policy is created when none exists."""
        # First call (get existing) returns error, second call (post) succeeds
        mock_canvas_api['make_canvas_request'].side_effect = [
            {"error": "Not found"},  # GET returns error (no existing policy)
            {"late_policy": {"late_submission_deduction": 10}}  # POST succeeds
        ]

        configure_policy = get_tool_function('configure_late_policy')
        result = await configure_policy(
            course_identifier="12345",
            late_submission_deduction=10.0
        )

        # Should have called POST since GET failed
        calls = mock_canvas_api['make_canvas_request'].call_args_list
        assert calls[1][0][0] == "post"
        assert "Late policy configured" in result
        assert "10% per day" in result or "10.0% per day" in result

    @pytest.mark.asyncio
    async def test_configure_late_policy_updates_existing(self, mock_canvas_api):
        """Test that late policy is updated when it exists."""
        mock_canvas_api['make_canvas_request'].side_effect = [
            {"late_policy": {"late_submission_deduction": 5}},  # GET returns existing policy
            {"late_policy": {"late_submission_deduction": 10}}  # PUT succeeds
        ]

        configure_policy = get_tool_function('configure_late_policy')
        result = await configure_policy(
            course_identifier="12345",
            late_submission_deduction=10.0
        )

        # Should have called PUT since GET succeeded
        calls = mock_canvas_api['make_canvas_request'].call_args_list
        assert calls[1][0][0] == "put"
        assert "Late policy configured" in result

    @pytest.mark.asyncio
    async def test_configure_late_policy_error_handling(self, mock_canvas_api):
        """Test error handling when configuration fails."""
        mock_canvas_api['make_canvas_request'].side_effect = [
            {"error": "Not found"},  # GET fails
            {"error": "Invalid parameters"}  # POST also fails
        ]

        configure_policy = get_tool_function('configure_late_policy')
        result = await configure_policy(course_identifier="12345")

        assert "Error configuring late policy" in result
        assert "Invalid parameters" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
