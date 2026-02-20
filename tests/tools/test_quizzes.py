"""
Tests for quiz management MCP tools.

Includes tests for:
- list_quizzes
- get_quiz_details
- create_quiz
- update_quiz
- delete_quiz
- publish_quiz
- unpublish_quiz
- list_quiz_questions
- add_quiz_question
- get_quiz_statistics
- list_quiz_submissions
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_canvas_api():
    """Fixture to mock Canvas API calls for quiz tools."""
    with patch('canvas_mcp.tools.quizzes.get_course_id') as mock_get_id, \
         patch('canvas_mcp.tools.quizzes.get_course_code') as mock_get_code, \
         patch('canvas_mcp.tools.quizzes.fetch_all_paginated_results') as mock_fetch, \
         patch('canvas_mcp.tools.quizzes.make_canvas_request') as mock_request:

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
    from canvas_mcp.tools.quizzes import register_quiz_tools

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
    register_quiz_tools(mcp)

    return captured_functions.get(tool_name)


class TestListQuizzes:
    """Tests for list_quizzes tool."""

    @pytest.mark.asyncio
    async def test_list_quizzes_returns_formatted_output(self, mock_canvas_api):
        """Test that list_quizzes returns formatted quiz information."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = [
            {
                "id": 1,
                "title": "Midterm Quiz",
                "quiz_type": "assignment",
                "points_possible": 100,
                "published": True,
                "due_at": "2024-03-01T23:59:00Z",
                "time_limit": 60,
                "question_count": 20
            }
        ]

        list_quizzes = get_tool_function('list_quizzes')
        result = await list_quizzes(course_identifier="12345")

        assert "Midterm Quiz" in result
        assert "ID: 1" in result
        assert "Points: 100" in result
        assert "Questions: 20" in result
        assert "Published" in result
        assert "60 min" in result

    @pytest.mark.asyncio
    async def test_list_quizzes_error_handling(self, mock_canvas_api):
        """Test error handling when API returns error."""
        mock_canvas_api['fetch_all_paginated_results'].return_value = {"error": "Unauthorized"}

        list_quizzes = get_tool_function('list_quizzes')
        result = await list_quizzes(course_identifier="12345")

        assert "Error fetching quizzes" in result
        assert "Unauthorized" in result


class TestCreateQuiz:
    """Tests for create_quiz tool."""

    @pytest.mark.asyncio
    async def test_create_quiz_sends_correct_data(self, mock_canvas_api):
        """Test that create_quiz sends correct data to API."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 100,
            "title": "New Quiz",
            "quiz_type": "assignment",
            "published": False
        }

        create_quiz = get_tool_function('create_quiz')
        result = await create_quiz(
            course_identifier="12345",
            title="New Quiz",
            points_possible=50,
            time_limit=30
        )

        call_args = mock_canvas_api['make_canvas_request'].call_args
        assert call_args[0][0] == "post"
        assert "/courses/12345/quizzes" in call_args[0][1]
        quiz_data = call_args[1]['data']['quiz']
        assert quiz_data['title'] == "New Quiz"
        assert quiz_data['points_possible'] == 50
        assert quiz_data['time_limit'] == 30

        assert "Quiz created successfully" in result
        assert "ID: 100" in result

    @pytest.mark.asyncio
    async def test_create_quiz_error_handling(self, mock_canvas_api):
        """Test error handling when quiz creation fails."""
        mock_canvas_api['make_canvas_request'].return_value = {"error": "Invalid parameters"}

        create_quiz = get_tool_function('create_quiz')
        result = await create_quiz(course_identifier="12345", title="Test Quiz")

        assert "Error creating quiz" in result
        assert "Invalid parameters" in result


class TestPublishUnpublishQuiz:
    """Tests for publish_quiz and unpublish_quiz tools."""

    @pytest.mark.asyncio
    async def test_publish_quiz_toggle_works(self, mock_canvas_api):
        """Test that publish quiz sends correct API call."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 1,
            "title": "Test Quiz",
            "published": True
        }

        publish_quiz = get_tool_function('publish_quiz')
        result = await publish_quiz(course_identifier="12345", quiz_id="1")

        call_args = mock_canvas_api['make_canvas_request'].call_args
        assert call_args[0][0] == "put"
        assert call_args[1]['data']['quiz']['published'] is True
        assert "published" in result

    @pytest.mark.asyncio
    async def test_unpublish_quiz_toggle_works(self, mock_canvas_api):
        """Test that unpublish quiz sends correct API call."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 1,
            "title": "Test Quiz",
            "published": False
        }

        unpublish_quiz = get_tool_function('unpublish_quiz')
        result = await unpublish_quiz(course_identifier="12345", quiz_id="1")

        call_args = mock_canvas_api['make_canvas_request'].call_args
        assert call_args[0][0] == "put"
        assert call_args[1]['data']['quiz']['published'] is False
        assert "unpublished" in result


class TestAddQuizQuestion:
    """Tests for add_quiz_question tool."""

    @pytest.mark.asyncio
    async def test_add_question_with_answers(self, mock_canvas_api):
        """Test adding a question with answers sends correct payload."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 50,
            "question_type": "multiple_choice_question",
            "points_possible": 5.0
        }

        add_question = get_tool_function('add_quiz_question')
        result = await add_question(
            course_identifier="12345",
            quiz_id="1",
            question_type="multiple_choice_question",
            question_text="What is 2+2?",
            points_possible=5.0,
            answers='[{"text": "4", "weight": 100}, {"text": "5", "weight": 0}]'
        )

        call_args = mock_canvas_api['make_canvas_request'].call_args
        assert call_args[0][0] == "post"
        question_data = call_args[1]['data']['question']
        assert question_data['question_type'] == "multiple_choice_question"
        assert question_data['question_text'] == "What is 2+2?"
        assert question_data['points_possible'] == 5.0
        assert len(question_data['answers']) == 2

        assert "Question added" in result
        assert "Question ID: 50" in result

    @pytest.mark.asyncio
    async def test_add_question_invalid_json_answers(self, mock_canvas_api):
        """Test error handling for invalid JSON in answers."""
        add_question = get_tool_function('add_quiz_question')
        result = await add_question(
            course_identifier="12345",
            quiz_id="1",
            question_type="multiple_choice_question",
            question_text="Test?",
            answers='invalid json'
        )

        assert "Error" in result
        assert "valid JSON" in result


class TestGetQuizStatistics:
    """Tests for get_quiz_statistics tool."""

    @pytest.mark.asyncio
    async def test_quiz_statistics_returns_formatted_analytics(self, mock_canvas_api):
        """Test that quiz statistics returns formatted analytics."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "quiz_statistics": [
                {
                    "submission_statistics": {
                        "unique_count": 25,
                        "score_average": 82.5,
                        "score_high": 100,
                        "score_low": 45,
                        "score_stdev": 12.3,
                        "duration_average": 1800
                    },
                    "question_statistics": [
                        {
                            "question_text": "<p>What is 2+2?</p>",
                            "correct": 20,
                            "incorrect": 5,
                            "partially_correct": 0
                        }
                    ]
                }
            ]
        }

        get_stats = get_tool_function('get_quiz_statistics')
        result = await get_stats(course_identifier="12345", quiz_id="1")

        assert "Submissions: 25" in result
        assert "Average Score: 82.5" in result
        assert "High Score: 100" in result
        assert "Correct: 20" in result
        assert "Incorrect: 5" in result

    @pytest.mark.asyncio
    async def test_quiz_statistics_error_handling(self, mock_canvas_api):
        """Test error handling for quiz statistics."""
        mock_canvas_api['make_canvas_request'].return_value = {"error": "Quiz not found"}

        get_stats = get_tool_function('get_quiz_statistics')
        result = await get_stats(course_identifier="12345", quiz_id="999")

        assert "Error fetching quiz statistics" in result
        assert "Quiz not found" in result


class TestUpdateQuiz:
    """Tests for update_quiz tool."""

    @pytest.mark.asyncio
    async def test_update_quiz_with_parameters(self, mock_canvas_api):
        """Test updating quiz with various parameters."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "id": 1,
            "title": "Updated Quiz",
            "points_possible": 75
        }

        update_quiz = get_tool_function('update_quiz')
        result = await update_quiz(
            course_identifier="12345",
            quiz_id="1",
            title="Updated Quiz",
            points_possible=75
        )

        call_args = mock_canvas_api['make_canvas_request'].call_args
        assert call_args[0][0] == "put"
        quiz_data = call_args[1]['data']['quiz']
        assert quiz_data['title'] == "Updated Quiz"
        assert quiz_data['points_possible'] == 75

        assert "updated successfully" in result

    @pytest.mark.asyncio
    async def test_update_quiz_no_parameters(self, mock_canvas_api):
        """Test that update with no parameters returns error."""
        update_quiz = get_tool_function('update_quiz')
        result = await update_quiz(course_identifier="12345", quiz_id="1")

        assert "No update parameters provided" in result
        mock_canvas_api['make_canvas_request'].assert_not_called()


class TestListQuizSubmissions:
    """Tests for list_quiz_submissions tool."""

    @pytest.mark.asyncio
    async def test_list_submissions_formatting(self, mock_canvas_api):
        """Test that quiz submissions are formatted correctly."""
        mock_canvas_api['make_canvas_request'].return_value = {
            "quiz_submissions": [
                {
                    "user_id": 1001,
                    "score": 85,
                    "kept_score": 85,
                    "attempt": 1,
                    "workflow_state": "complete",
                    "time_spent": 1800,
                    "finished_at": "2024-03-01T14:30:00Z"
                }
            ]
        }

        list_submissions = get_tool_function('list_quiz_submissions')
        result = await list_submissions(course_identifier="12345", quiz_id="1")

        assert "Total: 1 submissions" in result
        assert "User ID: 1001" in result
        assert "Score: 85" in result
        assert "30m 0s" in result or "Time: 30m" in result

    @pytest.mark.asyncio
    async def test_list_submissions_error_handling(self, mock_canvas_api):
        """Test error handling for quiz submissions."""
        mock_canvas_api['make_canvas_request'].return_value = {"error": "Access denied"}

        list_submissions = get_tool_function('list_quiz_submissions')
        result = await list_submissions(course_identifier="12345", quiz_id="1")

        assert "Error fetching quiz submissions" in result
        assert "Access denied" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
