# Canvas MCP - API Contracts

**Generated:** 2026-03-12 | **Scan Level:** Exhaustive

---

## Overview

Canvas MCP interacts with the Canvas LMS REST API v1. All requests go through the centralized `make_canvas_request()` function in `core/client.py`, which handles authentication, rate limiting, pagination, and anonymization.

**Base URL:** Configured via `CANVAS_API_URL` environment variable
**Authentication:** Bearer token via `CANVAS_API_TOKEN`
**Rate Limits:** ~700 requests/10 minutes (Canvas-enforced)

## Request Patterns

| Pattern | Method | Content-Type | Used By |
|---------|--------|-------------|---------|
| Standard JSON | GET/POST/PUT/DELETE | application/json | Most tools |
| Form Data | POST/PUT | application/x-www-form-urlencoded | Submissions, modules, messaging |
| File Upload | POST (3-step) | multipart/form-data | File submissions |
| Paginated | GET | - | List endpoints (auto-handled) |

## Canvas API Endpoints by Tool Module

### Course Tools (`tools/courses.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_courses` | GET | `/api/v1/courses` | List enrolled courses |
| `get_course_details` | GET | `/api/v1/courses/{id}` | Course info with syllabus |
| `get_course_content_overview` | GET | `/api/v1/courses/{id}` + sub-endpoints | Aggregated content summary |

### Assignment Tools (`tools/assignments.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_assignments` | GET | `/api/v1/courses/{id}/assignments` | All assignments in course |
| `get_assignment_details` | GET | `/api/v1/courses/{id}/assignments/{aid}` | Single assignment details |
| `create_assignment` | POST | `/api/v1/courses/{id}/assignments` | Create new assignment |
| `update_assignment` | PUT | `/api/v1/courses/{id}/assignments/{aid}` | Update assignment properties |
| `delete_assignment` | DELETE | `/api/v1/courses/{id}/assignments/{aid}` | Delete assignment |
| `list_submissions` | GET | `/api/v1/courses/{id}/assignments/{aid}/submissions` | All submissions |
| `list_ungraded_submissions` | GET | `/api/v1/courses/{id}/assignments/{aid}/submissions` | Filtered ungraded |
| `get_submission_content` | GET | `/api/v1/courses/{id}/assignments/{aid}/submissions/{uid}` | Submission with content |
| `get_submission_history` | GET | `/api/v1/courses/{id}/assignments/{aid}/submissions/{uid}` | Submission versions |
| `get_submission_comments` | GET | `/api/v1/courses/{id}/assignments/{aid}/submissions/{uid}` | Comments on submission |
| `post_submission_comment` | PUT | `/api/v1/courses/{id}/assignments/{aid}/submissions/{uid}` | Add comment |
| `download_submission_attachment` | GET | attachment URL | Download file attachment |
| `bulk_grade_submissions` | POST | `/api/v1/courses/{id}/assignments/{aid}/submissions/update_grades` | Bulk grade via progress |
| `submit_file_for_student` | POST | 3-step upload | Submit file on behalf of student |

### Rubric Tools (`tools/rubrics.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_all_rubrics` | GET | `/api/v1/courses/{id}/rubrics` | All course rubrics |
| `list_assignment_rubrics` | GET | `/api/v1/courses/{id}/assignments/{aid}` | Rubrics for assignment |
| `get_rubric_details` | GET | `/api/v1/courses/{id}/rubrics/{rid}` | Rubric criteria details |
| `get_assignment_rubric_details` | GET | `/api/v1/courses/{id}/assignments/{aid}` | Assignment's rubric |
| `create_rubric` | POST | `/api/v1/courses/{id}/rubrics` | Create rubric with criteria |
| `update_rubric` | PUT | `/api/v1/courses/{id}/rubrics/{rid}` | Update rubric |
| `delete_rubric` | DELETE | `/api/v1/courses/{id}/rubrics/{rid}` | Delete rubric |
| `associate_rubric_with_assignment` | POST | `/api/v1/courses/{id}/assignments/{aid}` | Link rubric to assignment |
| `grade_with_rubric` | PUT | `/api/v1/courses/{id}/assignments/{aid}/submissions/{uid}` | Grade using rubric |
| `get_submission_rubric_assessment` | GET | `/api/v1/courses/{id}/assignments/{aid}/submissions/{uid}` | Get rubric assessment |

### Discussion Tools (`tools/discussions.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_discussion_topics` | GET | `/api/v1/courses/{id}/discussion_topics` | All discussions |
| `get_discussion_topic_details` | GET | `/api/v1/courses/{id}/discussion_topics/{tid}` | Topic details |
| `get_discussion_with_replies` | GET | `/api/v1/courses/{id}/discussion_topics/{tid}/view` | Full thread |
| `list_discussion_entries` | GET | `/api/v1/courses/{id}/discussion_topics/{tid}/entries` | Top-level entries |
| `get_discussion_entry_details` | GET | `/api/v1/courses/{id}/discussion_topics/{tid}/entries/{eid}` | Single entry |
| `create_discussion_topic` | POST | `/api/v1/courses/{id}/discussion_topics` | Create topic |
| `find_discussion` | GET | `/api/v1/courses/{id}/discussion_topics` | Search discussions |
| `post_discussion_entry` | POST | `/api/v1/courses/{id}/discussion_topics/{tid}/entries` | Post entry |
| `reply_to_discussion_entry` | POST | `/api/v1/courses/{id}/discussion_topics/{tid}/entries/{eid}/replies` | Reply to entry |

### Discussion Analytics (`tools/discussion_analytics.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_discussion_participation_summary` | GET | Multiple discussion endpoints | Participation stats |
| `grade_discussion_participation` | PUT | `/api/v1/courses/{id}/assignments/{aid}/submissions/update_grades` | Grade participation |
| `export_discussion_data` | GET | Discussion endpoints | Export for analysis |

### Messaging Tools (`tools/messaging.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `send_conversation` | POST | `/api/v1/conversations` | Send message (form data) |
| `list_conversations` | GET | `/api/v1/conversations` | List conversations |
| `get_conversation_details` | GET | `/api/v1/conversations/{cid}` | Conversation details |
| `mark_conversations_read` | PUT | `/api/v1/conversations` | Mark as read |
| `send_bulk_messages_from_list` | POST | `/api/v1/conversations` (per recipient) | Bulk messaging |
| `send_peer_review_reminders` | POST | `/api/v1/conversations` | Peer review reminders |
| `send_peer_review_followup_campaign` | POST | `/api/v1/conversations` | Follow-up campaign |

### Analytics Tools (`tools/analytics.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_course_student_summaries` | GET | `/api/v1/courses/{id}/analytics/student_summaries` | Student summaries |
| `get_student_activity` | GET | `/api/v1/courses/{id}/analytics/users/{uid}/activity` | User activity |
| `get_student_assignment_data` | GET | `/api/v1/courses/{id}/analytics/users/{uid}/assignments` | Assignment data |
| `get_student_communication` | GET | `/api/v1/courses/{id}/analytics/users/{uid}/communication` | Message stats |
| `get_course_activity` | GET | `/api/v1/courses/{id}/analytics/activity` | Course-wide activity |
| `get_assignment_statistics` | GET | `/api/v1/courses/{id}/analytics/assignments` | Score distributions |
| `get_assignment_analytics` | GET | `/api/v1/courses/{id}/assignments/{aid}/submissions` | Assignment performance |
| `get_student_analytics` | GET | Multiple analytics endpoints | Comprehensive student view |
| `start_course_report` | POST | `/api/v1/courses/{id}/reports/{type}` | Start Canvas report |
| `get_report_status` | GET | `/api/v1/courses/{id}/reports/{type}/{rid}` | Check report progress |

### Student Tools (`tools/student_tools.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_my_upcoming_assignments` | GET | `/api/v1/users/self/upcoming_events` | Personal upcoming |
| `get_my_todo_items` | GET | `/api/v1/users/self/todo` | Personal TODO list |
| `get_my_submission_status` | GET | `/api/v1/courses/{id}/assignments` + submissions | Submission tracker |
| `get_my_course_grades` | GET | `/api/v1/courses` with enrollments | All grades |
| `get_my_peer_reviews_todo` | GET | `/api/v1/courses/{id}/assignments/{aid}/peer_reviews` | Pending reviews |

### Module Tools (`tools/modules.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_modules` | GET | `/api/v1/courses/{id}/modules` | All modules |
| `list_module_items` | GET | `/api/v1/courses/{id}/modules/{mid}/items` | Module items |
| `create_module` | POST | `/api/v1/courses/{id}/modules` | Create module |
| `update_module` | PUT | `/api/v1/courses/{id}/modules/{mid}` | Update module |
| `delete_module` | DELETE | `/api/v1/courses/{id}/modules/{mid}` | Delete module |
| `add_module_item` | POST | `/api/v1/courses/{id}/modules/{mid}/items` | Add item |
| `update_module_item` | PUT | `/api/v1/courses/{id}/modules/{mid}/items/{iid}` | Update item |
| `delete_module_item` | DELETE | `/api/v1/courses/{id}/modules/{mid}/items/{iid}` | Delete item |

### Page Tools (`tools/pages.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_pages` | GET | `/api/v1/courses/{id}/pages` | All pages |
| `get_page_content` | GET | `/api/v1/courses/{id}/pages/{url}` | Page body |
| `get_page_details` | GET | `/api/v1/courses/{id}/pages/{url}` | Page metadata |
| `get_front_page` | GET | `/api/v1/courses/{id}/front_page` | Course front page |
| `create_page` | POST | `/api/v1/courses/{id}/pages` | Create page |
| `edit_page_content` | PUT | `/api/v1/courses/{id}/pages/{url}` | Update content |
| `update_page_settings` | PUT | `/api/v1/courses/{id}/pages/{url}` | Publish, front page |
| `bulk_update_pages` | PUT | Multiple page endpoints | Batch operations |

### Quiz Tools (`tools/quizzes.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_quizzes` | GET | `/api/v1/courses/{id}/quizzes` | All quizzes |
| `get_quiz_details` | GET | `/api/v1/courses/{id}/quizzes/{qid}` | Quiz details |
| `create_quiz` | POST | `/api/v1/courses/{id}/quizzes` | Create quiz |
| `update_quiz` | PUT | `/api/v1/courses/{id}/quizzes/{qid}` | Update quiz |
| `delete_quiz` | DELETE | `/api/v1/courses/{id}/quizzes/{qid}` | Delete quiz |
| `publish_quiz` | PUT | `/api/v1/courses/{id}/quizzes/{qid}` | Publish |
| `unpublish_quiz` | PUT | `/api/v1/courses/{id}/quizzes/{qid}` | Unpublish |
| `list_quiz_questions` | GET | `/api/v1/courses/{id}/quizzes/{qid}/questions` | Questions |
| `add_quiz_question` | POST | `/api/v1/courses/{id}/quizzes/{qid}/questions` | Add question |
| `update_quiz_question` | PUT | `/api/v1/courses/{id}/quizzes/{qid}/questions/{qqid}` | Update question |
| `delete_quiz_question` | DELETE | `/api/v1/courses/{id}/quizzes/{qid}/questions/{qqid}` | Delete question |
| `get_quiz_statistics` | GET | `/api/v1/courses/{id}/quizzes/{qid}/statistics` | Quiz stats |
| `list_quiz_submissions` | GET | `/api/v1/courses/{id}/quizzes/{qid}/submissions` | Submissions |

### Peer Review Tools (`tools/peer_reviews.py` + `peer_review_comments.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_peer_reviews` | GET | `/api/v1/courses/{id}/assignments/{aid}/peer_reviews` | All reviews |
| `get_peer_review_assignments` | GET | Peer review + submission endpoints | Review assignments |
| `assign_peer_review` | POST | `/api/v1/courses/{id}/assignments/{aid}/submissions/{sid}/peer_reviews` | Create review |
| `get_peer_review_completion_analytics` | GET | Multiple endpoints | Completion stats |
| `get_peer_review_followup_list` | GET | Multiple endpoints | Follow-up priorities |
| `generate_peer_review_report` | GET | Multiple endpoints | Report generation |
| `get_peer_review_comments` | GET | Submission comment endpoints | Extract comments |
| `analyze_peer_review_quality` | GET | Comment + quality analysis | Quality metrics |
| `identify_problematic_peer_reviews` | GET | Comment analysis | Flag issues |
| `generate_peer_review_feedback_report` | GET | Multiple endpoints | Feedback report |
| `extract_peer_review_dataset` | GET | Multiple endpoints | Dataset export |

### Enrollment Tools (`tools/enrollment.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `list_users` | GET | `/api/v1/courses/{id}/users` | Course users |
| `find_student` | GET | `/api/v1/courses/{id}/users` + search | Find by name/email |
| `create_user` | POST | `/api/v1/accounts/{aid}/users` | Create user |
| `enroll_user` | POST | `/api/v1/courses/{id}/enrollments` | Enroll in course |
| `list_groups` | GET | `/api/v1/courses/{id}/groups` | Course groups |

### Gradebook Tools (`tools/gradebook.py`)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `export_grades` | GET | Assignment + submission endpoints | Grade export (CSV) |
| `get_assignment_groups` | GET | `/api/v1/courses/{id}/assignment_groups` | Assignment groups |
| `create_assignment_group` | POST | `/api/v1/courses/{id}/assignment_groups` | Create group |
| `update_assignment_group` | PUT | `/api/v1/courses/{id}/assignment_groups/{gid}` | Update group |
| `configure_late_policy` | POST/PUT | `/api/v1/courses/{id}/late_policy` | Late policy |
| `list_grading_periods` | GET | `/api/v1/courses/{id}/grading_periods` | Grading periods |

### Other Tools

| Tool | Module | Method | Endpoint | Description |
|------|--------|--------|----------|-------------|
| `list_announcements` | other_tools | GET | `/api/v1/announcements` | Course announcements |
| `create_announcement` | other_tools | POST | `/api/v1/courses/{id}/discussion_topics` | Create announcement |
| `delete_announcements` | other_tools | DELETE | `/api/v1/courses/{id}/discussion_topics/{tid}` | Delete announcement |
| `get_unread_count` | other_tools | GET | `/api/v1/conversations/unread_count` | Unread messages |
| `find_assignment` | search_helpers | GET | `/api/v1/courses/{id}/assignments` | Search assignments |
| `find_discussion` | search_helpers | GET | `/api/v1/courses/{id}/discussion_topics` | Search discussions |
| `copy_course_content` | content_migrations | POST | `/api/v1/courses/{id}/content_migrations` | Copy content |
| `scan_course_content_accessibility` | accessibility | GET | UDOIT integration | a11y scan |
| `create_student_anonymization_map` | accessibility | GET | User endpoints | Anonymization CSV |
| `get_anonymization_status` | accessibility | - | Local state | Check anonymization |

## Canvas API Conventions

### Course Identifiers
All course parameters accept three formats:
- **Canvas ID:** `12345` (numeric)
- **Course code:** `CS101_2024_Fall` (human-readable)
- **SIS ID:** `sis_course_id:SIS123` (institutional)

Resolution handled by `core/cache.py:get_course_id()`.

### Form Data vs JSON
- **Form data required:** Submissions, modules, conversations, rubric grading
- **JSON used:** Most other creation/update operations
- **Convention:** Tools use `use_form_data=True` parameter in `make_canvas_request()`

### Pagination
- Default `per_page`: 10-100 depending on endpoint
- Automatic collection via `fetch_all_paginated_results()`
- Canvas uses `Link` header with `rel="next"` for pagination

### Include Parameters
Many endpoints accept `include[]` arrays for extra data:
- `include[]=submission` - Include submission with assignment
- `include[]=user` - Include user details
- `include[]=rubric_assessment` - Include rubric scoring
- `include[]=total_scores` - Include enrollment grades
