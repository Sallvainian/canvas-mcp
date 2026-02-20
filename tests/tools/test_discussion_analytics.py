"""
Tests for discussion analytics MCP tools.

Includes tests for:
- get_discussion_participation_summary
- grade_discussion_participation
- export_discussion_data
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_canvas_api():
    """Fixture to mock Canvas API calls for discussion analytics tools."""
    with patch('canvas_mcp.tools.discussion_analytics.get_course_id') as mock_get_id, \
         patch('canvas_mcp.tools.discussion_analytics.get_course_code') as mock_get_code, \
         patch('canvas_mcp.tools.discussion_analytics.fetch_all_paginated_results') as mock_fetch, \
         patch('canvas_mcp.tools.discussion_analytics.make_canvas_request') as mock_request:

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
    from canvas_mcp.tools.discussion_analytics import register_discussion_analytics_tools

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
    register_discussion_analytics_tools(mcp)

    return captured_functions.get(tool_name)


class TestGetDiscussionParticipationSummary:
    """Tests for get_discussion_participation_summary tool."""

    @pytest.mark.asyncio
    async def test_participation_summary_categorizes_students(self, mock_canvas_api):
        """Test that participation summary correctly categorizes students."""
        # Mock students
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            # Students
            [
                {"id": 1001, "name": "Alice"},
                {"id": 1002, "name": "Bob"},
                {"id": 1003, "name": "Charlie"},
                {"id": 1004, "name": "Diana"}
            ],
            # Discussion entries
            [
                {"user_id": 1001, "recent_replies": [{"user_id": 1001}]},  # Alice posts and replies
                {"user_id": 1002, "recent_replies": []},  # Bob posts only
                {"user_id": 1003, "recent_replies": [{"user_id": 1004}]}  # Charlie posts, Diana replies
            ]
        ]
        # Mock topic details
        mock_canvas_api['make_canvas_request'].return_value = {"title": "Week 1 Discussion"}

        get_summary = get_tool_function('get_discussion_participation_summary')
        result = await get_summary(course_identifier="12345", topic_id="444")

        assert "Week 1 Discussion" in result
        assert "Alice" in result  # Full participant
        assert "Bob" in result  # Posted only
        assert "Diana" in result  # Replied only
        assert "Silent" in result

    @pytest.mark.asyncio
    async def test_participation_summary_counts(self, mock_canvas_api):
        """Test that summary shows correct participation counts."""
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}, {"id": 1002, "name": "Bob"}],
            [{"user_id": 1001, "recent_replies": [{"user_id": 1001}]}]
        ]
        mock_canvas_api['make_canvas_request'].return_value = {"title": "Test Discussion"}

        get_summary = get_tool_function('get_discussion_participation_summary')
        result = await get_summary(course_identifier="12345", topic_id="444")

        assert "1/2 students participated" in result or "50%" in result

    @pytest.mark.asyncio
    async def test_participation_summary_silent_students_ids(self, mock_canvas_api):
        """Test that silent student IDs are provided for messaging."""
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}, {"id": 1002, "name": "Bob"}],
            []  # No entries
        ]
        mock_canvas_api['make_canvas_request'].return_value = {"title": "Test Discussion"}

        get_summary = get_tool_function('get_discussion_participation_summary')
        result = await get_summary(course_identifier="12345", topic_id="444")

        assert "Silent" in result
        assert "1001,1002" in result or ("1001" in result and "1002" in result)

    @pytest.mark.asyncio
    async def test_participation_summary_error_students(self, mock_canvas_api):
        """Test error handling when fetching students fails."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Unauthorized"}

        get_summary = get_tool_function('get_discussion_participation_summary')
        result = await get_summary(course_identifier="12345", topic_id="444")

        assert "Error fetching students" in result
        assert "Unauthorized" in result

    @pytest.mark.asyncio
    async def test_participation_summary_error_entries(self, mock_canvas_api):
        """Test error handling when fetching discussion entries fails."""
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}],  # Students succeed
            {"error": "Not found"}  # Entries fail
        ]

        get_summary = get_tool_function('get_discussion_participation_summary')
        result = await get_summary(course_identifier="12345", topic_id="444")

        assert "Error fetching discussion entries" in result
        assert "Not found" in result


class TestGradeDiscussionParticipation:
    """Tests for grade_discussion_participation tool."""

    @pytest.mark.asyncio
    async def test_grade_calculation(self, mock_canvas_api):
        """Test that grades are calculated correctly."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 100,
            "name": "Discussion Grade",
            "points_possible": 10
        }
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}],
            [{"user_id": 1001, "recent_replies": [{"user_id": 1001}, {"user_id": 1001}]}]  # 1 post, 2 replies
        ]

        grade_discussion = get_tool_function('grade_discussion_participation')
        result = await grade_discussion(
            course_identifier="12345",
            topic_id="444",
            assignment_id="100",
            points_for_post=5.0,
            points_for_reply=3.0,
            dry_run=True
        )

        # 1 post * 5 + 2 replies * 3 = 11, but capped at 10
        assert "10.0" in result or "10" in result
        assert "Alice" in result

    @pytest.mark.asyncio
    async def test_grade_dry_run_mode(self, mock_canvas_api):
        """Test that dry run mode doesn't submit grades."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 100,
            "name": "Discussion Grade",
            "points_possible": 10
        }
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}],
            []
        ]

        grade_discussion = get_tool_function('grade_discussion_participation')
        result = await grade_discussion(
            course_identifier="12345",
            topic_id="444",
            assignment_id="100",
            dry_run=True
        )

        assert "DRY RUN" in result
        assert "Set dry_run=False to submit" in result
        # Should only call API for assignment details and fetching data, not for submitting grades
        assert all(call[0][0] != "put" or "submissions" not in call[0][1]
                  for call in mock_canvas_api['make_canvas_request'].call_args_list)

    @pytest.mark.asyncio
    async def test_grade_submission_success(self, mock_canvas_api):
        """Test successful grade submission."""
        mock_canvas_api['make_canvas_request'].side_effect = [
            {"id": 100, "name": "Discussion Grade", "points_possible": 10},  # Assignment details
            {"id": 1, "score": 5.0}  # Grade submission response
        ]
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}],
            [{"user_id": 1001, "recent_replies": []}]
        ]

        grade_discussion = get_tool_function('grade_discussion_participation')
        result = await grade_discussion(
            course_identifier="12345",
            topic_id="444",
            assignment_id="100",
            dry_run=False
        )

        assert "1 submitted" in result
        assert "0 failed" in result

    @pytest.mark.asyncio
    async def test_grade_max_points_override(self, mock_canvas_api):
        """Test that max_points parameter overrides assignment points_possible."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 100,
            "name": "Discussion Grade",
            "points_possible": 10
        }
        mock_canvas_api['fetch_all_paginated_results'].side_effect = [
            [{"id": 1001, "name": "Alice"}],
            [{"user_id": 1001, "recent_replies": [{"user_id": 1001}] * 10}]  # 1 post, 10 replies
        ]

        grade_discussion = get_tool_function('grade_discussion_participation')
        result = await grade_discussion(
            course_identifier="12345",
            topic_id="444",
            assignment_id="100",
            points_for_post=5.0,
            points_for_reply=3.0,
            max_points=15.0,
            dry_run=True
        )

        # 1 post * 5 + 10 replies * 3 = 35, capped at max_points=15
        assert "max 15" in result


class TestExportDiscussionData:
    """Tests for export_discussion_data tool."""

    @pytest.mark.asyncio
    async def test_export_csv_format(self, mock_canvas_api):
        """Test CSV export includes correct columns."""
        mock_canvas_api['make_canvas_request'].return_value = {"title": "Test Discussion"}
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {
                "id": 1,
                "user_id": 1001,
                "user_name": "Alice",
                "message": "<p>This is a post</p>",
                "created_at": "2024-01-15T09:00:00Z",
                "recent_replies": [
                    {
                        "id": 2,
                        "user_id": 1002,
                        "user_name": "Bob",
                        "message": "This is a reply",
                        "created_at": "2024-01-15T10:00:00Z"
                    }
                ]
            }
        ]

        export_data = get_tool_function('export_discussion_data')
        result = await export_data(course_identifier="12345", topic_id="444", format="csv")

        assert "entry_id" in result
        assert "user_id" in result
        assert "user_name" in result
        assert "type" in result
        assert "message_preview" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "post" in result
        assert "reply" in result

    @pytest.mark.asyncio
    async def test_export_summary_format(self, mock_canvas_api):
        """Test summary format returns correct counts."""
        mock_canvas_api['make_canvas_request'].return_value = {"title": "Test Discussion"}
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {
                "id": 1,
                "user_id": 1001,
                "recent_replies": [
                    {"user_id": 1002},
                    {"user_id": 1003}
                ]
            },
            {
                "id": 2,
                "user_id": 1002,
                "recent_replies": []
            }
        ]

        export_data = get_tool_function('export_discussion_data')
        result = await export_data(course_identifier="12345", topic_id="444", format="summary")

        assert "Total posts: 2" in result
        assert "Total replies: 2" in result
        assert "Total interactions: 4" in result
        assert "Unique participants: 3" in result

    @pytest.mark.asyncio
    async def test_export_error_handling(self, mock_canvas_api):
        """Test error handling when fetching entries fails."""
        mock_canvas_api['make_canvas_request'].return_value = {"title": "Test Discussion"}
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Not found"}

        export_data = get_tool_function('export_discussion_data')
        result = await export_data(course_identifier="12345", topic_id="444")

        assert "Error fetching entries" in result
        assert "Not found" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
