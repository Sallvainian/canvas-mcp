"""Core utilities for Canvas MCP server."""

from .cache import get_course_code, get_course_id, refresh_course_cache
from .client import (
    cleanup_http_client,
    fetch_all_paginated_results,
    make_canvas_request,
    poll_canvas_progress,
)
from .config import API_BASE_URL, API_TOKEN, get_config, validate_config
from .dates import (
    format_date,
    format_date_smart,
    format_datetime_compact,
    parse_date,
    truncate_text,
)
from .response_formatter import (
    Verbosity,
    format_assignment_item,
    format_boolean,
    format_count,
    format_footer,
    format_header,
    format_item,
    format_list,
    format_response,
    format_stats,
    format_submission_item,
    format_user_item,
    get_verbosity,
    is_compact,
    set_verbosity,
)
from .types import AnnouncementInfo, AssignmentInfo, CourseInfo, PageInfo
from .validation import (
    format_error,
    is_error_response,
    validate_parameter,
    validate_params,
)

__all__ = [
    "make_canvas_request",
    "fetch_all_paginated_results",
    "cleanup_http_client",
    "poll_canvas_progress",
    "get_course_id",
    "get_course_code",
    "refresh_course_cache",
    "validate_params",
    "validate_parameter",
    "format_error",
    "is_error_response",
    "format_date",
    "parse_date",
    "truncate_text",
    "format_date_smart",
    "format_datetime_compact",
    "CourseInfo",
    "AssignmentInfo",
    "PageInfo",
    "AnnouncementInfo",
    "get_config",
    "validate_config",
    "API_BASE_URL",
    "API_TOKEN",
    # Response formatter exports
    "Verbosity",
    "get_verbosity",
    "set_verbosity",
    "is_compact",
    "format_header",
    "format_item",
    "format_list",
    "format_footer",
    "format_response",
    "format_boolean",
    "format_count",
    "format_stats",
    "format_assignment_item",
    "format_submission_item",
    "format_user_item",
]
