"""
Tests for search helper MCP tools.

Includes tests for:
- find_assignment
- find_student
- find_discussion
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_canvas_api():
    """Fixture to mock Canvas API calls for search helper tools."""
    with patch('canvas_mcp.tools.search_helpers.get_course_id') as mock_get_id, \
         patch('canvas_mcp.tools.search_helpers.get_course_code') as mock_get_code, \
         patch('canvas_mcp.tools.search_helpers.fetch_all_paginated_results') as mock_fetch:

        mock_get_id.return_value = "12345"
        mock_get_code.return_value = "CS101"

        yield {
            'get_course_id': mock_get_id,
            'get_course_code': mock_get_code,
            'fetch_all_paginated_results': mock_fetch,
        }


def get_tool_function(tool_name: str):
    """Get a tool function by name from the registered tools."""
    from mcp.server.fastmcp import FastMCP
    from canvas_mcp.tools.search_helpers import register_search_helper_tools

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
    register_search_helper_tools(mcp)

    return captured_functions.get(tool_name)


class TestFindAssignment:
    """Tests for find_assignment tool."""

    @pytest.mark.asyncio
    async def test_find_assignment_returns_matches(self, mock_canvas_api):
        """Test finding assignments by name returns matches."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {"id": 1, "name": "Midterm Exam", "due_at": "2024-03-01T23:59:00Z", "points_possible": 100, "published": True},
            {"id": 2, "name": "Final Exam", "due_at": "2024-05-01T23:59:00Z", "points_possible": 200, "published": True}
        ]

        find_assignment = get_tool_function('find_assignment')
        result = await find_assignment(course_identifier="12345", name_query="midterm")

        assert "Midterm Exam" in result
        assert "100 pts" in result
        assert "ID: 1" in result
        assert "Published" in result
        mock_canvas_api['get_course_id'].assert_called_once_with("12345")

    @pytest.mark.asyncio
    async def test_find_assignment_no_matches(self, mock_canvas_api):
        """Test finding assignments with no matches."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {"id": 1, "name": "Homework 1", "due_at": "2024-03-01T23:59:00Z", "points_possible": 50, "published": True}
        ]

        find_assignment = get_tool_function('find_assignment')
        result = await find_assignment(course_identifier="12345", name_query="exam")

        assert "No assignments matching 'exam' found" in result

    @pytest.mark.asyncio
    async def test_find_assignment_case_insensitive(self, mock_canvas_api):
        """Test that search is case-insensitive."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {"id": 1, "name": "FINAL EXAM", "due_at": "2024-05-01T23:59:00Z", "points_possible": 100, "published": True}
        ]

        find_assignment = get_tool_function('find_assignment')
        result = await find_assignment(course_identifier="12345", name_query="final")

        assert "FINAL EXAM" in result
        assert "ID: 1" in result

    @pytest.mark.asyncio
    async def test_find_assignment_error_handling(self, mock_canvas_api):
        """Test error handling when API returns error."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Unauthorized"}

        find_assignment = get_tool_function('find_assignment')
        result = await find_assignment(course_identifier="12345", name_query="test")

        assert "Error searching assignments" in result
        assert "Unauthorized" in result

    @pytest.mark.asyncio
    async def test_find_assignment_fallback_filtering(self, mock_canvas_api):
        """Test client-side fallback when server-side search doesn't match."""
        # First call returns empty, second call returns all assignments
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [],  # First call with search_term returns nothing
            [{"id": 1, "name": "Quiz 1", "due_at": "2024-03-01T23:59:00Z", "points_possible": 20, "published": True}]
        ]

        find_assignment = get_tool_function('find_assignment')
        result = await find_assignment(course_identifier="12345", name_query="quiz")

        assert "Quiz 1" in result
        assert mock_canvas_api['fetch_all_paginated_results'].call_count == 2


class TestFindStudent:
    """Tests for find_student tool."""

    @pytest.mark.asyncio
    async def test_find_student_returns_matches(self, mock_canvas_api):
        """Test finding students by name returns matches."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {"id": 1001, "name": "Alice Smith", "email": "alice@example.com"},
            {"id": 1002, "name": "Bob Smith", "email": "bob@example.com"}
        ]

        find_student = get_tool_function('find_student')
        result = await find_student(course_identifier="12345", name_query="alice")

        assert "Alice Smith" in result
        assert "alice@example.com" in result
        assert "ID: 1001" in result
        assert "Bob Smith" not in result

    @pytest.mark.asyncio
    async def test_find_student_no_matches(self, mock_canvas_api):
        """Test finding students with no matches."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {"id": 1001, "name": "Alice Smith", "email": "alice@example.com"}
        ]

        find_student = get_tool_function('find_student')
        result = await find_student(course_identifier="12345", name_query="charlie")

        assert "No students matching 'charlie' found" in result

    @pytest.mark.asyncio
    async def test_find_student_case_insensitive(self, mock_canvas_api):
        """Test that student search is case-insensitive."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {"id": 1001, "name": "ALICE SMITH", "email": "alice@example.com"}
        ]

        find_student = get_tool_function('find_student')
        result = await find_student(course_identifier="12345", name_query="alice")

        assert "ALICE SMITH" in result

    @pytest.mark.asyncio
    async def test_find_student_error_handling(self, mock_canvas_api):
        """Test error handling when API returns error."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Course not found"}

        find_student = get_tool_function('find_student')
        result = await find_student(course_identifier="99999", name_query="test")

        assert "Error searching students" in result
        assert "Course not found" in result


class TestFindDiscussion:
    """Tests for find_discussion tool."""

    @pytest.mark.asyncio
    async def test_find_discussion_returns_matches(self, mock_canvas_api):
        """Test finding discussions by title returns matches."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {
                "id": 444,
                "title": "Week 1 Discussion",
                "posted_at": "2024-01-15T09:00:00Z",
                "is_announcement": False,
                "discussion_subentry_count": 15
            },
            {
                "id": 445,
                "title": "Week 2 Discussion",
                "posted_at": "2024-01-22T09:00:00Z",
                "is_announcement": False,
                "discussion_subentry_count": 20
            }
        ]

        find_discussion = get_tool_function('find_discussion')
        result = await find_discussion(course_identifier="12345", name_query="week 1")

        assert "Week 1 Discussion" in result
        assert "ID: 444" in result
        assert "15 entries" in result
        assert "Discussion" in result
        assert "Week 2 Discussion" not in result

    @pytest.mark.asyncio
    async def test_find_discussion_no_matches(self, mock_canvas_api):
        """Test finding discussions with no matches."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {"id": 444, "title": "Week 1 Discussion", "posted_at": "2024-01-15T09:00:00Z", "is_announcement": False}
        ]

        find_discussion = get_tool_function('find_discussion')
        result = await find_discussion(course_identifier="12345", name_query="final")

        assert "No discussions matching 'final' found" in result

    @pytest.mark.asyncio
    async def test_find_discussion_announcements(self, mock_canvas_api):
        """Test finding announcements (special type of discussion)."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {
                "id": 555,
                "title": "Important Announcement",
                "posted_at": "2024-01-10T08:00:00Z",
                "is_announcement": True,
                "discussion_subentry_count": 0
            }
        ]

        find_discussion = get_tool_function('find_discussion')
        result = await find_discussion(course_identifier="12345", name_query="announcement")

        assert "Important Announcement" in result
        assert "Announcement" in result
        assert "ID: 555" in result

    @pytest.mark.asyncio
    async def test_find_discussion_error_handling(self, mock_canvas_api):
        """Test error handling when API returns error."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Access denied"}

        find_discussion = get_tool_function('find_discussion')
        result = await find_discussion(course_identifier="12345", name_query="test")

        assert "Error searching discussions" in result
        assert "Access denied" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
