"""Tests for Canvas MCP analytics tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def sample_student_summaries():
    """Sample student summaries data for testing."""
    return [
        {
            "id": 1001,
            "name": "Alice Johnson",
            "page_views": 150,
            "participations": 25,
            "tardiness_breakdown": {
                "late": 1,
                "missing": 0,
                "on_time": 10
            }
        },
        {
            "id": 1002,
            "name": "Bob Smith",
            "page_views": 5,
            "participations": 2,
            "tardiness_breakdown": {
                "late": 4,
                "missing": 3,
                "on_time": 3
            }
        },
        {
            "id": 1003,
            "name": "Carol Davis",
            "page_views": 0,
            "participations": 0,
            "tardiness_breakdown": {
                "late": 0,
                "missing": 5,
                "on_time": 0
            }
        }
    ]


@pytest.fixture
def sample_student_activity():
    """Sample student activity data for testing."""
    return {
        "page_views": {
            "2024-01-15T00:00:00Z": 10,
            "2024-01-16T00:00:00Z": 15,
            "2024-01-17T00:00:00Z": 8
        },
        "participations": [
            {
                "created_at": "2024-01-17T14:30:00Z",
                "url": "/courses/12345/discussion_topics/100"
            },
            {
                "created_at": "2024-01-16T10:00:00Z",
                "url": "/courses/12345/assignments/200/submissions"
            }
        ]
    }


@pytest.fixture
def sample_student_assignments():
    """Sample student assignment analytics data."""
    return [
        {
            "title": "Homework 1",
            "points_possible": 100,
            "submission": {
                "score": 85,
                "submitted_at": "2024-01-15T18:00:00Z",
                "late": False
            }
        },
        {
            "title": "Homework 2",
            "points_possible": 100,
            "submission": {
                "score": 70,
                "submitted_at": "2024-01-20T23:59:00Z",
                "late": True
            }
        },
        {
            "title": "Homework 3",
            "points_possible": 100,
            "submission": None
        }
    ]


@pytest.fixture
def sample_student_communication():
    """Sample student communication data."""
    return {
        "level": {
            "instructorMessages": 5,
            "studentMessages": 8
        }
    }


@pytest.fixture
def sample_course_activity():
    """Sample course activity data."""
    return [
        {
            "date": "2024-01-15",
            "views": 120,
            "participations": 45,
            "submissions": 30
        },
        {
            "date": "2024-01-16",
            "views": 85,
            "participations": 20,
            "submissions": 15
        },
        {
            "date": "2024-01-17",
            "views": 200,
            "participations": 80,
            "submissions": 50
        }
    ]


@pytest.fixture
def sample_assignment_statistics():
    """Sample assignment statistics data."""
    return [
        {
            "title": "Midterm Exam",
            "points_possible": 100,
            "due_at": "2024-02-15T23:59:00Z",
            "min_score": 55.0,
            "max_score": 98.0,
            "median": 82.0,
            "first_quartile": 72.0,
            "third_quartile": 90.0,
            "tardiness_breakdown": {
                "on_time": 28,
                "late": 2,
                "missing": 5,
                "floating": 0
            }
        },
        {
            "title": "Quiz 1",
            "points_possible": 20,
            "due_at": "2024-01-20T23:59:00Z",
            "min_score": 12.0,
            "max_score": 20.0,
            "median": 18.0,
            "first_quartile": 16.0,
            "third_quartile": 19.0,
            "tardiness_breakdown": {
                "on_time": 30,
                "late": 0,
                "missing": 2,
                "floating": 0
            }
        }
    ]


@pytest.fixture
def sample_report_response():
    """Sample report start/status response."""
    return {
        "id": 12345,
        "status": "running",
        "progress": 25,
        "created_at": "2024-01-20T10:00:00Z"
    }


@pytest.fixture
def sample_report_complete():
    """Sample completed report response."""
    return {
        "id": 12345,
        "status": "complete",
        "progress": 100,
        "created_at": "2024-01-20T10:00:00Z",
        "attachment": {
            "url": "https://canvas.example.com/files/grades.csv",
            "filename": "grades.csv",
            "size": 102400
        }
    }


class TestGetCourseStudentSummaries:
    """Tests for get_course_student_summaries tool."""

    @pytest.mark.asyncio
    async def test_returns_student_summaries(self, sample_student_summaries):
        """Test successful retrieval of student summaries."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.fetch_all_paginated_results', new_callable=AsyncMock) as mock_fetch, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_fetch.return_value = sample_student_summaries
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            # Get the tool function
            tool = mcp._tool_manager._tools.get("get_course_student_summaries")
            assert tool is not None

            result = await tool.fn("12345")

            assert "Total Students: 3" in result
            assert "Students with No Activity" in result
            assert "Carol Davis" in result
            assert "Tardiness Issues" in result

    @pytest.mark.asyncio
    async def test_invalid_sort_option(self):
        """Test error handling for invalid sort option."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id:
            mock_get_id.return_value = "12345"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_course_student_summaries")
            result = await tool.fn("12345", sort_by="invalid_option")

            assert "Error: Invalid sort_by option" in result


class TestGetStudentActivity:
    """Tests for get_student_activity tool."""

    @pytest.mark.asyncio
    async def test_returns_student_activity(self, sample_student_activity):
        """Test successful retrieval of student activity."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_student_activity
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_student_activity")
            result = await tool.fn("12345", 1001)

            assert "Total Page Views: 33" in result
            assert "Recent Participations" in result


class TestGetStudentAssignmentData:
    """Tests for get_student_assignment_data tool."""

    @pytest.mark.asyncio
    async def test_returns_assignment_data(self, sample_student_assignments):
        """Test successful retrieval of student assignment data."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_student_assignments
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_student_assignment_data")
            result = await tool.fn("12345", 1001)

            assert "Total Assignments: 3" in result
            assert "Missing: 1" in result
            assert "Late: 1" in result
            assert "Overall Grade:" in result


class TestGetStudentCommunication:
    """Tests for get_student_communication tool."""

    @pytest.mark.asyncio
    async def test_returns_communication_data(self, sample_student_communication):
        """Test successful retrieval of communication data."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_student_communication
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_student_communication")
            result = await tool.fn("12345", 1001)

            assert "Messages from Instructor: 5" in result
            assert "Messages from Student: 8" in result


class TestGetCourseActivity:
    """Tests for get_course_activity tool."""

    @pytest.mark.asyncio
    async def test_returns_course_activity(self, sample_course_activity):
        """Test successful retrieval of course activity."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_course_activity
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_course_activity")
            result = await tool.fn("12345")

            assert "Activity by Category:" in result
            assert "Peak Activity Days" in result


class TestGetAssignmentStatistics:
    """Tests for get_assignment_statistics tool."""

    @pytest.mark.asyncio
    async def test_returns_assignment_statistics(self, sample_assignment_statistics):
        """Test successful retrieval of assignment statistics."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_assignment_statistics
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_assignment_statistics")
            result = await tool.fn("12345")

            assert "Total Assignments: 2" in result
            assert "Midterm Exam" in result
            assert "Score Distribution" in result
            assert "Min:" in result


class TestStartCourseReport:
    """Tests for start_course_report tool."""

    @pytest.mark.asyncio
    async def test_starts_report(self, sample_report_response):
        """Test successful report start."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_report_response
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("start_course_report")
            result = await tool.fn("12345", "grade_export_csv")

            assert "Report Started" in result
            assert "Report ID: 12345" in result
            assert "Status: running" in result

    @pytest.mark.asyncio
    async def test_invalid_report_type(self):
        """Test error handling for invalid report type."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id:
            mock_get_id.return_value = "12345"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("start_course_report")
            result = await tool.fn("12345", "invalid_report")

            assert "Error: Invalid report type" in result


class TestGetReportStatus:
    """Tests for get_report_status tool."""

    @pytest.mark.asyncio
    async def test_returns_complete_status(self, sample_report_complete):
        """Test successful retrieval of complete report status."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_report_complete
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_report_status")
            result = await tool.fn("12345", "grade_export_csv", 12345)

            assert "Report Complete" in result
            assert "Download URL:" in result
            assert "grades.csv" in result

    @pytest.mark.asyncio
    async def test_returns_running_status(self, sample_report_response):
        """Test status check for running report."""
        with patch('canvas_mcp.tools.analytics.get_course_id', new_callable=AsyncMock) as mock_get_id, \
             patch('canvas_mcp.tools.analytics.make_canvas_request', new_callable=AsyncMock) as mock_request, \
             patch('canvas_mcp.tools.analytics.get_course_code', new_callable=AsyncMock) as mock_get_code:

            mock_get_id.return_value = "12345"
            mock_request.return_value = sample_report_response
            mock_get_code.return_value = "CS101"

            from canvas_mcp.tools.analytics import register_analytics_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_analytics_tools(mcp)

            tool = mcp._tool_manager._tools.get("get_report_status")
            result = await tool.fn("12345", "grade_export_csv", 12345)

            assert "Status: running" in result
            assert "still generating" in result
