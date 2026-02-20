"""Tool modules for Canvas MCP server."""

from .courses import register_course_tools
from .assignments import register_assignment_tools
from .discussions import register_discussion_tools
from .discussion_analytics import register_discussion_analytics_tools
from .enrollment import register_enrollment_tools
from .modules import register_module_tools
from .other_tools import register_other_tools
from .rubrics import register_rubric_tools
from .peer_reviews import register_peer_review_tools
from .peer_review_comments import register_peer_review_comment_tools
from .messaging import register_messaging_tools
from .student_tools import register_student_tools
from .accessibility import register_accessibility_tools
from .discovery import register_discovery_tools
from .code_execution import register_code_execution_tools
from .pages import register_page_tools
from .analytics import register_analytics_tools
from .search_helpers import register_search_helper_tools
from .quizzes import register_quiz_tools
from .gradebook import register_gradebook_tools

__all__ = [
    'register_course_tools',
    'register_assignment_tools',
    'register_discussion_tools',
    'register_discussion_analytics_tools',
    'register_enrollment_tools',
    'register_module_tools',
    'register_other_tools',
    'register_rubric_tools',
    'register_peer_review_tools',
    'register_peer_review_comment_tools',
    'register_messaging_tools',
    'register_student_tools',
    'register_accessibility_tools',
    'register_discovery_tools',
    'register_code_execution_tools',
    'register_page_tools',
    'register_analytics_tools',
    'register_search_helper_tools',
    'register_quiz_tools',
    'register_gradebook_tools'
]