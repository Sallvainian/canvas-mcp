---
title: 'Codebase Cleanup & Maintainability Overhaul'
slug: 'codebase-cleanup-maintainability'
created: '2026-03-12'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - Python 3.12+
  - FastMCP 2.14+
  - mypy 1.5+ (strict)
  - ruff 0.15+
  - black 23+
  - pytest 7+
  - core/logging.py (log_error, log_warning, log_info, log_debug)
files_to_modify:
  - src/canvas_mcp/core/client.py
  - src/canvas_mcp/core/dates.py
  - src/canvas_mcp/core/cache.py
  - src/canvas_mcp/core/config.py
  - src/canvas_mcp/core/peer_reviews.py
  - src/canvas_mcp/core/peer_review_comments.py
  - src/canvas_mcp/core/__init__.py
  - src/canvas_mcp/__init__.py
  - src/canvas_mcp/resources/resources.py
  - src/canvas_mcp/tools/assignments.py
  - src/canvas_mcp/tools/rubrics.py
  - src/canvas_mcp/tools/other_tools.py
  - src/canvas_mcp/tools/pages.py
  - src/canvas_mcp/tools/modules.py
  - src/canvas_mcp/tools/enrollment.py
  - src/canvas_mcp/tools/analytics.py
  - src/canvas_mcp/tools/messaging.py
  - src/canvas_mcp/tools/discussions.py
  - src/canvas_mcp/tools/discovery.py
  - src/canvas_mcp/tools/student_tools.py
  - src/canvas_mcp/tools/search_helpers.py
  - src/canvas_mcp/tools/code_execution.py
  - src/canvas_mcp/tools/content_migrations.py
  - src/canvas_mcp/tools/discussion_analytics.py
  - src/canvas_mcp/tools/peer_review_comments.py
  - src/canvas_mcp/tools/__init__.py
  - src/canvas_mcp/server.py
  - pyproject.toml
code_patterns:
  - 'register_*_tools(mcp: FastMCP) pattern for tool registration'
  - '@mcp.tool() then @validate_params decorator order'
  - 'make_canvas_request() returns Any -- root cause of 100+ mypy errors downstream'
  - 'fetch_all_paginated_results() returns Any -- returns list[Any] on success, dict on error'
  - 'get_course_code() accepts str but callers pass str | None -- 10+ arg-type errors'
  - 'Return error dicts, never raise exceptions'
test_patterns:
  - 'tests/tools/test_{module}.py matching src/canvas_mcp/tools/{module}.py'
  - 'mock make_canvas_request, not httpx directly'
  - 'get_tool_function(mcp, "tool_name") for extraction'
  - 'Tests import by module path -- helper functions that move need re-exports (e.g., build_bulk_grade_form_data)'
---

# Tech-Spec: Codebase Cleanup & Maintainability Overhaul

**Created:** 2026-03-12

## Overview

### Problem Statement

The canvas-mcp codebase has accumulated 212 mypy errors across 24 files, 136 ruff lint violations (118 auto-fixable), 52 raw `print()` calls instead of structured logging, 3 oversized tool files, and a deprecated ruff config format in pyproject.toml. Tests pass (269/269 + 26 skipped), but the codebase doesn't meet its own strict quality standards defined in project-context.md and pyproject.toml.

### Solution

Systematically fix all diagnostic failures, split oversized modules, migrate prints to structured logging, and clean up the catch-all `other_tools.py` -- making the codebase pass its own CI checks and be straightforward for AI agents to navigate and work with.

### Scope

**In Scope:**
- Fix all 212 mypy type errors
- Fix all 136 ruff violations
- Migrate pyproject.toml ruff config to non-deprecated format
- Migrate 36 print() calls to structured logging (16 intentional CLI prints in server.py stay)
- Split assignments.py and rubrics.py into focused sub-modules
- Decompose other_tools.py into 4 existing domain files
- Ensure all 269 existing tests continue passing

**Out of Scope:**
- New features or tool additions
- Test refactoring
- Documentation rewrites
- Architecture changes beyond file splitting

## Context for Development

### Codebase Patterns

- All tool functions live inside `register_*_tools(mcp: FastMCP)` functions
- Decorator order: `@mcp.tool()` FIRST, then `@validate_params`
- New tool modules must be imported in `tools/__init__.py` and called in `server.py:register_all_tools()`
- All Canvas API calls go through `make_canvas_request()` -- never httpx directly
- All tool output through `format_response()` / `format_header()`
- Course identifiers resolved via `await get_course_id(course_identifier)`
- Error handling: return `{"error": "..."}` dicts, never raise exceptions
- Type hints: use `X | Y` and `X | None`, never `Union` or `Optional`
- Logging via `core/logging.py`: `log_error()`, `log_warning()`, `log_info()`, `log_debug()`

### Root Cause Analysis

**Mypy Error Categories (212 total):**

| Category | Count | Root Cause | Fix Strategy |
| -------- | ----- | ---------- | ------------ |
| `object` has no attribute / not indexable / not iterable | ~80 | `make_canvas_request()` and `fetch_all_paginated_results()` return `Any`, but mypy infers `object` in some contexts | Add isinstance narrowing or cast() at call sites |
| `Returning Any from function` | ~20 | Functions return values from `make_canvas_request()` without type narrowing | Add explicit cast() or isinstance checks before returns |
| `arg-type: str \| None` passed to `str` | ~15 | `get_course_code()` signature requires `str` but callers pass `str \| None` | Update `get_course_code()` to accept `str \| None` |
| Missing return type annotation | ~5 | `register_*_tools()` and helpers lack annotations | Add annotations |
| `Union`/`Optional` syntax | ~10 | Legacy type hint syntax | Convert to `X \| Y` / `X \| None` |
| `import-untyped` (dateutil) | 1 | Missing type stubs | Install `types-python-dateutil` |
| Unreachable code | 1 | Dead code in dates.py | Remove unreachable branch |
| `var-annotated` | ~5 | Variables need explicit type annotations | Add annotations |
| Miscellaneous type mismatches | ~75 | Various: list[str] vs list[dict], int vs float, etc. | Case-by-case fixes |

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `src/canvas_mcp/core/logging.py` | Provides log_error, log_warning, log_info, log_debug |
| `src/canvas_mcp/core/client.py` | Root cause: make_canvas_request() -> Any |
| `src/canvas_mcp/core/cache.py` | get_course_code(str) needs to accept str \| None |
| `src/canvas_mcp/tools/__init__.py` | Must update imports after file splits |
| `src/canvas_mcp/server.py` | Must update register_all_tools() after decomposing other_tools |
| `pyproject.toml` | Ruff config, dev dependencies |
| `_bmad-output/project-context.md` | Authoritative conventions reference |

### Technical Decisions

1. **client.py return types -- keep `Any`, fix at call sites.** Changing to a union return would force isinstance checks at 100+ call sites. Instead, add targeted narrowing only where mypy complains.

2. **get_course_code() -- widen parameter type** to `str | None` with early return `None` for `None` input. Fixes ~15 arg-type errors.

3. **assignments.py split -- flat files, not sub-package.** Split into `assignments.py` (CRUD + peer reviews) and `assignment_analytics.py` (submissions + analytics). Preserves import patterns.

4. **rubrics.py split -- flat files.** Split into `rubrics.py` (CRUD + management) and `rubric_grading.py` (grading operations + helpers).

5. **other_tools.py decomposition -- move to existing domain files.** 6 page tools -> pages.py, 1 module item tool -> modules.py, 2 user/group tools -> enrollment.py, 3 analytics/anonymization tools -> analytics.py. Delete other_tools.py.

6. **Print migration -- 36 convert, 16 keep.** 19 errors -> log_error(), 15 warnings -> log_warning(), 2 debug/info -> log_debug()/log_info(). 16 intentional CLI prints in server.py stay as print() (14 config display lines 154-189, 2 test result lines 194+197).

## Implementation Plan

### Phase 1: Foundation (config, dependencies, auto-fixes)

- [ ] Task 1: Update pyproject.toml ruff config and add type stubs
  - File: `pyproject.toml`
  - Action: Move `select`, `ignore`, `per-file-ignores` from `[tool.ruff]` to `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]`. Add `"types-python-dateutil>=2.8.0"` to `[project.optional-dependencies] dev`.
  - Notes: Run `uv pip install -e ".[dev]"` after to install stubs.

- [ ] Task 2: Run ruff auto-fix for all 118 auto-fixable violations
  - File: All `src/` files
  - Action: Run `.venv/bin/python -m ruff check --fix src/`. Then run `.venv/bin/python -m black src/` to reformat.
  - Notes: This handles I001, UP017, UP007, UP045, F401, F541, W292, UP041 in one pass. Manually review F841 (unused variables) after -- some may be intentional destructuring.

- [ ] Task 3: Widen get_course_code() parameter type
  - File: `src/canvas_mcp/core/cache.py`
  - Action: Change `def get_course_code(course_id: str)` to `def get_course_code(course_id: str | None)`. Add early return: `if course_id is None: return None`. Fix the `Returning Any` error on line 111 with an explicit `str()` cast or isinstance check.
  - Notes: This fixes ~15 downstream arg-type errors in search_helpers.py, rubrics.py, analytics.py, student_tools.py.

- [ ] Task 4: Fix core/dates.py issues
  - File: `src/canvas_mcp/core/dates.py`
  - Action: Remove unreachable code at line 194. Fix `no-any-return` at line 276 by adding explicit return type narrowing. The UP017 datetime.UTC fixes should already be handled by Task 2.
  - Notes: Also migrate the 1 print() on line 78 to `log_warning()`.

- [ ] Task 5: Fix core/peer_reviews.py type errors
  - File: `src/canvas_mcp/core/peer_reviews.py`
  - Action: Fix `object has no attribute "append"` errors at lines 531 and 548. These are variables holding API response data typed as `object` -- add isinstance narrowing or explicit `list[Any]` annotations.

- [ ] Task 6: Fix core/peer_review_comments.py type errors
  - File: `src/canvas_mcp/core/peer_review_comments.py`
  - Action: Fix `object not iterable` (line 539), `float <= object` (line 546), and `var-annotated` (line 568). Add proper type annotations and isinstance narrowing.

- [ ] Task 7: Fix resources/resources.py type errors
  - File: `src/canvas_mcp/resources/resources.py`
  - Action: Fix `Returning Any` errors at lines 35 and 62. Add explicit `str()` cast or isinstance check before returns.

**Checkpoint: Run `pytest`, `ruff check src/`, `mypy src/`. Ruff should be at 0. Mypy should be significantly reduced. Tests must pass.**

### Phase 2: Print-to-logging migration

- [ ] Task 8: Migrate core/ prints to logging
  - File: `src/canvas_mcp/core/client.py`
  - Action: Replace 7 print() calls: lines 137, 186, 336 -> `log_debug()`; line 203 -> `log_info()`; lines 216, 220, 312 -> `log_error()`. Add `from .logging import log_debug, log_error, log_info` import.

- [ ] Task 9: Migrate core/config.py prints to logging
  - File: `src/canvas_mcp/core/config.py`
  - Action: Replace 10 print() calls: lines 123-124, 128-129 -> `log_error()`; lines 133-134, 137-148, 152-163 -> `log_warning()`. Add `from .logging import log_error, log_warning` import.

- [ ] Task 10: Migrate core/cache.py prints to logging
  - File: `src/canvas_mcp/core/cache.py`
  - Action: Replace 3 print() calls: line 17 -> `log_debug()`; line 21 -> `log_error()`; line 36 -> `log_info()`. Add logging import.

- [ ] Task 11: Migrate tools/messaging.py prints to logging
  - File: `src/canvas_mcp/tools/messaging.py`
  - Action: Replace 9 print() calls: lines 99, 175, 227, 269, 293, 329, 419, 515 -> `log_error()`; line 518 -> `log_info()`. Add `from ..core.logging import log_error, log_info` import.

- [ ] Task 12: Migrate remaining tool prints to logging
  - File: `src/canvas_mcp/tools/other_tools.py` -- 3 prints at lines 477, 531, 628 -> `log_warning()`
  - File: `src/canvas_mcp/tools/peer_review_comments.py` -- 1 print at line 322 -> `log_info()`
  - File: `src/canvas_mcp/server.py` -- 2 prints at lines 146-147 -> `log_error()`. Keep lines 154-197 as print() (intentional CLI config display).
  - Action: Add logging imports to each file. Replace prints as specified.

**Checkpoint: Run `pytest`. Grep for `print(` in src/ -- should find only the 16 intentional CLI prints in server.py (config display + test results).**

### Phase 3: Decompose other_tools.py

**Important ordering:** Phase 1 must be complete before Phase 3 (ruff auto-fix converts all Union/Optional to pipe syntax first, preventing mixed syntax in destination files). Line numbers below are approximate from pre-refactor state -- use function names to identify code, not line numbers.

**Atomic rule:** For each task 13-16, move the tool functions to the destination AND remove them from other_tools.py in the same step. Do not defer removals -- this prevents double-registration since `register_other_tools(mcp)` is still being called until Task 17.

- [ ] Task 13: Move page tools from other_tools.py to pages.py
  - File: `src/canvas_mcp/tools/pages.py` (destination), `src/canvas_mcp/tools/other_tools.py` (source)
  - Action: Move `list_pages`, `get_page_content`, `get_page_details`, `get_front_page`, `create_page`, `edit_page_content` (approx lines 22-321 of other_tools.py) into `pages.py`. Merge into the existing `register_page_tools(mcp)` function. Ensure all imports are carried over. Remove from other_tools.py. Update the `pages.py` module docstring to reflect full scope (CRUD + settings, not just settings).

- [ ] Task 14: Move list_module_items from other_tools.py to modules.py
  - File: `src/canvas_mcp/tools/modules.py` (destination)
  - Action: Move `list_module_items` (lines 367-425 of other_tools.py) into the existing `register_module_tools(mcp)` function. Carry over imports. Remove from other_tools.py.

- [ ] Task 15: Move user/group tools from other_tools.py to enrollment.py
  - File: `src/canvas_mcp/tools/enrollment.py` (destination)
  - Action: Move `list_groups` and `list_users` (lines 429-587 of other_tools.py) into the existing `register_enrollment_tools(mcp)` function. Carry over imports including anonymization. Remove from other_tools.py.

- [ ] Task 16: Move analytics/anonymization tools from other_tools.py to analytics.py
  - File: `src/canvas_mcp/tools/analytics.py` (destination)
  - Action: Move `get_anonymization_status`, `get_student_analytics`, `create_student_anonymization_map` (lines 324-363, 592-746 of other_tools.py) into the existing `register_analytics_tools(mcp)` function. Carry over imports. Remove from other_tools.py.

- [ ] Task 17: Delete other_tools.py and update registrations
  - File: `src/canvas_mcp/tools/other_tools.py` -- delete entirely
  - File: `src/canvas_mcp/tools/__init__.py` -- remove `register_other_tools` import/export
  - File: `src/canvas_mcp/server.py` -- remove `register_other_tools(mcp)` call from `register_all_tools()`
  - Notes: The tools that were in other_tools.py are now registered by pages, modules, enrollment, and analytics registration functions which are already called in server.py.

**Checkpoint: Run `pytest`. All 269 tests must pass. Verify `other_tools.py` no longer exists. Run `mypy src/` and `ruff check src/`.**

### Phase 4: Split assignments.py

- [ ] Task 18: Create assignment_analytics.py from assignments.py
  - File: `src/canvas_mcp/tools/assignment_analytics.py` (new)
  - Action: Extract from assignments.py: `list_submissions` (line 609), `get_submission_content` (line 726), `get_submission_comments` (line 799), `post_submission_comment` (line 849), `get_submission_history` (line 891), `download_submission_attachment` (line 955), `list_ungraded_submissions` (line 1070), `list_resubmitted_after_grading` (line 1144), `get_assignment_analytics` (line 1261). Create a new `register_assignment_analytics_tools(mcp: FastMCP) -> None` function containing these tools. Copy required imports.
  - Notes: The `description_to_html` helper stays in assignments.py (used by create_assignment). If any extracted tools use it, import from assignments.py.

- [ ] Task 19: Update assignments.py after extraction
  - File: `src/canvas_mcp/tools/assignments.py`
  - Action: Remove the extracted functions. The file should retain: `description_to_html` helper, `register_assignment_tools(mcp)` containing `list_grading_periods`, `list_assignments`, `get_assignment_details`, `update_assignment`, `delete_assignment`, `assign_peer_review`, `list_peer_reviews`, `create_assignment`. Clean up unused imports.

- [ ] Task 20: Register assignment_analytics in server.py
  - File: `src/canvas_mcp/tools/__init__.py` -- add `from .assignment_analytics import register_assignment_analytics_tools`
  - File: `src/canvas_mcp/server.py` -- add `register_assignment_analytics_tools(mcp)` unconditionally alongside the other tool registrations (lines 59-76). Note: register_assignment_tools is called unconditionally, not in a conditional block.

**Checkpoint: Run `pytest`. All 269 tests must pass.**

### Phase 5: Split rubrics.py

- [ ] Task 21: Create rubric_grading.py from rubrics.py
  - File: `src/canvas_mcp/tools/rubric_grading.py` (new)
  - Action: Extract from rubrics.py: helper functions `build_bulk_grade_form_data` (line 246), `build_rubric_assessment_form_data` (line 279), `_grade_single_submission_individual` (line 327). Extract tools: `get_submission_rubric_assessment` (line 640), `grade_with_rubric` (line 754), `bulk_grade_submissions` (line 1271). Create `register_rubric_grading_tools(mcp: FastMCP) -> None`. Copy required imports.
  - Notes: If grading tools reference `format_rubric_response` or `validate_rubric_criteria`, import them from rubrics.py.

- [ ] Task 22: Update rubrics.py after extraction
  - File: `src/canvas_mcp/tools/rubrics.py`
  - Action: Remove extracted functions and helpers. Retain: `preprocess_criteria_string`, `validate_rubric_criteria`, `format_rubric_response`, `build_criteria_structure`, and `register_rubric_tools(mcp)` containing `list_assignment_rubrics`, `get_assignment_rubric_details`, `get_rubric_details`, `list_all_rubrics`, `create_rubric`, `update_rubric`, `delete_rubric`, `associate_rubric_with_assignment`. Clean up unused imports. **Critical:** Add re-export for `build_bulk_grade_form_data` at the top of rubrics.py: `from .rubric_grading import build_bulk_grade_form_data` -- this preserves backward compatibility for `tests/tools/test_rubrics.py` which imports it directly from `canvas_mcp.tools.rubrics` in 4 places (lines 128, 139, 146, 151).

- [ ] Task 23: Register rubric_grading in server.py
  - File: `src/canvas_mcp/tools/__init__.py` -- add `from .rubric_grading import register_rubric_grading_tools`
  - File: `src/canvas_mcp/server.py` -- add `register_rubric_grading_tools(mcp)` unconditionally alongside the other tool registrations (lines 59-76). Note: register_rubric_tools is called unconditionally, not in a conditional block.

**Checkpoint: Run `pytest`. All 269 tests must pass.**

### Phase 6: Fix remaining mypy errors

- [ ] Task 24: Fix mypy errors in tools/messaging.py
  - File: `src/canvas_mcp/tools/messaging.py`
  - Action: Fix `Returning Any` errors (lines 90, 172, 218, 261, 285, 320) by adding isinstance or cast. Fix `object has no attribute` errors (lines 374, 397, 402, 408, 414) by adding proper type annotations to variables holding API data. Fix `arg-type` on line 447 (str|None passed as int). Fix `object has no attribute "get"` and indexed assignment errors (lines 466, 485, 498, 501, 502) with isinstance narrowing.

- [ ] Task 25: Fix mypy errors in tools/discovery.py
  - File: `src/canvas_mcp/tools/discovery.py`
  - Action: Fix `arg-type` errors at lines 96, 102, 110, 115 where `dict[str, str | None]` is appended to `list[str]`. The list type annotation is wrong -- change to `list[dict[str, str | None]]` or fix the append logic.

- [ ] Task 26: Fix mypy errors in tools/student_tools.py
  - File: `src/canvas_mcp/tools/student_tools.py`
  - Action: Add missing return type annotation at line 18. Fix arg-type at line 117 (get_course_code already fixed in Task 3).

- [ ] Task 27: Fix mypy errors in tools/analytics.py
  - File: `src/canvas_mcp/tools/analytics.py`
  - Action: Add missing return type annotation at line 15. Fix var-annotated at lines 179 and 457. Fix assignment type mismatch at line 467 (int vs int|float). The get_course_code arg-type errors should be fixed by Task 3.

- [ ] Task 28: Fix remaining mypy errors across all files
  - Files: All files still showing mypy errors after Tasks 1-27
  - Action: Run `mypy src/` and fix each remaining error. Most will be `object` type narrowing issues in assignment_analytics.py (carried over from assignments.py split) and rubric_grading.py (carried over from rubrics.py split). Add isinstance checks or cast() as appropriate.
  - Notes: Target is 0 mypy errors. Work file-by-file, running mypy between each to track progress.

**Checkpoint: Run `mypy src/` -- must show 0 errors. Run `ruff check src/` -- must show 0 errors. Run `pytest` -- 269 pass, 26 skip.**

### Phase 7: Final verification

- [ ] Task 29: Run black formatter on all modified files
  - Action: Run `.venv/bin/python -m black src/`
  - Notes: Ensure consistent formatting after all manual edits.

- [ ] Task 30: Final triple-check
  - Action: Run all three checks in sequence:
    1. `.venv/bin/python -m ruff check src/` -- 0 errors
    2. `.venv/bin/python -m mypy src/` -- 0 errors
    3. `.venv/bin/python -m pytest tests/ -q` -- 269 passed, 26 skipped
  - Notes: If any failures, fix and re-run all three until clean.

### Acceptance Criteria

- [ ] AC 1: Given the source code, when running `ruff check src/`, then 0 violations are reported and no deprecation warnings appear for ruff config format.
- [ ] AC 2: Given the source code, when running `mypy src/`, then 0 errors are reported across all 39 source files.
- [ ] AC 3: Given the source code, when running `pytest tests/ -q`, then 269 tests pass and 26 are skipped (same as baseline).
- [ ] AC 4: Given the tools/ directory, when listing Python files, then `other_tools.py` does not exist and its 12 tools are found in `pages.py`, `modules.py`, `enrollment.py`, and `analytics.py`.
- [ ] AC 5: Given `assignments.py`, when counting lines, then it is under 1,100 lines and `assignment_analytics.py` exists containing the extracted submission/analytics tools.
- [ ] AC 6: Given `rubrics.py`, when counting lines, then it is under 1,000 lines and `rubric_grading.py` exists containing the extracted grading tools.
- [ ] AC 7: Given the source code, when grepping for `print(` in `src/`, then only 16 intentional CLI prints remain in `server.py` (14 config display lines 154-189, 2 test result lines 194+197). All other output uses `log_error`, `log_warning`, `log_info`, or `log_debug`.
- [ ] AC 8: Given any MCP client connected to the server, when listing available tools, then all tool names are identical to the pre-refactor state -- no tools were renamed, removed, or have changed signatures.

## Additional Context

### Dependencies

- Add `types-python-dateutil>=2.8.0` to `[project.optional-dependencies] dev` in pyproject.toml
- Run `uv pip install -e ".[dev]"` to install
- No other new dependencies required

### Testing Strategy

- All 269 existing tests must pass after every phase checkpoint
- Run mypy and ruff after each phase to track progress
- Run full test suite after file splits (Phases 3-5) to catch import breakage
- No new tests required -- existing coverage is sufficient for a cleanup
- Tests that import `register_*_tools` functions by module path will work as long as those functions stay in their original modules. Tests that import helper functions directly (e.g., `build_bulk_grade_form_data` from `rubrics.py`) will break if helpers move to new modules -- use re-exports to preserve backward compatibility (see Task 22)

### Notes

- **Git strategy:** Create a feature branch before starting. Commit after each phase checkpoint passes. This allows rollback to last known-good state if a phase goes wrong.
- **High-risk item:** Phase 3 (other_tools.py decomposition) touches 4 destination files and deletes 1 source file. Each task must move AND remove atomically to avoid double-registration.
- **High-risk item:** Phase 4-5 (assignments/rubrics splits) create new registration functions that must be called unconditionally in server.py (same as existing tool registrations on lines 59-76).
- **Do not stop between Phase 5 and Phase 6.** Phases 3-5 may temporarily increase mypy error count as errors move to new files. Phase 6 addresses all remaining mypy errors.
- **Known limitation:** The `-> Any` return type on `make_canvas_request()` is a deliberate trade-off. A proper fix would require a generic/overloaded return type, which is out of scope.
- **Future consideration:** `docs/CLAUDE.md` lines 98 and 267 still reference Union/Optional syntax, contradicting project-context.md. Out of scope but should be fixed in a docs pass.
