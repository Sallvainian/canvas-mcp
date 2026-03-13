"""
Tests for rubric-related MCP tools.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch

from canvas_mcp.tools.rubrics import (
    validate_rubric_criteria,
    preprocess_criteria_string,
)


class TestRubricValidation:
    """Test rubric validation functions."""

    def test_validate_valid_criteria(self):
        """Test validating valid rubric criteria."""
        criteria_json = json.dumps(
            {"criterion_1": {"description": "Quality", "points": 10, "ratings": []}}
        )

        result = validate_rubric_criteria(criteria_json)

        assert "criterion_1" in result
        assert result["criterion_1"]["points"] == 10

    def test_validate_missing_description(self):
        """Test validation fails for missing description."""
        criteria_json = json.dumps({"criterion_1": {"points": 10}})

        with pytest.raises(ValueError, match="description"):
            validate_rubric_criteria(criteria_json)

    def test_validate_missing_points(self):
        """Test validation fails for missing points."""
        criteria_json = json.dumps({"criterion_1": {"description": "Quality"}})

        with pytest.raises(ValueError, match="points"):
            validate_rubric_criteria(criteria_json)

    def test_validate_negative_points(self):
        """Test validation fails for negative points."""
        criteria_json = json.dumps(
            {"criterion_1": {"description": "Quality", "points": -5}}
        )

        with pytest.raises(ValueError, match="valid number|non-negative"):
            validate_rubric_criteria(criteria_json)

    def test_preprocess_criteria_string(self):
        """Test preprocessing criteria string."""
        criteria = '{"criterion_1": {"description": "Test", "points": 10}}'
        result = preprocess_criteria_string(criteria)

        assert result == criteria

    def test_preprocess_with_outer_quotes(self):
        """Test preprocessing with outer quotes."""
        criteria = '"{"criterion_1": {"description": "Test", "points": 10}}"'
        result = preprocess_criteria_string(criteria)

        # Should remove outer quotes and unescape
        assert result.startswith("{")
        assert result.endswith("}")


class TestRubricTools:
    """Test rubric tool functions."""

    @pytest.mark.asyncio
    async def test_list_rubrics(self):
        """Test listing rubrics."""
        mock_rubrics = [
            {"id": 1, "title": "Rubric 1", "points_possible": 100},
            {"id": 2, "title": "Rubric 2", "points_possible": 50},
        ]

        with patch(
            "canvas_mcp.core.client.fetch_all_paginated_results", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_rubrics

            from canvas_mcp.core.client import fetch_all_paginated_results

            result = await fetch_all_paginated_results("/courses/12345/rubrics", {})

            assert len(result) == 2
            assert result[0]["title"] == "Rubric 1"

    @pytest.mark.asyncio
    async def test_get_rubric_details(self):
        """Test getting rubric details."""
        mock_rubric = {
            "id": 123,
            "title": "Test Rubric",
            "criteria": [{"id": "crit1", "description": "Quality", "points": 40}],
        }

        with patch(
            "canvas_mcp.core.client.make_canvas_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_rubric

            from canvas_mcp.core.client import make_canvas_request

            result = await make_canvas_request("get", "/courses/12345/rubrics/123")

            assert result["title"] == "Test Rubric"
            assert len(result["criteria"]) == 1


class TestBulkGradeFormData:
    """Test build_bulk_grade_form_data helper."""

    def test_simple_grades(self):
        from canvas_mcp.tools.rubric_grading import build_bulk_grade_form_data

        grades = {
            "123": {"grade": 95, "comment": "Great work"},
            "456": {"grade": "85%"},
        }
        result = build_bulk_grade_form_data(grades)
        assert ("grade_data[123][posted_grade]", "95") in result
        assert ("grade_data[123][text_comment]", "Great work") in result
        assert ("grade_data[456][posted_grade]", "85%") in result

    def test_excused(self):
        from canvas_mcp.tools.rubric_grading import build_bulk_grade_form_data

        grades = {"123": {"excused": True, "comment": "Absent"}}
        result = build_bulk_grade_form_data(grades)
        assert ("grade_data[123][excuse]", "true") in result
        assert ("grade_data[123][text_comment]", "Absent") in result

    def test_empty_grades(self):
        from canvas_mcp.tools.rubric_grading import build_bulk_grade_form_data

        result = build_bulk_grade_form_data({})
        assert result == []

    def test_excused_takes_precedence_over_grade(self):
        from canvas_mcp.tools.rubric_grading import build_bulk_grade_form_data

        grades = {"123": {"excused": True, "grade": 100}}
        result = build_bulk_grade_form_data(grades)
        keys = [k for k, v in result]
        assert "grade_data[123][excuse]" in keys
        assert "grade_data[123][posted_grade]" not in keys


class TestPollCanvasProgress:
    """Test progress polling utility."""

    @pytest.mark.asyncio
    async def test_immediate_completion(self):
        with patch(
            "canvas_mcp.core.client.make_canvas_request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = {
                "id": 42,
                "workflow_state": "completed",
                "completion": 100,
                "message": "done",
            }
            from canvas_mcp.core.client import poll_canvas_progress

            result = await poll_canvas_progress(42)
            assert result["completed"] is True
            assert result["workflow_state"] == "completed"
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_failed_progress(self):
        with patch(
            "canvas_mcp.core.client.make_canvas_request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = {
                "id": 42,
                "workflow_state": "failed",
                "completion": 50,
                "message": "Something went wrong",
            }
            from canvas_mcp.core.client import poll_canvas_progress

            result = await poll_canvas_progress(42)
            assert result["completed"] is True
            assert result["workflow_state"] == "failed"
            assert "Something went wrong" in result["error"]

    @pytest.mark.asyncio
    async def test_polling_then_complete(self):
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"id": 42, "workflow_state": "running", "completion": 50}
            return {
                "id": 42,
                "workflow_state": "completed",
                "completion": 100,
                "message": "done",
            }

        with patch(
            "canvas_mcp.core.client.make_canvas_request", side_effect=mock_request
        ):
            from canvas_mcp.core.client import poll_canvas_progress

            result = await poll_canvas_progress(
                42, initial_interval=0.01, max_interval=0.02
            )
            assert result["completed"] is True
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_timeout(self):
        async def mock_request(*args, **kwargs):
            return {"id": 42, "workflow_state": "running", "completion": 25}

        with patch(
            "canvas_mcp.core.client.make_canvas_request", side_effect=mock_request
        ):
            from canvas_mcp.core.client import poll_canvas_progress

            result = await poll_canvas_progress(
                42, max_wait_seconds=0.05, initial_interval=0.01, max_interval=0.02
            )
            assert result["completed"] is False
            assert result["workflow_state"] == "timeout"

    @pytest.mark.asyncio
    async def test_url_parsing(self):
        with patch(
            "canvas_mcp.core.client.make_canvas_request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = {
                "id": 99,
                "workflow_state": "completed",
                "completion": 100,
                "message": "done",
            }
            from canvas_mcp.core.client import poll_canvas_progress

            await poll_canvas_progress("/api/v1/progress/99")
            mock_req.assert_called_once_with(
                "get", "/progress/99", skip_anonymization=True
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
