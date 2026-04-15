# Source Tree Analysis

**Project:** canvas-mcp
**Version:** 1.0.6
**Generated:** 2026-04-14 (full rescan, exhaustive)
**Repository type:** Monolith (single part)
**Primary language:** Python 3.12+ · **Secondary:** TypeScript (bulk-operation submodule)

---

## Annotated Directory Tree

```
canvas-mcp/
├── src/canvas_mcp/                # Python package — all application code
│   ├── __init__.py                # Package exports (__version__ = "1.0.6") and `main` re-export
│   ├── server.py                  # ▶ Entry point: FastMCP server bootstrap + CLI (`canvas-mcp-server`)
│   │
│   ├── core/                      # Shared infrastructure (no MCP tools; used by every tool module)
│   │   ├── __init__.py            # Public facade — re-exports from all submodules
│   │   ├── client.py              # HTTP client: `make_canvas_request`, pagination, 429-retry, file upload, progress polling
│   │   ├── config.py              # Env-var config loader (~22 knobs); singleton `Config` via `get_config()`
│   │   ├── cache.py               # Bidirectional course_code ↔ ID cache; `get_course_id()` supports ID/code/SIS formats
│   │   ├── validation.py          # `@validate_params` decorator + type coercion (Union, Optional, JSON→list, CSV→list)
│   │   ├── dates.py               # ISO 8601 parsing, `format_date_smart()` with standard/compact/relative modes
│   │   ├── anonymization.py       # FERPA: hash-based anonymous IDs, PII redaction, type-dispatched anonymizers
│   │   ├── logging.py             # Structured logger "canvas_mcp" → stderr with context kwargs
│   │   ├── response_formatter.py  # Verbosity enum (COMPACT/STANDARD/VERBOSE) + `format_*` helpers for tokens
│   │   ├── types.py               # TypedDicts: CourseInfo, AssignmentInfo, PageInfo, AnnouncementInfo
│   │   ├── peer_reviews.py        # `PeerReviewAnalyzer` class — completion analytics, follow-up lists
│   │   └── peer_review_comments.py# `PeerReviewCommentAnalyzer` — quality scoring, sentiment, flagging
│   │
│   ├── tools/                     # ▶ All MCP tool registrations — 23 modules, 129 tools
│   │   ├── __init__.py            # Exports all `register_*_tools` functions
│   │   ├── accessibility.py       # 4 tools — UFIXIT accessibility reports + WCAG violation parsing
│   │   ├── analytics.py           # 11 tools — cross-course student/assignment analytics + anonymization mapping
│   │   ├── assignment_analytics.py# 9 tools — submission list/content/comments/history + ungraded/resubmitted
│   │   ├── assignments.py         # 8 tools — assignment CRUD + grading periods + peer review assignment
│   │   ├── code_execution.py      # 2 tools (developer-only) — TS sandbox execution + module discovery
│   │   ├── content_migrations.py  # 1 tool — copy course content (selective items)
│   │   ├── courses.py             # 3 tools — list/details/content overview
│   │   ├── discovery.py           # 1 tool (developer-only) — search code_api functions
│   │   ├── discussion_analytics.py# 3 tools — participation summary, auto-grade, export
│   │   ├── discussions.py         # 11 tools — topics + entries + announcements CRUD + replies
│   │   ├── enrollment.py          # 5 tools — create user, enroll, groups, users, submit-for-student
│   │   ├── gradebook.py           # 5 tools — export, assignment groups, late policy
│   │   ├── grading_export.py      # 1 tool ★ NEW (commit a4630f7, 0307c55) — per-assignment bulk submission CSV export
│   │   ├── message_templates.py   # 0 tools — `MessageTemplates` helper class only
│   │   ├── messaging.py           # 8 tools — Canvas conversations (form-data POST /conversations)
│   │   ├── modules.py             # 8 tools — modules + module items CRUD
│   │   ├── pages.py               # 8 tools — wiki pages CRUD + `bulk_update_pages`
│   │   ├── peer_review_comments.py# 5 tools — comments, quality analysis, CSV/JSON export, reports
│   │   ├── peer_reviews.py        # 4 tools — assignments, completion analytics, reports, follow-up
│   │   ├── quizzes.py             # 13 tools — quiz + question CRUD + publish/unpublish + stats + submissions
│   │   ├── rubrics.py             # 8 tools — rubric CRUD + assignment association
│   │   ├── rubric_grading.py      # 3 tools — per-submission rubric grade + bulk grade endpoint fallback
│   │   ├── search_helpers.py      # 3 tools — find_assignment/find_student/find_discussion (name search)
│   │   └── student_tools.py       # 5 tools (student role) — upcoming, grades, TODOs, peer reviews
│   │
│   ├── resources/                 # MCP resources + prompts
│   │   ├── __init__.py            # Re-exports `register_resources_and_prompts`
│   │   └── resources.py           # 3 resources (course-syllabus, assignment-description, code-api-file) + 1 prompt (summarize-course)
│   │
│   └── code_api/                  # ▶ TypeScript submodule — token-efficient bulk ops via code execution
│       ├── index.ts               # Barrel export of all TS functions
│       ├── client.ts              # Canvas HTTP client (retry, pagination, form-encoding); init from env
│       ├── README.md              # Submodule usage docs
│       └── canvas/
│           ├── courses/           # listCourses, getCourseDetails
│           ├── assignments/       # listSubmissions (paginated, include[]=user)
│           ├── communications/    # sendMessage (POST /conversations)
│           ├── discussions/       # listDiscussions, postEntry, bulkGradeDiscussion
│           └── grading/           # bulkGrade, gradeWithRubric (form-encoded rubric_assessment[])
│
├── tests/                         # ▶ Test suite — 23 files, 328 test functions
│   ├── conftest.py                # Shared fixtures: mock_canvas_request, mock_fetch_paginated, mock_course_id_resolver, sample data
│   ├── test_analytics.py          # 11 tests — stats, aggregation, missing-submission detection
│   ├── test_dates.py              # 16 tests — parse/format, relative-time edge cases (negative deltas)
│   ├── test_token_efficiency.py   # 11 tests — compact vs verbose token savings (~4 char/token heuristic)
│   ├── tools/                     # Per-tool-module unit tests (14 files, 216 tests)
│   │   ├── test_assignments.py    # 35 tests
│   │   ├── test_courses.py        # 7 tests
│   │   ├── test_discussion_analytics.py  # 12 tests
│   │   ├── test_discussions.py    # 5 tests
│   │   ├── test_gradebook.py      # 13 tests
│   │   ├── test_grading_export.py # 33 tests (new module has robust coverage)
│   │   ├── test_messaging.py      # 7 tests
│   │   ├── test_modules.py        # 36 tests — reference impl for TDD patterns
│   │   ├── test_pages.py          # 15 tests
│   │   ├── test_peer_reviews.py   # 5 tests
│   │   ├── test_quizzes.py        # 14 tests
│   │   ├── test_rubrics.py        # 17 tests
│   │   ├── test_search_helpers.py # 13 tests
│   │   └── test_student_tools.py  # 5 tests
│   └── security/                  # FERPA + security tests (5 files, 73 tests)
│       ├── test_authentication.py # 13 tests — token exposure prevention
│       ├── test_code_execution.py # 16 tests — sandbox security (most @skip, not fully implemented)
│       ├── test_dependencies.py   # 13 tests — pip-audit CVE scan
│       ├── test_ferpa_compliance.py  # 14 tests — PII anonymization w/ env flag
│       └── test_input_validation.py  # 17 tests — type checks, SQL injection, boundary values
│
├── tools/                         # ⚠ Documentation ONLY (not runtime code — confusingly named)
│   ├── README.md                  # Human-facing full tool reference (~100+ tools documented)
│   └── TOOL_MANIFEST.json         # Machine-readable tool catalog for programmatic use
│
├── examples/                      # Workflow tutorials (human-authored)
│   ├── bulk_grading_example.md
│   ├── common_issues.md
│   ├── educator_quickstart.md
│   ├── real_world_workflows.md
│   └── student_quickstart.md
│
├── docs/                          # ▶ Documentation root (this file lives here)
│   ├── index.md                   # Master AI-retrieval entry point (regenerated)
│   ├── project-overview.md        # Executive summary + tech stack (regenerated)
│   ├── architecture.md            # Full architecture walkthrough (regenerated)
│   ├── source-tree-analysis.md    # This file (regenerated)
│   ├── api-contracts.md           # Every MCP tool catalogued (regenerated)
│   ├── development-guide.md       # Setup, testing, contributing (regenerated)
│   ├── deployment-guide.md        # Docker, PyPI, MCP Registry (regenerated)
│   ├── CLAUDE.md                  # Developer-focused guide (codebase conventions) — preserved
│   ├── EDUCATOR_GUIDE.md          # End-user guide (educator persona) — preserved
│   ├── STUDENT_GUIDE.md           # End-user guide (student persona) — preserved
│   ├── best-practices.md          # Operational guidance — preserved
│   ├── course_documentation_prompt_template.md — preserved
│   ├── project-scan-report.json   # BMAD workflow state file (this scan)
│   ├── .archive/                  # Prior state files (2026-03-12)
│   └── index.html, *.html, styles.css, CNAME  # GitHub Pages site (preserved)
│
├── config/
│   └── overlays/                  # Layered env config
│       ├── baseline.env           # Safe defaults
│       ├── enterprise.env         # Enterprise deployment
│       ├── public.env             # Public-instance defaults
│       └── README.md
│
├── .github/workflows/             # CI/CD (9 workflows) — all Python 3.12
│   ├── canvas-mcp-testing.yml     # Pytest on push/PR to main + development (path-scoped to discussions.py + tests/)
│   ├── security-testing.yml       # Weekly cron + PR — runs tests/security/ with coverage
│   ├── publish-mcp.yml            # On tag v* — PyPI publish + MCP Registry push
│   ├── auto-update-docs.yml       # On PR touching src/canvas_mcp/tools/** or server.py — Claude auto-updates docs
│   ├── auto-claude-review.yml     # Auto-triggers Claude PR review on open
│   ├── claude-code-review.yml     # Claude code review action
│   ├── claude.yml                 # @claude mention handler (issues + PRs)
│   ├── auto-label-issues.yml      # Claude triages + labels new issues
│   └── weekly-maintenance.yml     # Sunday 00:00 UTC cron — maintenance jobs
│
├── archive/                       # Legacy code (git-tracked but outside runtime)
│   └── canvas_server_cached.py    # Previous-generation server impl (reference only)
│
├── Dockerfile                     # python:3.12-slim + uv + non-root mcp user + HEALTHCHECK
├── .dockerignore                  # Excludes dev noise from image
├── pyproject.toml                 # Python package config (hatchling build, fastmcp ≥2.14.0, httpx, pydantic ≥2.12)
├── uv.lock                        # uv dependency lockfile
├── package.json                   # TS submodule: canvas-mcp-code-api@1.0.6 (node-fetch, ts-node, tsx)
├── package-lock.json              # npm lockfile
├── tsconfig.json                  # TS config — rootDir: src/canvas_mcp/code_api, outDir: dist
├── server.json                    # MCP Registry metadata (stdio transport, env var schema)
├── start_canvas_server.sh         # Legacy startup wrapper (prefers .venv; loads .env)
├── env.template                   # .env scaffold with all ~22 env vars documented
├── README.md                      # Primary human entry point (installation, overview)
├── AGENTS.md                      # AI-agent-facing guide (tool tables, constraints, workflows)
├── SECURITY.md                    # Security policy
├── SECURITY_IMPLEMENTATION_GUIDE.md  # Security controls documentation
├── PROJECT_COMPLETION_SUMMARY.md  # Release-level summary
├── COMPREHENSIVE_CRITIQUE.md      # Internal critique/retrospective
├── CNAME                          # GitHub Pages domain
└── LICENSE                        # MIT
```

---

## Critical Directories

| Directory | Purpose | Entry Points |
|-----------|---------|--------------|
| `src/canvas_mcp/` | Python package | `server.py::main()` (CLI: `canvas-mcp-server`) |
| `src/canvas_mcp/core/` | Shared infra: HTTP client, config, cache, validation, formatting, FERPA anonymization | `client.make_canvas_request`, `cache.get_course_id`, `validation.validate_params` |
| `src/canvas_mcp/tools/` | All MCP tool modules (23) — every file exports `register_*_tools(mcp)` | `server.register_all_tools()` calls each in sequence |
| `src/canvas_mcp/resources/` | MCP resources + prompts | `resources.register_resources_and_prompts(mcp)` |
| `src/canvas_mcp/code_api/` | TypeScript bulk-operation submodule — used by `tools/code_execution.py` | `index.ts` (barrel) |
| `tests/` | pytest + pytest-asyncio; heavy AsyncMock use at client boundary | `conftest.py` fixtures |
| `.github/workflows/` | CI/CD pipelines (Python 3.12, uv) | `publish-mcp.yml` releases on `v*` tags |
| `config/overlays/` | Environment preset files | loaded manually via shell |

---

## Key Files to Know

| File | Why it matters |
|------|----------------|
| `src/canvas_mcp/server.py` | Server bootstrap — read first to understand tool registration order + user_type conditional logic |
| `src/canvas_mcp/core/client.py` | Every Canvas API call routes through `make_canvas_request` — rate-limit retry, anonymization decision matrix |
| `src/canvas_mcp/core/config.py` | Single source of truth for env-var behavior (~22 knobs) |
| `src/canvas_mcp/core/validation.py` | `@validate_params` powers ALL MCP tool input coercion (Union/Optional/JSON→list) |
| `src/canvas_mcp/tools/__init__.py` | Aggregates `register_*_tools` exports; add new modules here + in `server.py` |
| `src/canvas_mcp/tools/quizzes.py` | Largest tool module (13 tools) — good pattern reference |
| `src/canvas_mcp/tools/discussions.py` | 11 tools; only module CI directly path-watches |
| `docs/CLAUDE.md` | Developer conventions (TDD enforcement, tool doc source-of-truth hierarchy) |
| `AGENTS.md` | Authoritative tool table for MCP clients — keep in sync when adding tools |
| `tools/TOOL_MANIFEST.json` | Machine-readable tool catalog — kept in sync with AGENTS.md |
| `pyproject.toml` | Python 3.12+ requirement, FastMCP ≥2.14.0, Pydantic v2.12+, ruff + black + mypy configured |

---

## Tool Registration Order (from `server.py`)

Always registered (20 modules):
`course → assignment → assignment_analytics → discussion → discussion_analytics → enrollment → module → page → rubric → rubric_grading → peer_review → peer_review_comment → messaging → accessibility → analytics → search_helper → quiz → gradebook → grading_export → content_migration`

Conditionally registered:
- If `CANVAS_MCP_USER_TYPE` ∈ {`"all"`, `"student"`} → `student_tools` (5 tools)
- If `CANVAS_MCP_USER_TYPE == "all"` → `discovery`, `code_execution` (3 tools combined)

Final: `register_resources_and_prompts()` → 3 resources + 1 prompt.

---

## Tool Count Summary

| Module | Tools | Module | Tools |
|--------|-------|--------|-------|
| accessibility | 4 | messaging | 8 |
| analytics | 11 | modules | 8 |
| assignment_analytics | 9 | pages | 8 |
| assignments | 8 | peer_review_comments | 5 |
| code_execution | 2 | peer_reviews | 4 |
| content_migrations | 1 | quizzes | 13 |
| courses | 3 | rubrics | 8 |
| discovery | 1 | rubric_grading | 3 |
| discussion_analytics | 3 | search_helpers | 3 |
| discussions | 11 | student_tools | 5 |
| enrollment | 5 | **Total** | **129 MCP tools** |
| gradebook | 5 | Resources | **3** |
| grading_export | 1 | Prompts | **1** |

---

## Excluded From Scan (not source code)

`.venv/`, `.git/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.qlty/`, `dist/`, `build/`, `coverage/`, `_bmad/`, `_bmad-output/`, `.agent*/`, `.cursor/`, `.gemini/`, `venv-textual-paint/`, `articles/`, `local_maps/`, `akeyless` binary, `.DS_Store`.
