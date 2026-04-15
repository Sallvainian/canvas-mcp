# Architecture

**Project:** canvas-mcp · **Version:** 1.0.6
**Generated:** 2026-04-14 (full rescan, exhaustive)

---

## 1. Executive Summary

Canvas MCP is a **Model Context Protocol (MCP) server** that exposes the Canvas LMS REST API to AI clients (Claude Desktop, Cursor, Zed, etc.) as typed, role-gated tools. It is a **Python 3.12+ monolith** built on the **FastMCP** framework, with a tightly-coupled **TypeScript sub-module** for token-efficient bulk operations.

The server emphasizes four operating concerns:

1. **Role-gated surface area** — `CANVAS_MCP_USER_TYPE` (`all` / `educator` / `student`) controls which of the 129 MCP tools the process registers.
2. **FERPA-compliant privacy** — Student PII can be anonymized via a global hash-based ID scheme at the HTTP response boundary.
3. **Token economy** — All responses pass through a verbosity-aware formatter (`COMPACT` / `STANDARD` / `VERBOSE`) with pipe-delimited compact output and abbreviated field labels. Bulk operations execute in a TypeScript sandbox so large datasets never enter the LLM context.
4. **Type-coerced inputs** — Every MCP tool wraps through a single `@validate_params` decorator that handles `Union`, `Optional`, JSON-string → list, and comma-separated strings.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Client                                  │
│            (Claude Desktop, Cursor, Zed, etc.)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │ stdio transport (JSON-RPC)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│           FastMCP Server — server.py                             │
│   create_server() → register_all_tools() → register_resources()  │
└──────┬─────────────────────────────────────────┬─────────────────┘
       │                                         │
       ▼                                         ▼
┌──────────────────────┐              ┌─────────────────────────┐
│ Tool Layer (23 files)│              │ Resources + Prompts     │
│  tools/*.py          │              │  resources/resources.py │
│  129 @mcp.tool defs  │              │  3 resources            │
│  + register_* funcs  │              │  1 prompt               │
│                      │              │  (course-syllabus,      │
│  Conditional by      │              │   assignment-descr,     │
│  user_type:          │              │   code-api-file,        │
│   • all (129)        │              │   summarize-course)     │
│   • educator (121)   │              └─────────────────────────┘
│   • student (126)    │
└─────┬────────────────┘
      │ all tools use:
      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Core Utilities — core/*.py                          │
│                                                                   │
│  client.py      → make_canvas_request() is the SINGLE choke point │
│  config.py      → Config singleton, ~22 env vars                  │
│  cache.py       → course_code ↔ ID cache (lazy refresh on miss)   │
│  validation.py  → @validate_params decorator (type coercion)      │
│  anonymization.py → FERPA: hash-based anonymous_id + PII redaction│
│  response_formatter.py → Verbosity (COMPACT/STANDARD/VERBOSE)     │
│  dates.py       → ISO 8601 + smart (standard/compact/relative)    │
│  logging.py     → Structured logger → stderr (name="canvas_mcp")  │
│  peer_reviews.py / peer_review_comments.py → analytics classes    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ httpx.AsyncClient (global, lazy)
                           ▼
                 ┌─────────────────────┐
                 │   Canvas LMS API    │
                 │  CANVAS_API_URL     │
                 │  Bearer token auth  │
                 └─────────────────────┘

           ┌─────────────────────────────────────────────┐
           │   TypeScript submodule (code_api/)          │
           │  Invoked via tools/code_execution.py        │
           │  Sandbox modes: auto | local | container    │
           │                                              │
           │  index.ts  → barrel export                   │
           │  client.ts → Canvas HTTP, retry, pagination  │
           │  canvas/courses/      listCourses            │
           │  canvas/assignments/  listSubmissions        │
           │  canvas/communications/ sendMessage          │
           │  canvas/discussions/  bulkGradeDiscussion    │
           │  canvas/grading/      bulkGrade, rubric      │
           └─────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Python runtime (primary)
| Category | Tech | Version | Why |
|----------|------|---------|-----|
| Language | Python | ≥3.12 | Modern type hints, PEP 604 unions |
| MCP framework | FastMCP | ≥2.14.0 | Canvas MCP's only framework dependency |
| HTTP client | httpx | ≥0.28.1 | Async, connection pooling, Link header support |
| Fallback HTTP | requests | ≥2.32.0 | Used in start-up checks / scripts |
| Validation | Pydantic | ≥2.12.0 | Declarative type schemas |
| Config | python-dotenv | ≥1.0.0 | `.env` loading at package import |
| Date handling | python-dateutil | ≥2.8.0 | Flexible human-friendly parsing |
| Markdown → HTML | markdown | ≥3.7.0 | Assignment description conversion |
| Build | hatchling | — | `pyproject.toml` → wheel |
| Package manager | uv | — | Recommended for install/lock |

### Python dev tooling
| Tool | Version | Purpose |
|------|---------|---------|
| pytest | ≥7.0.0 | Test runner |
| pytest-asyncio | ≥0.21.0 | Async test support |
| black | 26.3.1 | Formatter (line-length 88) |
| ruff | ≥0.1.0 | Lint (E, W, F, I, B, C4, UP rulesets) |
| mypy | ≥1.5.0 | Strict type-check (`disallow_untyped_defs`, etc.) |

### TypeScript submodule (secondary)
| Category | Tech | Version |
|----------|------|---------|
| Runtime | Node.js | ≥20 (image `node:20-alpine`) |
| Language | TypeScript | ^5.3.3 |
| HTTP | node-fetch | ^3.3.2 |
| Exec | tsx, ts-node | ^4.20.6 / ^10.9.2 |
| Target | ES2022 (ESM) | — |

### Architecture pattern
**Layered + registrar pattern** with a **single HTTP choke point**.

- Presentation: MCP tools (`@mcp.tool()` decorated async functions)
- Service: Core utility modules (`cache`, `client`, `anonymization`, `response_formatter`)
- Integration: `core/client.py::make_canvas_request` is the only path to Canvas
- Cross-cutting: `@validate_params` decorator + `get_config()` singleton + stderr logger

---

## 4. Component Details

### 4.1 Server bootstrap (`server.py`)

`main()` is the CLI entry point registered in `pyproject.toml` as the `canvas-mcp-server` script. Flow:

1. `argparse` handles `--test` (connectivity check) and `--config` (print config, exit)
2. `validate_config()` warns on missing URL suffix, invalid `TS_SANDBOX_MODE`, unimplemented knobs
3. `create_server()` → `FastMCP(config.mcp_server_name)`
4. `register_all_tools(mcp)` registers modules in a fixed order (see Section 6)
5. `register_resources_and_prompts(mcp)` registers 3 resources + 1 prompt
6. `mcp.run()` starts stdio transport; `finally` block calls `cleanup_http_client()`

### 4.2 HTTP client (`core/client.py`)

Single async function `make_canvas_request(method, endpoint, params, data, use_form_data, skip_anonymization)`:

- **Lazy global `httpx.AsyncClient`** (never re-created except via `cleanup_http_client()`)
- **429 retry with exponential backoff**: `MAX_RETRIES=3`, `INITIAL_BACKOFF_SECONDS=2`, honors `Retry-After`
- **Form-encoding path** via `use_form_data=True` + `urlencode()` for duplicate-key arrays (Canvas requires `module[prerequisite_module_ids][]=X` syntax)
- **Anonymization boundary**: decides based on endpoint:
  - Always redacted: `/users`, `/submissions`, `/enrollments`, etc.
  - Always pass-through: `/courses`, `/accounts`, `/terms` (without `/users`)
  - Controlled globally by `ENABLE_DATA_ANONYMIZATION`
- **Progress polling**: `poll_canvas_progress(url)` with 1.5× interval growth, capped at 5s, max 120s total
- **Pagination**: `fetch_all_paginated_results(endpoint, params)` follows RFC 5988 Link headers, aggregates, **then applies anonymization once** (not per page)
- **File upload**: `upload_file_multipart` handles the 3-step S3 redirect flow (Canvas → presigned URL → confirmation)

### 4.3 Validation decorator (`core/validation.py`)

`@validate_params` is applied to every MCP tool. It reads the function's type hints via `inspect.signature()` and runs `validate_parameter()` on each bound argument:

- **Union types**: tries each type in declaration order, collects errors if all fail
- **Optional[T]**: allows `None` or coerces to T
- **bool**: accepts bool / case-insensitive string / int / float
- **list**: accepts list / JSON array string / comma-separated string
- **dict**: accepts dict / JSON object string
- **Failure**: returns `{"error": "...", "details": "..."}` JSON dict (does not raise)

### 4.4 Cache (`core/cache.py`)

Two module-global dicts:
- `course_code_to_id_cache: dict[str, str]` — e.g., `{"CS101": "12345"}`
- `id_to_course_code_cache: dict[str, str]` — e.g., `{"12345": "CS101"}`

`get_course_id(course_identifier)` accepts ID / code / `sis_course_id:...`; on cache miss it calls `refresh_course_cache()` which paginates `/courses` and populates both directions.

### 4.5 Anonymization (`core/anonymization.py`)

Hash-based consistent ID mapping:
- `generate_anonymous_id(real_id, prefix="Student")` → `f"{prefix}_{sha256(real_id)[:8]}"` cached in `_anonymization_cache`
- Type-dispatched: `anonymize_response_data(data, data_type="general")` routes to `anonymize_user_data` / `anonymize_discussion_entry` / `anonymize_submission_data` / `anonymize_assignment_data`
- Regex PII redaction: email, phone, SSN inside free-text fields
- **Real user IDs preserved** for functionality (needed for messaging); only names, emails, SIS IDs are redacted

### 4.6 Response formatter (`core/response_formatter.py`)

Global verbosity (`CANVAS_MCP_VERBOSITY`, default `"compact"`):
- **COMPACT** — `"id|name|due|pts"` pipe-delimited, `Y`/`N` booleans, abbreviated labels (`Due`, `Pts`, `Sub`). Aimed at ~40–85% token reduction (verified by `tests/test_token_efficiency.py`)
- **STANDARD** — `"Name: value, Due: ..."` single-line per item
- **VERBOSE** — full labels with colons, multi-line, lists expanded

### 4.7 Core analyzer classes

`PeerReviewAnalyzer` (`core/peer_reviews.py`) and `PeerReviewCommentAnalyzer` (`core/peer_review_comments.py`) are stateful class wrappers around peer-review endpoints + comment-quality heuristics (word count, constructive/specific/generic/harsh keyword banks, statistics aggregation). Used by `tools/peer_reviews.py` and `tools/peer_review_comments.py`.

---

## 5. Data Architecture

### 5.1 In-memory state

| Name | Location | Purpose | Lifetime |
|------|----------|---------|----------|
| `_config` | `core/config.py` | Config singleton | Process |
| `http_client` | `core/client.py` | `httpx.AsyncClient` | Process; closed at exit via `cleanup_http_client()` |
| `course_code_to_id_cache` | `core/cache.py` | Course resolution | Process; lazy refresh on miss |
| `id_to_course_code_cache` | `core/cache.py` | Reverse lookup | Process |
| `_anonymization_cache` | `core/anonymization.py` | Hash map for consistent IDs | Process; `clear_anonymization_cache()` available |
| `_verbosity` | `core/response_formatter.py` | Cached verbosity | First access |

**No database.** All persistent data lives in Canvas.

### 5.2 Canvas object shapes

`core/types.py` defines four TypedDicts (all `total=False`):
- `CourseInfo` — id, name, course_code, start_at, end_at, time_zone, default_view, is_public, blueprint
- `AssignmentInfo` — id, name, due_at, points_possible, submission_types, published, locked_for_user
- `PageInfo` — page_id, url, title, published, front_page, locked_for_user, last_edited_by, editing_roles
- `AnnouncementInfo` — id, title, message, posted_at, delayed_post_at, lock_at, published, is_announcement

Most tool responses return raw JSON-serialized strings, not typed objects.

---

## 6. Tool Layer

### 6.1 Registration order (`server.py::register_all_tools`)

Always registered (20 modules, 121 tools):
```
course → assignment → assignment_analytics → discussion → discussion_analytics
  → enrollment → module → page → rubric → rubric_grading → peer_review
  → peer_review_comment → messaging → accessibility → analytics
  → search_helper → quiz → gradebook → grading_export → content_migration
```

Conditionally:
- If `user_type ∈ {"all", "student"}` → `student_tools` (+5 tools)
- If `user_type == "all"` → `discovery`, `code_execution` (+3 tools)

Then `register_resources_and_prompts()` (+3 resources, +1 prompt).

### 6.2 Tool module catalogue

See [api-contracts.md](./api-contracts.md) for the complete signature-by-signature reference. Summary:

| Module | Tools | Primary Canvas endpoints |
|--------|-------|--------------------------|
| `accessibility.py` | 4 | `/courses/{id}/ufixit_summary` + content scan |
| `analytics.py` | 11 | `/courses/{id}/analytics/*`, `/reports/*` |
| `assignment_analytics.py` | 9 | `/assignments/{id}/submissions`, `/submission_history` |
| `assignments.py` | 8 | `/courses/{id}/assignments`, `/grading_periods`, `/peer_reviews` |
| `code_execution.py` | 2 | No Canvas calls — invokes TS submodule |
| `content_migrations.py` | 1 | `/courses/{id}/content_migrations` |
| `courses.py` | 3 | `/courses`, `/accounts/{id}/courses` |
| `discovery.py` | 1 | TS submodule introspection |
| `discussion_analytics.py` | 3 | `/discussion_topics/{id}/entries` |
| `discussions.py` | 11 | `/discussion_topics`, `/entries`, `/replies`, `/announcements` |
| `enrollment.py` | 5 | `/accounts/{id}/users`, `/enrollments`, `/groups` |
| `gradebook.py` | 5 | `/assignment_groups`, `/students/submissions` |
| `grading_export.py` | 1 | `/courses/{id}/assignments/{id}/submissions` (new per-assignment path; see commit `0307c55`) |
| `messaging.py` | 8 | `POST /conversations` (form-encoded) |
| `modules.py` | 8 | `/courses/{id}/modules`, `/modules/{id}/items` |
| `pages.py` | 8 | `/courses/{id}/pages`, `/front_page` |
| `peer_review_comments.py` | 5 | `/peer_reviews` + submission comments |
| `peer_reviews.py` | 4 | `/peer_reviews` (wraps `PeerReviewAnalyzer`) |
| `quizzes.py` | 13 | `/quizzes`, `/questions`, `/statistics`, `/submissions` |
| `rubrics.py` | 8 | `/rubrics`, `/rubric_associations` |
| `rubric_grading.py` | 3 | `/submissions/update_grades` (bulk) + rubric PUT fallback |
| `search_helpers.py` | 3 | `/assignments`, `/users`, `/discussion_topics` (search+filter) |
| `student_tools.py` | 5 | `/users/self/*` endpoints only |

### 6.3 Tool author conventions

From `docs/CLAUDE.md`:
1. Every tool uses `@mcp.tool()` + `@validate_params`, declared async
2. Course IDs accept `Union[str, int]` and resolve via `get_course_id()`
3. Dates output via `format_date()` / `format_date_smart(mode=...)`
4. Errors return JSON strings containing an `"error"` key (never raise)
5. Canvas POST/PUT endpoints that require form data set `use_form_data=True`
6. Privacy: real user IDs preserved; names anonymized via `anonymize_response_data()` decision matrix
7. Optional parameters use `Optional[T]` (PEP 604 `T | None` equivalent)
8. TDD enforced: ≥3 tests per new tool (success path, error path, edge case) — see `tests/tools/test_modules.py` as reference pattern

---

## 7. TypeScript Submodule (`code_api/`)

Purpose: run bulk operations locally in a sandbox to keep large datasets out of the LLM context.

- **Entry:** `index.ts` barrel-re-exports every domain function
- **Client:** `client.ts` provides `canvasGet/Post/Put/Delete/PutForm`, `fetchAllPaginated<T>`, 30-second timeout, retry (3× at 1/2/4s backoff), error surface with status + body
- **Domain folders** under `canvas/`:
  - `courses/` — `listCourses()`, `getCourseDetails(input)`
  - `assignments/` — `listSubmissions(input)` (paginated)
  - `communications/` — `sendMessage(input)`
  - `discussions/` — `listDiscussions`, `postEntry`, `bulkGradeDiscussion` (local participation analysis with O(1) parent lookup, concurrent batched PUTs)
  - `grading/` — `bulkGrade` (accepts a `(Submission) => GradeResult | null` callback, concurrent-limited execution, dry-run mode), `gradeWithRubric` (form-encoded `rubric_assessment[{criterion_id}][points]` etc.)

**Invocation from Python:** `tools/code_execution.py::execute_typescript` runs user-supplied TS code inside Node.js (`local` mode) or a container (`container` mode; `node:20-alpine` by default). Network is restricted via an injected allowlist guard; memory/CPU/timeout enforceable via container runtime.

**Token-efficiency example** (from submodule README): bulk-grading 90 submissions traditional-path = ~1.35M tokens; via `bulkGrade` = ~3.5K tokens (≈99.7% reduction).

---

## 8. Configuration

### 8.1 Environment variables

Loaded via `python-dotenv` at `core/config.py` import.

**Required:**
- `CANVAS_API_TOKEN` — Canvas personal access token (Account → Settings → New Access Token)
- `CANVAS_API_URL` — Full API URL including `/api/v1` suffix (e.g., `https://canvas.example.edu/api/v1`)

**Core:**
- `MCP_SERVER_NAME` (default `"canvas-api"`) — Transport identifier
- `DEBUG` (default `false`), `LOG_LEVEL` (default `"INFO"`), `LOG_API_REQUESTS` (default `false`)
- `API_TIMEOUT` (default `30`), `CACHE_TTL` (default `300`), `MAX_CONCURRENT_REQUESTS` (default `10`)

**Privacy:**
- `ENABLE_DATA_ANONYMIZATION` (default `true` when set via env.template; default in code is also `true`)
- `ANONYMIZATION_DEBUG` (default `false`)

**Response shaping:**
- `CANVAS_MCP_VERBOSITY` (`compact` | `standard` | `verbose`; default `compact`)
- `CANVAS_MCP_USER_TYPE` (`all` | `educator` | `student`; default `all`)

**TS sandbox:**
- `ENABLE_TS_SANDBOX` (default `false`)
- `TS_SANDBOX_MODE` (`auto` | `local` | `container`; default `auto`)
- `TS_SANDBOX_BLOCK_OUTBOUND_NETWORK`, `TS_SANDBOX_ALLOWLIST_HOSTS`
- `TS_SANDBOX_CPU_LIMIT`, `TS_SANDBOX_MEMORY_LIMIT_MB`, `TS_SANDBOX_TIMEOUT_SEC` (all `0` = unlimited/best-effort locally)
- `TS_SANDBOX_CONTAINER_IMAGE` (default `node:20-alpine`)

**Metadata:**
- `INSTITUTION_NAME`, `TIMEZONE` (default `"UTC"`)

### 8.2 Config overlays

`config/overlays/{baseline,enterprise,public}.env` provide layered presets. Loaded manually via shell (`source config/overlays/enterprise.env`).

---

## 9. Testing Strategy

- **Runner:** pytest + pytest-asyncio
- **Fixture hub:** `tests/conftest.py` — mocks `canvas_mcp.core.client.make_canvas_request`, `fetch_all_paginated_results`, and `cache.get_course_id/get_course_code` with AsyncMock. Also provides sample Canvas JSON payloads for courses, assignments, submissions, pages, rubrics, discussions, announcements.
- **Pattern:** mock the HTTP boundary; assert tool output shape and that the right endpoint/params were called.
- **Reference implementation:** `tests/tools/test_modules.py` (36 tests) and `tests/tools/test_grading_export.py` (33 tests)
- **Cross-cutting:**
  - `test_token_efficiency.py` (11 tests) verifies compact/standard/verbose token-savings heuristic (~4 chars/token)
  - `test_dates.py` (16 tests) covers relative-time edge cases including a specific timedelta-negative-delta bug
  - `test_analytics.py` (11 tests) for statistics
- **Security suite** (`tests/security/`, 73 tests):
  - `test_authentication.py` — token exposure in logs/errors
  - `test_input_validation.py` — type checks, SQL injection, boundary values
  - `test_ferpa_compliance.py` — PII anonymization w/ env flag
  - `test_code_execution.py` — sandbox isolation (most `@skip` — sandbox security is not fully implemented)
  - `test_dependencies.py` — `pip-audit` CVE scan

### Coverage gaps

Tool modules **without** a matching `tests/tools/test_*.py` file:
`accessibility`, `analytics`, `assignment_analytics`, `code_execution`, `content_migrations`, `discovery`, `enrollment`, `message_templates`, `peer_review_comments`, `rubric_grading`.

Notable: `rubric_grading.py` (rubric-driven grading) and `code_execution.py` (TS sandbox entry) are both shipped features without dedicated test files. See GitHub issue #56 for the comprehensive coverage plan.

---

## 10. Deployment Architecture

### 10.1 Runtime modes

| Mode | Invocation | Target |
|------|------------|--------|
| CLI (console script) | `canvas-mcp-server` | Developers / local MCP clients |
| Docker | `docker run -e CANVAS_API_TOKEN=... -e CANVAS_API_URL=... canvas-mcp` | Containerized deploy |
| Legacy shell | `./start_canvas_server.sh` | Loads `.env` + prefers `.venv/bin/canvas-mcp-server` |

### 10.2 Docker image

`Dockerfile` (Python 3.12-slim):
1. `RUN pip install uv`
2. Copies `pyproject.toml`, `LICENSE`, `README.md`, `env.template`, `src/`
3. `uv pip install --system --no-cache -e .`
4. Creates non-root user `mcp` (uid/gid default), `chown -R mcp:mcp /app`
5. Env defaults: `MCP_SERVER_NAME=canvas-mcp`, `ENABLE_DATA_ANONYMIZATION=false`, `ANONYMIZATION_DEBUG=false`
6. `USER mcp`
7. `HEALTHCHECK` runs `python -c "import canvas_mcp; print('OK')"` (interval 30s, 3 retries)
8. `CMD ["canvas-mcp-server"]`

### 10.3 Distribution channels

- **PyPI** — `canvas-mcp` package (published via `.github/workflows/publish-mcp.yml` on `v*` tags using `pypa/gh-action-pypi-publish`)
- **MCP Registry** — server metadata at `server.json`; same workflow publishes to `https://static.modelcontextprotocol.io` with stdio transport entry
- **GitHub Pages** — `docs/*.html` deployed at the `CNAME` domain

---

## 11. CI/CD Pipelines (`.github/workflows/`)

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `canvas-mcp-testing.yml` | `push`/PR to `main`,`development`; paths: `src/canvas_mcp/tools/discussions.py`, `tests/**` | Pytest smoke-runner on narrow scope |
| `security-testing.yml` | push, PR, weekly Sunday cron | `pytest tests/security/ --cov=src/canvas_mcp` |
| `publish-mcp.yml` | tag `v*` | PyPI publish → MCP Registry push |
| `auto-update-docs.yml` | PR changing `src/canvas_mcp/tools/**` or `server.py` | Claude Action auto-updates docs |
| `auto-claude-review.yml` | PR `opened` | Posts `@claude` review trigger comment |
| `claude-code-review.yml` | PR events | Claude code review |
| `claude.yml` | `@claude` mention in issue/PR comment | Claude Code action handler |
| `auto-label-issues.yml` | `issues.opened` | Claude-powered triage + labeling |
| `weekly-maintenance.yml` | Sunday 00:00 UTC cron + manual | Maintenance jobs (dependency checks, etc.) |

All Python jobs use **Python 3.12**. Publishing uses `uv` for installs.

---

## 12. Security & Privacy Controls

- **AuthN:** Bearer token via `CANVAS_API_TOKEN`; token validated at startup (`validate_config()`)
- **AuthZ:** Role derived from Canvas token permissions + MCP-side gating via `CANVAS_MCP_USER_TYPE`
- **FERPA:** Hash-based student-ID anonymization at HTTP response boundary (`anonymize_response_data()`); toggleable via `ENABLE_DATA_ANONYMIZATION`
- **Token hygiene:** Logs go to stderr with `log_api_requests` disabled by default; tokens never enter log lines (`tests/security/test_authentication.py` verifies)
- **TS sandbox:** `code_execution.py` supports network-allowlist, container isolation (`node:20-alpine`), CPU/memory/timeout limits; image can be validated by SHA256
- **Input validation:** `@validate_params` rejects wrong types at the tool boundary; `tests/security/test_input_validation.py` covers SQL-injection strings, boundary integers, extreme values
- **Dependency scanning:** weekly `pip-audit` (`test_dependencies.py`)

---

## 13. Known Limitations & Risks

- **Sandbox isolation is partial** — many `tests/security/test_code_execution.py` cases are `@pytest.mark.skip`. Running untrusted TypeScript in `local` mode offers limited isolation; prefer `container` mode for untrusted code.
- **`grading_export.py` has hardcoded course mapping** for a specific Science 8 course (period P1–P9 → Canvas course IDs). Reuse requires code changes.
- **10 tool modules lack unit tests** (see §9). Tracked in issue #56.
- **Cache has no TTL** in code — `CACHE_TTL` env var exists but `cache.py` uses lazy-on-miss; a long-running server might hold a stale code→ID map if a course is renamed.
- **Global state** — `http_client`, `_config`, `_anonymization_cache`, caches — is safe within a stdio transport's single-process model; would need rework for multi-client HTTP transport.
