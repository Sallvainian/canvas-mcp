"""Search-by-name helper tools for Canvas MCP."""

from mcp.server.fastmcp import FastMCP

from ..core.cache import get_course_code, get_course_id
from ..core.client import fetch_all_paginated_results
from ..core.dates import format_date
from ..core.validation import validate_params


def register_search_helper_tools(mcp: FastMCP) -> None:
    """Register search-by-name helper tools."""

    @mcp.tool()
    @validate_params
    async def find_assignment(
        course_identifier: str | int,
        name_query: str
    ) -> str:
        """Find assignments by name (case-insensitive search).

        Searches assignment titles for the given query string.
        Useful when you know the assignment name but not its Canvas ID.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            name_query: Search term to match against assignment titles
        """
        course_id = await get_course_id(course_identifier)
        query_lower = name_query.lower()

        assignments = await fetch_all_paginated_results(
            f"/courses/{course_id}/assignments",
            {"per_page": 100, "search_term": name_query}
        )

        if isinstance(assignments, dict) and "error" in assignments:
            return f"Error searching assignments: {assignments['error']}"

        # Canvas search_term may not be exact, so also do client-side filtering
        matches = []
        if isinstance(assignments, list):
            for a in assignments:
                title = a.get("name", "")
                if query_lower in title.lower():
                    matches.append(a)

        if not matches:
            # Fallback: fetch all and search client-side
            all_assignments = await fetch_all_paginated_results(
                f"/courses/{course_id}/assignments",
                {"per_page": 100}
            )
            if isinstance(all_assignments, list):
                matches = [a for a in all_assignments if query_lower in a.get("name", "").lower()]

        if not matches:
            return f"No assignments matching '{name_query}' found."

        course_display = await get_course_code(course_id) or course_identifier
        result = f"Assignments matching '{name_query}' in {course_display}:\n\n"

        for a in matches:
            due = format_date(a.get("due_at"))
            points = a.get("points_possible", "N/A")
            published = "Published" if a.get("published") else "Unpublished"
            result += f"  ID: {a['id']} | {a.get('name', 'Untitled')} | {points} pts | Due: {due} | {published}\n"

        return result

    @mcp.tool()
    @validate_params
    async def find_student(
        course_identifier: str | int,
        name_query: str
    ) -> str:
        """Find students by name (case-insensitive search).

        Searches enrolled student names for the given query string.
        Useful when you know a student's name but not their Canvas ID.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            name_query: Search term to match against student names
        """
        course_id = await get_course_id(course_identifier)
        query_lower = name_query.lower()

        users = await fetch_all_paginated_results(
            f"/courses/{course_id}/users",
            {
                "enrollment_type[]": "student",
                "search_term": name_query,
                "per_page": 100
            }
        )

        if isinstance(users, dict) and "error" in users:
            return f"Error searching students: {users['error']}"

        # Client-side filter for accuracy
        matches = []
        if isinstance(users, list):
            matches = [u for u in users if query_lower in u.get("name", "").lower()]

        if not matches:
            # Fallback: fetch all students and filter
            all_users = await fetch_all_paginated_results(
                f"/courses/{course_id}/users",
                {"enrollment_type[]": "student", "per_page": 100}
            )
            if isinstance(all_users, list):
                matches = [u for u in all_users if query_lower in u.get("name", "").lower()]

        if not matches:
            return f"No students matching '{name_query}' found."

        course_display = await get_course_code(course_id) or course_identifier
        result = f"Students matching '{name_query}' in {course_display}:\n\n"

        for u in matches:
            email = u.get("email", "N/A")
            result += f"  ID: {u['id']} | {u.get('name', 'Unknown')} | Email: {email}\n"

        return result

    @mcp.tool()
    @validate_params
    async def find_discussion(
        course_identifier: str | int,
        name_query: str
    ) -> str:
        """Find discussion topics by title (case-insensitive search).

        Searches discussion topic titles for the given query string.
        Useful when you know the discussion name but not its Canvas ID.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            name_query: Search term to match against discussion titles
        """
        course_id = await get_course_id(course_identifier)
        query_lower = name_query.lower()

        topics = await fetch_all_paginated_results(
            f"/courses/{course_id}/discussion_topics",
            {"per_page": 100}
        )

        if isinstance(topics, dict) and "error" in topics:
            return f"Error searching discussions: {topics['error']}"

        matches = []
        if isinstance(topics, list):
            matches = [t for t in topics if query_lower in t.get("title", "").lower()]

        if not matches:
            return f"No discussions matching '{name_query}' found."

        course_display = await get_course_code(course_id) or course_identifier
        result = f"Discussions matching '{name_query}' in {course_display}:\n\n"

        for t in matches:
            posted = format_date(t.get("posted_at"))
            is_announcement = t.get("is_announcement", False)
            topic_type = "Announcement" if is_announcement else "Discussion"
            entry_count = t.get("discussion_subentry_count", 0)
            result += f"  ID: {t['id']} | {t.get('title', 'Untitled')} | {topic_type} | {entry_count} entries | Posted: {posted}\n"

        return result
