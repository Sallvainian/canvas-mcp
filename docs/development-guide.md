# Development Guide

**Project:** canvas-mcp · **Version:** 1.0.6
**Generated:** 2026-04-14 (full rescan, exhaustive)

---

## Prerequisites

- **Python 3.12+** (required — `pyproject.toml` sets `requires-python = ">=3.12"`)
- **[uv](https://github.com/astral-sh/uv)** package manager (recommended; falls back to `pip`)
- **Node.js ≥20** (only if you need to work on the TypeScript `code_api/` submodule)
- A **Canvas API token** with permissions for the tools you plan to test (Account → Settings → New Access Token)

---

## First-time Setup

```bash
# 1. Clone
git clone https://github.com/vishalsachdev/canvas-mcp.git
cd canvas-mcp

# 2. Install uv (if not already installed)
pip install uv

# 3. Create venv + install the package in editable mode
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"   # includes pytest, black, ruff, mypy

# 4. Create .env from template
cp env.template .env
# …then edit .env with your CANVAS_API_TOKEN and CANVAS_API_URL (with /api/v1 suffix)
```

After install, the CLI entry point `canvas-mcp-server` is on your PATH (inside the venv).

### TypeScript submodule (optional)

```bash
npm install
npm run build   # tsc → dist/
```

---

## Running the Server

```bash
# Normal start (reads .env automatically via python-dotenv)
canvas-mcp-server

# Connectivity test (calls GET /users/self and prints the result)
canvas-mcp-server --test

# Print effective config (tokens redacted) and exit
canvas-mcp-server --config

# Legacy shell wrapper (loads .env explicitly; prefers .venv/bin/canvas-mcp-server)
./start_canvas_server.sh
```

Point your MCP client (e.g., Claude Desktop at `~/Library/Application Support/Claude/claude_desktop_config.json`) at this binary with `transport: stdio`.

---

## Configuration (`.env`)

Full schema in [`env.template`](../env.template). Highlights:

| Variable | Default | Notes |
|----------|---------|-------|
| `CANVAS_API_TOKEN` | — | **Required** |
| `CANVAS_API_URL` | — | **Required**; must include `/api/v1` |
| `CANVAS_MCP_USER_TYPE` | `all` | `all` / `educator` / `student` — gates tool registration |
| `CANVAS_MCP_VERBOSITY` | `compact` | `compact` / `standard` / `verbose` |
| `ENABLE_DATA_ANONYMIZATION` | `true` (env.template) | FERPA toggle |
| `ENABLE_TS_SANDBOX` | `false` | Enables `execute_typescript` tool |
| `TS_SANDBOX_MODE` | `auto` | `auto` / `local` / `container` |
| `DEBUG`, `LOG_LEVEL`, `LOG_API_REQUESTS` | `false`/`INFO`/`false` | Standard logging knobs |
| `API_TIMEOUT` | `30` | HTTP client timeout (s) |

`config/overlays/{baseline,public,enterprise}.env` provide preset combinations. Load manually via `source config/overlays/enterprise.env`.

---

## Development Commands

```bash
# Run tests
pytest                              # everything
pytest tests/tools/test_modules.py  # one file
pytest -k test_create_module        # by name match
pytest tests/security/              # security suite
pytest --cov=src/canvas_mcp         # with coverage

# Lint + format
ruff check .
black .

# Type-check (strict — configured in pyproject.toml)
mypy src/canvas_mcp

# Quick syntax sanity check
python -c "import canvas_mcp; print('OK')"
```

---

## Code Style & Conventions

Enforced by `pyproject.toml`:
- **black** line-length 88, target `py312`
- **ruff** rulesets: `E`, `W`, `F`, `I`, `B`, `C4`, `UP` — with `E501` ignored (black handles)
- **mypy** strict: `disallow_untyped_defs`, `disallow_incomplete_defs`, `check_untyped_defs`, `disallow_untyped_decorators`, `no_implicit_optional`, `warn_redundant_casts`, `warn_unused_ignores`, `warn_no_return`

Project conventions (see [CLAUDE.md](./CLAUDE.md) for the authoritative list):
- Type hints on every function; `Union`/`Optional` (or PEP 604 `T | None`) where applicable
- MCP tools: `@mcp.tool()` + `@validate_params` + `async def`
- Course ID params: `Union[str, int]`, resolved via `get_course_id()`
- Dates: output via `format_date()` / `format_date_smart()`
- Errors: return JSON string with `"error"` key; **never raise**
- Canvas form data: `use_form_data=True`
- Logging: use `log_info/log_error/log_warning/log_debug` — **not `print`**
- Privacy: real user IDs preserved; names redacted via `anonymize_response_data()`

---

## Test-Driven Development (Enforced)

**Every new MCP tool must land with ≥3 tests before merge:**

1. Success path (happy case + Canvas response shape)
2. Error path (API error 404/401/500 handling)
3. Edge case (empty list, None, invalid type, special characters)

### Test file layout

```
tests/
├── conftest.py             # Shared fixtures (mock_canvas_request, mock_fetch_paginated, sample data)
├── test_analytics.py       # Cross-cutting
├── test_dates.py           # Cross-cutting
├── test_token_efficiency.py# Cross-cutting
├── tools/                  # Per-tool-module tests
│   ├── test_modules.py     # ← Reference implementation (36 tests)
│   ├── test_grading_export.py # Most recent addition (33 tests)
│   └── …
└── security/               # FERPA + security (73 tests)
```

### Reference test pattern (from `test_modules.py`)

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.fixture
def mock_canvas_request():
    with patch("canvas_mcp.tools.modules.make_canvas_request") as mock:
        yield mock

@pytest.mark.asyncio
async def test_create_module_success(mock_canvas_request, mock_course_id_resolver):
    mock_canvas_request.return_value = {"id": 123, "name": "Week 1"}
    # tool is an inner closure registered on `mcp`; get via the registration fn
    ...
```

`tests/conftest.py` centralizes:
- `mock_canvas_request`, `mock_fetch_paginated`
- `mock_course_id_resolver`, `mock_course_code_resolver`
- Sample data fixtures: `sample_course_data`, `sample_assignment_data`, `sample_submission_data`, `sample_page_data`, `sample_rubric_data`, `sample_discussion_topic_data`, `sample_announcement_data`

### Current coverage

- **14** of 23 tool modules have dedicated test files (216 tool tests)
- **5** security test files (73 tests)
- **3** cross-cutting test files (38 tests)
- **Total: 328 test functions across 23 files**

**Gaps — tool modules without tests:** `accessibility`, `analytics`, `assignment_analytics`, `code_execution`, `content_migrations`, `discovery`, `enrollment`, `message_templates`, `peer_review_comments`, `rubric_grading`. Tracked in [GitHub issue #56](https://github.com/vishalsachdev/canvas-mcp/issues/56).

---

## Common Development Tasks

### Add a new MCP tool

1. **Choose a module** — pick the best-matching `tools/*.py` file (or create `tools/<area>.py` + add `register_*_tools` to `server.py` and `tools/__init__.py`)
2. **Write the tool** inside the `register_*_tools(mcp)` closure:
   ```python
   @mcp.tool()
   @validate_params
   async def my_new_tool(course_identifier: str | int, …) -> str:
       """One-line purpose (first line becomes the MCP description)."""
       course_id = await get_course_id(course_identifier)
       if not course_id:
           return json.dumps(format_error("Course not found"))
       result = await make_canvas_request("GET", f"/courses/{course_id}/…")
       return json.dumps(result)
   ```
3. **Update docs per [CLAUDE.md](./CLAUDE.md) source-of-truth hierarchy:**
   - `tools/README.md` (full doc for humans)
   - `AGENTS.md` (tool table for AI)
   - `tools/TOOL_MANIFEST.json` (machine-readable)
4. **Write tests** in `tests/tools/test_<module>.py` (≥3 tests)
5. **Run** `pytest tests/tools/test_<module>.py`, `ruff check`, `black`, `mypy src/canvas_mcp`
6. **Commit + PR** — expect `auto-update-docs.yml` to push doc fixes, and `claude-code-review.yml` to post review

### Update `docs/` directly

Do not hand-edit the auto-generated files (`index.md`, `project-overview.md`, `architecture.md`, `source-tree-analysis.md`, `api-contracts.md`, `development-guide.md`, `deployment-guide.md`) — they are rebuilt by this workflow on demand. Human-authored files (`CLAUDE.md`, `EDUCATOR_GUIDE.md`, `STUDENT_GUIDE.md`, `best-practices.md`) are preserved across scans.

### Work on the TypeScript submodule

```bash
npm run build      # tsc
# No dedicated TS tests in-repo — exercised through tools/code_execution.py integration
```

The Python side invokes TS via `execute_typescript` (see `tools/code_execution.py`). To test locally with sandbox:

```bash
# .env
ENABLE_TS_SANDBOX=true
TS_SANDBOX_MODE=local    # Node.js in-process
# or
TS_SANDBOX_MODE=container  # Docker/Podman image (default node:20-alpine)
```

### Regenerate these docs

Run the `/bmad-document-project` skill. It archives the current state file, re-detects the project type, re-scans all source files (choose exhaustive scan level), and rewrites the auto-generated documents. Human-authored docs in `docs/` are left untouched.

---

## CI/CD Integration Points

Workflows in `.github/workflows/` that you may trigger from a PR:

- **`canvas-mcp-testing.yml`** — Runs pytest on push/PR to `main`/`development`, path-scoped to `src/canvas_mcp/tools/discussions.py` + `tests/**`. Note: narrow path scope — most PRs do **not** trigger it.
- **`security-testing.yml`** — Runs `pytest tests/security/ --cov=src/canvas_mcp` on every push/PR + weekly Sunday cron. Uploads coverage HTML artifact.
- **`auto-update-docs.yml`** — Triggered on PR touching `src/canvas_mcp/tools/**` or `server.py`. Uses Claude Code Action to write doc updates.
- **`auto-claude-review.yml`** — Posts `@claude` mention on PR open to trigger review.
- **`claude-code-review.yml`** — Claude PR review action.
- **`claude.yml`** — Claude responder for `@claude` mentions in issues/PR comments.
- **`auto-label-issues.yml`** — Claude triages + labels new issues.
- **`weekly-maintenance.yml`** — Sunday 00:00 UTC cron for maintenance tasks.

Releases: see [deployment-guide.md](./deployment-guide.md#release-process).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ModuleNotFoundError: canvas_mcp` | Not installed in current venv | `uv pip install -e .` |
| `401 Unauthorized` from Canvas | Bad/expired token | Generate new token; update `.env` |
| `404 Not Found` on a course | Token scope doesn't include that course | Confirm in Canvas that the token's user is enrolled in the course |
| Tool returns `{"error": "..."}` | Validation or API error | Inspect stderr log; set `LOG_LEVEL=DEBUG` |
| `429 Too Many Requests` | Canvas rate limit (~700 req/10min) | Client retries 3× with backoff automatically; reduce bulk op concurrency |
| Compact responses hard to read | `CANVAS_MCP_VERBOSITY=compact` default | Set `CANVAS_MCP_VERBOSITY=standard` in `.env` |
| TS sandbox fails | `ENABLE_TS_SANDBOX=false` or no runtime | Set to `true`; ensure Docker/Podman installed for `container` mode |

---

## Additional References

- [CLAUDE.md](./CLAUDE.md) — developer conventions, TDD rules, doc source-of-truth matrix
- [best-practices.md](./best-practices.md) — operational guidance
- [../AGENTS.md](../AGENTS.md) — AI agent tool reference
- [../tools/README.md](../tools/README.md) — human tool reference
- [../examples/](../examples/) — workflow tutorials
