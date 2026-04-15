# API Contracts

**Project:** canvas-mcp · **Version:** 1.0.6
**Generated:** 2026-04-14 (full rescan, exhaustive)

**Total surface:** **129 MCP tools**, **3 resources**, **1 prompt** across 23 tool modules.

All Canvas API traffic routes through `core/client.py::make_canvas_request()`. All inputs pass through `@validate_params` (see `core/validation.py`). All student data passes through `anonymize_response_data()` at the response boundary when `ENABLE_DATA_ANONYMIZATION=true`.

---

## Connection Summary

- **Base URL:** `{CANVAS_API_URL}` (must include `/api/v1`)
- **Auth:** `Authorization: Bearer {CANVAS_API_TOKEN}`
- **Content-Type:** `application/json` (default) or `application/x-www-form-urlencoded` (tools pass `use_form_data=True`)
- **Pagination:** RFC 5988 Link headers via `fetch_all_paginated_results()`
- **Retry:** 3× on HTTP 429 with exponential backoff honoring `Retry-After`
- **Anonymization:** Applied once after response parse, endpoint-dispatched (see `_should_anonymize_endpoint` + `_determine_data_type` in `core/client.py`)

---

## Resources (MCP Resources)

| URI | Function | Canvas backend |
|-----|----------|----------------|
| `canvas://course/{course_identifier}/syllabus` | `get_course_syllabus` | `GET /courses/{id}` → `syllabus_body` field |
| `canvas://course/{course_identifier}/assignment/{assignment_id}/description` | `get_assignment_description` | `GET /courses/{id}/assignments/{id}` → `description` field |
| `canvas://code-api/{file_path}` | `get_code_api_file` | Reads from `src/canvas_mcp/code_api/` (path-traversal-checked; `.ts/.js/.mts/.mjs` only) |

## Prompts (MCP Prompts)

| Name | Function | Action |
|------|----------|--------|
| `summarize-course` | `summarize_course(course_identifier)` | Returns system+user prompt with course info, assignment count, upcoming assignment count, module count |

---

## Tool Conventions

Every tool below:
- Is `async def` decorated with `@mcp.tool()` + `@validate_params`
- Accepts `course_identifier: str | int` (ID, course code, or `sis_course_id:…`) resolved by `get_course_id()`
- Returns a JSON-serialized `str` (errors have an `"error"` key; never raises)
- Formats dates via `format_date()` / `format_date_smart()`
- Honors `CANVAS_MCP_VERBOSITY` when documented

---

## 1. `accessibility.py` — 4 tools · `register_accessibility_tools`

| Tool | Signature | Canvas endpoint | Notes |
|------|-----------|-----------------|-------|
| `fetch_ufixit_report` | `(course_identifier)` | `GET /courses/{id}/ufixit_summary` | Requires UFIXIT integration |
| `parse_ufixit_violations` | `(course_identifier, include_fixes=False)` | — (processes fetched data) | Maps error codes → WCAG criteria |
| `format_accessibility_summary` | `(course_identifier, verbosity=None)` | — | Verbosity-aware |
| `scan_course_content_accessibility` | `(course_identifier, check_html=True, check_alt_text=True)` | fetches course content | HTML semantic + alt-text checks |

## 2. `analytics.py` — 11 tools · `register_analytics_tools`

| Tool | Signature | Canvas endpoint |
|------|-----------|-----------------|
| `get_course_student_summaries` | `(course_identifier)` | `GET /courses/{id}/users` (paginated) |
| `get_student_activity` | `(course_identifier, user_id, start_date=None, end_date=None)` | `GET /courses/{id}/analytics/users/{user_id}` |
| `get_student_assignment_data` | `(course_identifier, user_id)` | `GET /courses/{id}/assignments` + `GET /courses/{id}/students/submissions` |
| `get_student_communication` | `(course_identifier, user_id)` | `GET /courses/{id}/discussion_topics` + `/announcements` |
| `get_course_activity` | `(course_identifier, start_date=None, end_date=None)` | `GET /courses/{id}/analytics` |
| `get_assignment_statistics` | `(course_identifier, assignment_id=None)` | `GET /courses/{id}/assignments/{id}/submissions` |
| `start_course_report` | `(course_identifier, report_type)` | `POST /courses/{id}/reports/{report_type}` |
| `get_report_status` | `(course_identifier, report_id)` | `GET /courses/{id}/reports/{report_type}/{id}` |
| `get_anonymization_status` | `(course_identifier)` | — (local state) |
| `get_student_analytics` | `(course_identifier, user_id)` | aggregates multiple endpoints |
| `create_student_anonymization_map` | `(course_identifier, output_format="csv")` | — (local generation) |

## 3. `assignment_analytics.py` — 9 tools · `register_assignment_analytics_tools`

| Tool | Purpose |
|------|---------|
| `list_submissions` | List submissions for an assignment |
| `get_submission_content` | Get the text/body/URL of a specific submission |
| `get_submission_comments` | List comments on a submission |
| `post_submission_comment` | Post a comment on a submission |
| `get_submission_history` | Retrieve submission history (all attempts) for a student |
| `download_submission_attachment` | Download a file attached to a submission |
| `list_ungraded_submissions` | List submissions without grades |
| `list_resubmitted_after_grading` | List submissions resubmitted after initial grading |
| `get_assignment_analytics` | Statistical analytics (mean, median, distribution) for an assignment |

Primary endpoints: `GET /courses/{id}/assignments/{id}/submissions`, `/submission_history`, `/comments`.

## 4. `assignments.py` — 8 tools · `register_assignment_tools`

| Tool | Signature | Canvas endpoint | Notes |
|------|-----------|-----------------|-------|
| `list_grading_periods` | `(course_identifier)` | `GET /courses/{id}/grading_periods` | Paginated |
| `list_assignments` | `(course_identifier, include_submission_types=False, verbosity=None)` | `GET /courses/{id}/assignments` | Paginated, verbosity-aware |
| `get_assignment_details` | `(course_identifier, assignment_id)` | `GET /courses/{id}/assignments/{id}` | Includes rubric |
| `update_assignment` | `(course_identifier, assignment_id, name?, description?, due_date?, points_possible?)` | `PUT /courses/{id}/assignments/{id}` | Markdown→HTML auto-conversion |
| `delete_assignment` | `(course_identifier, assignment_id)` | `DELETE /courses/{id}/assignments/{id}` | Irreversible |
| `assign_peer_review` | `(course_identifier, assignment_id, assessor_user_id, subject_user_id)` | `POST /courses/{id}/assignments/{id}/peer_reviews` | — |
| `list_peer_reviews` | `(course_identifier, assignment_id, submission_id=None)` | `GET /courses/{id}/assignments/{id}/peer_reviews` | Optional submission filter |
| `create_assignment` | `(course_identifier, name, description?, due_date?, points_possible?, submission_types?, publish=False)` | `POST /courses/{id}/assignments` | Markdown→HTML auto-conversion |

## 5. `code_execution.py` — 2 tools · `register_code_execution_tools` (developer-only: `user_type=all`)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `execute_typescript` | `(code, sandbox_mode="auto", allowed_hosts=None, memory_limit_mb=None, cpu_limit_millicpus=None, timeout_seconds=30)` | Run user-supplied TS in Node.js sandbox with Canvas API access |
| `list_code_api_modules` | `(detail_level="names")` | Introspect TS `code_api/` exports (names / signatures / full) |

**Security:** network allowlist guard injected as a prelude, container image SHA256 check, memory/CPU/timeout enforcement; modes: `auto` (detect), `local` (Node), `container` (Docker/Podman).

## 6. `content_migrations.py` — 1 tool · `register_content_migration_tools`

| Tool | Signature | Canvas endpoint |
|------|-----------|-----------------|
| `copy_course_content` | `(source_course_identifier, target_course_identifier, include_items=None, exclude_items=None)` | `POST /courses/{target_id}/content_migrations` (migration_type=`course_copy_importer`) |

## 7. `courses.py` — 3 tools · `register_course_tools`

| Tool | Signature | Canvas endpoint |
|------|-----------|-----------------|
| `list_courses` | `(account_id=None, include_syllabus=False, verbosity=None)` | `GET /accounts/{id}/courses` or `GET /courses` |
| `get_course_details` | `(course_identifier, include_syllabus=False)` | `GET /courses/{id}` |
| `get_course_content_overview` | `(course_identifier)` | Aggregates `/modules`, `/assignments`, `/discussion_topics`, `/pages` |

## 8. `discovery.py` — 1 tool · `register_discovery_tools` (developer-only: `user_type=all`)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `search_canvas_tools` | `(query, detail_level="names")` | Fuzzy-search `code_api/` TS exports by name/docstring |

## 9. `discussion_analytics.py` — 3 tools · `register_discussion_analytics_tools`

| Tool | Signature | Canvas endpoint |
|------|-----------|-----------------|
| `get_discussion_participation_summary` | `(course_identifier, discussion_id, categorize="all")` | `GET /courses/{id}/discussion_topics/{id}/entries` |
| `grade_discussion_participation` | `(course_identifier, discussion_id, assignment_id=None, dry_run=True, min_posts=0, min_replies=0)` | entries + optionally `PUT /courses/{id}/assignments/{id}/submissions/{user_id}` |
| `export_discussion_data` | `(course_identifier, discussion_id, format="csv")` | local aggregation (CSV/JSON) |

## 10. `discussions.py` — 11 tools · `register_discussion_tools`

| Tool | Purpose | Primary endpoint |
|------|---------|------------------|
| `list_discussion_topics` | List topics in a course | `GET /courses/{id}/discussion_topics` |
| `get_discussion_topic_details` | Topic metadata | `GET /courses/{id}/discussion_topics/{id}` |
| `list_discussion_entries` | List entries with optional full content + replies | `GET /courses/{id}/discussion_topics/{id}/entries` |
| `get_discussion_entry_details` | Entry + all replies | `GET /courses/{id}/discussion_topics/{id}/entries/{id}` |
| `get_discussion_with_replies` | Enhanced entries fetcher with reply expansion | `/entries` + `/replies` |
| `post_discussion_entry` | Post top-level entry | `POST /courses/{id}/discussion_topics/{id}/entries` |
| `reply_to_discussion_entry` | Reply to an entry | `POST /courses/{id}/discussion_topics/{id}/entries/{id}/replies` |
| `create_discussion_topic` | Create new topic | `POST /courses/{id}/discussion_topics` |
| `list_announcements` | List announcements | `GET /courses/{id}/discussion_topics?only_announcements=true` |
| `create_announcement` | Create announcement with optional scheduling | `POST /courses/{id}/discussion_topics` (is_announcement=true) |
| `delete_announcements` | Delete by ID/filter — **defaults to dry_run=True for safety** | `DELETE /courses/{id}/discussion_topics/{id}` |

## 11. `enrollment.py` — 5 tools · `register_enrollment_tools`

| Tool | Signature | Canvas endpoint |
|------|-----------|-----------------|
| `create_user` | `(account_id, name, email, login_id=None, sis_user_id=None, send_confirmation=False, skip_confirmation=True)` | `POST /accounts/{id}/users` |
| `enroll_user` | `(course_identifier, user_id, enrollment_type="StudentEnrollment", enrollment_state="active", notify=False)` | `POST /courses/{id}/enrollments` |
| `submit_file_for_student` | `(course_identifier, assignment_id, user_id, file_path, content_type=None, comment=None)` | 3-step upload + `POST /submissions` |
| `list_groups` | `(course_identifier)` | `GET /courses/{id}/groups` + `GET /groups/{id}/users` |
| `list_users` | `(course_identifier, verbosity=None)` | `GET /courses/{id}/users` (+enrollments, email) |

Enrollment types: `StudentEnrollment / TeacherEnrollment / TaEnrollment / ObserverEnrollment / DesignerEnrollment`. States: `active / invited / creation_pending / inactive`.

## 12. `gradebook.py` — 5 tools · `register_gradebook_tools`

| Tool | Signature | Canvas endpoint |
|------|-----------|-----------------|
| `export_grades` | `(course_identifier, format="csv", include_hidden=False)` | `GET /assignments` + `GET /students/submissions` |
| `get_assignment_groups` | `(course_identifier)` | `GET /courses/{id}/assignment_groups` |
| `create_assignment_group` | `(course_identifier, name, weight=None)` | `POST /courses/{id}/assignment_groups` |
| `update_assignment_group` | `(course_identifier, group_id, name?, weight?, drop_lowest?, drop_highest?)` | `PUT /courses/{id}/assignment_groups/{id}` |
| `configure_late_policy` | `(course_identifier, late_submission_interval="day", late_submission_minimum_percent=0.0, missing_submission_percent=0.0)` | `PUT /courses/{id}` |

## 13. `grading_export.py` — 1 tool · `register_grading_export_tools` ★ NEW

| Tool | Signature | Purpose |
|------|-----------|---------|
| `grading_export` | `(course_code=None, assignment_filter=None, group_filter=None, student_filter=None, gender_csv_path=None, submission_state_filter=None, date_start=None, date_end=None, grade_min=None, grade_max=None, format="csv")` | Specialized per-assignment bulk submission export (Science 8 Cottone). Uses `GET /courses/{id}/assignments/{id}/submissions` endpoint (switched in commit `0307c55`). Hardcoded period→course-ID map (P1–P9). CSV includes: Student ID, Name, Gender, Assignment, Submission Time, Grade, Points, Status. |

## 14. `messaging.py` — 8 tools · `register_messaging_tools`

| Tool | Signature | Canvas endpoint | Notes |
|------|-----------|-----------------|-------|
| `send_conversation` | `(course_identifier, recipient_ids, subject, body, group_conversation=False, bulk_message=False, context_code=None, mode="sync", force_new=False, attachment_ids=None)` | `POST /conversations` | Form-encoded |
| `send_peer_review_reminders` | `(course_identifier, assignment_id, recipient_ids, custom_message=None, include_assignment_link=True, subject_prefix="Peer Review Reminder")` | `POST /conversations` | Uses `MessageTemplates` |
| `list_conversations` | `(scope="unread", filter_ids=None, filter_mode="and", include_participants=True, include_all_ids=False)` | `GET /conversations` | — |
| `get_conversation_details` | `(conversation_id, auto_mark_read=True, include_messages=True)` | `GET /conversations/{id}` | — |
| `get_unread_count` | `()` | `GET /conversations/unread_count` | — |
| `mark_conversations_read` | `(conversation_ids)` | `PUT /conversations` | Batch update |
| `send_bulk_messages_from_list` | `(course_identifier, recipient_data, subject_template, body_template, context_code=None, mode="sync")` | multiple `POST /conversations` | Template interpolation |
| `send_peer_review_followup_campaign` | `(course_identifier, assignment_id)` | analytics + `POST /conversations` | Chained analytics→messaging pipeline |

## 15. `modules.py` — 8 tools · `register_module_tools`

| Tool | Purpose | Canvas endpoint |
|------|---------|-----------------|
| `list_modules` | List course modules | `GET /courses/{id}/modules` |
| `create_module` | Create module (supports prerequisites) | `POST /courses/{id}/modules` (form data) |
| `update_module` | Update module settings | `PUT /courses/{id}/modules/{id}` (form data) |
| `delete_module` | Delete module (items unlinked) | `DELETE /courses/{id}/modules/{id}` |
| `add_module_item` | Add item (File/Page/Discussion/Assignment/Quiz/SubHeader/ExternalUrl/ExternalTool) | `POST /courses/{id}/modules/{id}/items` |
| `update_module_item` | Update item, move across modules, completion requirements | `PUT /courses/{id}/modules/{id}/items/{id}` |
| `list_module_items` | List items with content details | `GET /courses/{id}/modules/{id}/items` |
| `delete_module_item` | Remove item (content preserved) | `DELETE /courses/{id}/modules/{id}/items/{id}` |

## 16. `pages.py` — 8 tools · `register_page_tools`

| Tool | Purpose | Canvas endpoint |
|------|---------|-----------------|
| `list_pages` | List with sort/filter + verbosity | `GET /courses/{id}/pages` |
| `get_page_content` | Full HTML body | `GET /courses/{id}/pages/{url}` |
| `get_page_details` | Metadata (dates, editor, status, roles) | `GET /courses/{id}/pages/{url}` |
| `get_front_page` | Course front page | `GET /courses/{id}/front_page` |
| `create_page` | Create with body + publish flag | `POST /courses/{id}/pages` |
| `edit_page_content` | Replace HTML body | `PUT /courses/{id}/pages/{url}` |
| `update_page_settings` | Publish, front page, editing roles, notify | `PUT /courses/{id}/pages/{url}` |
| `bulk_update_pages` | Batch settings update | Multiple `PUT` calls |

Editing roles: `teachers / students / members / public`.

## 17. `peer_review_comments.py` — 5 tools · `register_peer_review_comment_tools`

| Tool | Purpose |
|------|---------|
| `get_peer_review_comments` | Extract actual comment text (optional anonymize) |
| `analyze_peer_review_quality` | Quality score + constructiveness + sentiment (via `PeerReviewCommentAnalyzer`) |
| `identify_problematic_peer_reviews` | Flag low-word-count, generic, harsh, low-quality reviews |
| `extract_peer_review_dataset` | Export to CSV/JSON (optional local save) |
| `generate_peer_review_feedback_report` | Markdown instructor report |

## 18. `peer_reviews.py` — 4 tools · `register_peer_review_tools`

| Tool | Purpose |
|------|---------|
| `get_peer_review_assignments` | Reviewer→reviewee mapping with completion status |
| `get_peer_review_completion_analytics` | Per-student breakdown grouped by `none_complete` / `partial_complete` / `all_complete` |
| `generate_peer_review_report` | Markdown/CSV/JSON report with exec summary, action items, timeline |
| `get_peer_review_followup_list` | Prioritized follow-up list (urgent / medium / low) with optional contact info |

All wrap `core.peer_reviews.PeerReviewAnalyzer`.

## 19. `quizzes.py` — 13 tools · `register_quiz_tools`

| Tool | Purpose |
|------|---------|
| `list_quizzes` | List with optional search |
| `get_quiz_details` | Full quiz metadata |
| `create_quiz` | Full settings (unpublished by default) |
| `update_quiz` | Update settings |
| `delete_quiz` | Permanent delete |
| `publish_quiz` / `unpublish_quiz` | Toggle published |
| `list_quiz_questions` | Questions with previews |
| `add_quiz_question` | MC/TF/Essay/FITB/Matching/Numerical |
| `update_quiz_question` | Edit |
| `delete_quiz_question` | Remove |
| `get_quiz_statistics` | `GET /courses/{id}/quizzes/{id}/statistics` (submission + per-question analytics) |
| `list_quiz_submissions` | `GET /courses/{id}/quizzes/{id}/submissions` |

Quiz types: `assignment / practice_quiz / graded_survey / survey`. Allowed attempts: `-1` = unlimited.

## 20. `rubrics.py` — 8 tools · `register_rubric_tools`

| Tool | Canvas endpoint |
|------|-----------------|
| `list_assignment_rubrics` | `GET /courses/{id}/assignments/{id}` (include=rubric,rubric_settings) |
| `get_assignment_rubric_details` | same as above (detailed criteria) |
| `get_rubric_details` | `GET /courses/{id}/rubrics/{id}` |
| `list_all_rubrics` | `GET /courses/{id}/rubrics` |
| `create_rubric` | `POST /courses/{id}/rubrics` — accepts object or array rating format |
| `update_rubric` | `PUT /courses/{id}/rubrics/{id}` |
| `delete_rubric` | `DELETE /courses/{id}/rubrics/{id}` |
| `associate_rubric_with_assignment` | `PUT /courses/{id}/rubrics/{id}` (rubric_association) |

## 21. `rubric_grading.py` — 3 tools · `register_rubric_grading_tools`

| Tool | Canvas endpoint |
|------|-----------------|
| `get_submission_rubric_assessment` | `GET /courses/{id}/assignments/{id}/submissions/{id}` (include=rubric_assessment) |
| `grade_with_rubric` | `PUT /courses/{id}/assignments/{id}/submissions/{id}` (form-encoded rubric_assessment) |
| `bulk_grade_submissions` | `POST /courses/{id}/assignments/{id}/submissions/update_grades` (bulk); rubric-based grades fall back to per-submission PUT |

Rubric assessment form keys: `rubric_assessment[{criterion_id}][points]`, `[rating_id]`, `[comments]`. Criterion IDs often start with `_` (e.g., `_8027`).

## 22. `search_helpers.py` — 3 tools · `register_search_helper_tools`

| Tool | Canvas endpoint |
|------|-----------------|
| `find_assignment` | `GET /courses/{id}/assignments?search_term=X` + client-side fallback |
| `find_student` | `GET /courses/{id}/users?enrollment_type[]=student&search_term=X` |
| `find_discussion` | `GET /courses/{id}/discussion_topics` (client-side filter) |

## 23. `student_tools.py` — 5 tools · `register_student_tools` (role-gated)

| Tool | Canvas endpoint |
|------|-----------------|
| `get_my_upcoming_assignments` | `GET /users/self/upcoming_events` |
| `get_my_submission_status` | `GET /courses/{id}/assignments?include[]=submission` |
| `get_my_course_grades` | `GET /courses?include[]=total_scores,current_grading_period_scores` |
| `get_my_todo_items` | `GET /users/self/todo` |
| `get_my_peer_reviews_todo` | `GET /courses/{id}/assignments/{id}/peer_reviews` |

Gated on `CANVAS_MCP_USER_TYPE ∈ {"all", "student"}`. All use `/users/self` only.

---

## Helper Module (not a tool module)

### `message_templates.py` — 0 MCP tools

Exports class `MessageTemplates` with `PEER_REVIEW_TEMPLATES`, `ASSIGNMENT_TEMPLATES`, `DISCUSSION_TEMPLATES`, `GRADE_TEMPLATES`, `GRADING_FEEDBACK_TEMPLATES` and methods:
- `get_template(category, template_name) → dict`
- `format_template(template, variables) → dict`
- `get_formatted_template(category, template_name, variables)`
- `list_available_templates() → dict`
- `get_template_variables(category, template_name) → list`
- `compose_grading_feedback(student_name, assignment_name, total_score, max_total, criterion_feedbacks) → str`

Plus module-level `create_default_variables(student_name, assignment_name, instructor_name=None, course_name=None, **kwargs) → dict`.

Used by: `messaging.py` (peer review reminders / follow-up campaigns).

---

## TypeScript `code_api/` Exports (invoked via `execute_typescript`)

| Function | Input | Canvas endpoint |
|----------|-------|-----------------|
| `initializeCanvasClient(apiUrl, apiToken, timeout?)` | — | client init |
| `listCourses()` | — | `GET /courses` (paginated) |
| `getCourseDetails({ courseIdentifier })` | — | `GET /courses/{id}` |
| `listSubmissions({ courseIdentifier, assignmentId, includeUser? })` | — | `GET /courses/{id}/assignments/{id}/submissions` |
| `sendMessage({ recipients, subject, body, contextCode?, attachmentIds? })` | — | `POST /conversations` |
| `listDiscussions({ courseIdentifier })` | — | `GET /courses/{id}/discussion_topics` |
| `postEntry({ courseIdentifier, topicId, message, attachmentIds? })` | — | `POST /courses/{id}/discussion_topics/{id}/entries` |
| `bulkGradeDiscussion(input)` | initial-post points, peer-review points, peer-review cap, late penalties, dryRun, maxConcurrent | `PUT /courses/{id}/assignments/{id}/submissions/{user_id}` (batch) |
| `bulkGrade(input)` | `(Submission) => GradeResult \| null` callback, maxConcurrent, rateLimitDelay, dryRun | `PUT` per submission |
| `gradeWithRubric(input)` | rubric assessment (criterionId → points/ratingId/comments) OR simple grade string | `PUT /courses/{id}/assignments/{id}/submissions/{user_id}` (form-encoded `rubric_assessment[...]`) |

Client helpers: `canvasGet/Post/Put/Delete/PutForm`, `fetchAllPaginated<T>`. Retries 3× at 1/2/4s backoff. Default 30s timeout.

---

## Error Envelope

All tools return JSON strings. Errors are formatted by `core/validation.py::format_error()`:

```json
{"error": "Human-readable message", "details": "Optional context"}
```

Use `core/validation.py::is_error_response(parsed_dict)` to detect errors. Tools never raise; they return the envelope.

---

## Canvas Response Anonymization Map

When `ENABLE_DATA_ANONYMIZATION=true`, `core/client.py::_determine_data_type()` dispatches based on endpoint substring:

| Endpoint contains | Data type |
|-------------------|-----------|
| `/users`, `/user_*`, `/enrollments` | user |
| `/submissions`, `/submission_*` | submission |
| `/assignments` (without `/submissions`) | assignment |
| `/discussion_topics`, `/entries` | discussion_entry |
| else | general |

`_should_anonymize_endpoint()` returns `False` for `/courses`, `/accounts`, `/terms`, `/grading_periods` unless the path also contains `/users`. Real user IDs are always preserved for functionality (messaging etc.); only names/emails/SIS IDs/free-text PII are redacted.
