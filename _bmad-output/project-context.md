---
project_name: 'canvas-mcp'
user_name: 'Sallvain'
date: '2026-03-12'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules']
status: 'complete'
rule_count: 52
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

| Technology | Version | Role |
|---|---|---|
| Python | >=3.12 (target py312) | Primary runtime |
| Node.js | 20+ | TypeScript code execution API |
| FastMCP | >=2.14.0 | MCP server framework |
| httpx | >=0.28.1 | Async HTTP client for Canvas API |
| Pydantic | >=2.12.0 | Data validation |
| python-dateutil | >=2.8.0 | Date parsing/formatting |
| markdown | >=3.7.0 | Markdown-to-HTML for Canvas descriptions |
| TypeScript | >=5.3.3 | Code execution sandbox |
| Hatchling | latest | Build backend (pyproject.toml) |
| Ruff | >=0.1.0 | Linting (E/W/F/I/B/C4/UP, 88-char lines) |
| Black | >=23.0.0 | Code formatting (88-char, py312 target) |
| mypy | >=1.5.0 | Strict type checking (mandatory type hints) |
| pytest | >=7.0.0 | Testing with pytest-asyncio (auto mode) |

**Version constraints:**
- Python 3.12 minimum — use PEP 604 union syntax (`X | Y`), builtin generics (`list[]`, `dict[]`)
- mypy strict mode enforced on `src/` (relaxed for `tests/`)
- Ruff and Black both use 88-char line length — do not change
- Docker production image: `python:3.12-slim`

## Critical Implementation Rules

### Python Language Rules

- **Union syntax:** Always use `X | Y` and `X | None`, never `Union[X, Y]` or `Optional[X]`
- **Builtin generics:** Use `list[str]`, `dict[str, Any]`, `tuple[...]` — never import from `typing`
- **Type hints mandatory:** All function signatures must have full type hints including return types (mypy strict)
- **Tests exempt:** `disallow_untyped_defs = false` for `tests/` — type hints optional in test files
- **Async everywhere:** All tool functions and API interactions must be `async def`
- **Error handling — return, don't raise:** Tool functions return `{"error": "..."}` dicts, never raise exceptions
- **Imports from `typing`:** Only use `Any`, `TypedDict` — everything else is builtin
- **String formatting:** f-strings preferred, no `.format()` or `%` formatting
- **Markdown-to-HTML:** Use `description_to_html()` from `tools/assignments.py` — it auto-detects whether input is already HTML or needs markdown conversion
- **ISO 8601 dates:** All dates sent to Canvas API must be ISO 8601 format; use `parse_to_iso8601()` for conversion

### FastMCP & Canvas API Rules

**Tool Registration Pattern:**
- Every tool function lives inside a `register_*_tools(mcp: FastMCP)` function
- Decorator order matters: `@mcp.tool()` FIRST, then `@validate_params` — reversing breaks registration
- New tool modules must be imported in `tools/__init__.py` and called in `server.py:register_all_tools()`
- Conditional registration: student tools only when `user_type in ("all", "student")`

**Canvas API Request Pattern:**
- ALL Canvas API calls go through `make_canvas_request(method, endpoint, ...)` — never use httpx directly
- Form data required for: submissions, modules, conversations, rubric grading — use `use_form_data=True`
- For duplicate-key form data (e.g., `module[prerequisite_module_ids][]`), pass `data` as `list[tuple[str, str]]`
- Pagination: use `fetch_all_paginated_results()` for list endpoints — never manually paginate

**Course Identifier Resolution:**
- All course parameters accept 3 formats: numeric ID (`12345`), course code (`CS101_2024`), SIS ID (`sis_course_id:SIS123`)
- Always resolve via `await get_course_id(course_identifier)` before API calls
- Parameter type: `course_identifier: str | int` (not `course_id`)

**Response Formatting:**
- Always use `format_response()` / `format_header()` for tool output — never return raw JSON
- Three verbosity levels: COMPACT (pipe-delimited), STANDARD (label: value), VERBOSE (full)
- Default is COMPACT for token efficiency (~70% savings)

**Tool Naming:**
- Pattern: `{action}_{entity}[_{specifier}]` in snake_case (e.g., `list_assignments`, `get_quiz_details`)
- Parameters: `course_identifier`, `assignment_id`, `topic_id` — always use full `_id` suffix

### Testing Rules

**TDD Enforced:** All new MCP tools MUST have tests before the feature is considered complete.

**Structure:**
- Tool tests in `tests/tools/test_{module}.py` matching `src/canvas_mcp/tools/{module}.py`
- Security tests in `tests/security/`
- Shared fixtures in `tests/conftest.py` — always check here before creating new fixtures
- Minimum 3 tests per tool: success path, error handling, edge case

**Test Patterns:**
- Framework: pytest with `pytest-asyncio` (auto mode — no manual `@pytest.mark.asyncio` on classes needed)
- Mocking: patch `canvas_mcp.core.client.make_canvas_request` — never mock httpx directly
- Course ID resolution: use `mock_course_id_resolver` fixture from conftest
- Tool extraction: use `get_tool_function(mcp, "tool_name")` to get registered tool functions from FastMCP
- Always use `AsyncMock` for Canvas API mocks, not regular `Mock`

**What NOT to do in tests:**
- Don't call Canvas API directly — always mock `make_canvas_request`
- Don't import tool functions directly — register them on a FastMCP instance and extract
- Don't create fixtures that duplicate conftest (sample_course_data, sample_assignment_data, etc.)

**Running:**
- `pytest` (all tests)
- `pytest tests/tools/` (tool tests only)
- `pytest tests/security/` (security tests only)
- `pytest --cov=src/canvas_mcp --cov-report=html` (with coverage)

### Code Quality & Style Rules

**Linting & Formatting:**
- Ruff rules: E, W, F, I (isort), B (bugbear), C4 (comprehensions), UP (pyupgrade)
- E501 (line too long) ignored — handled by Black at 88 chars
- B008 (function calls in defaults) ignored — needed for FastMCP patterns
- C901 (complexity) ignored
- `__init__.py` files: F401 (unused imports) ignored — re-exports are intentional

**File & Code Organization:**
- Source layout: `src/canvas_mcp/` (src-layout, not flat)
- Tools: one module per Canvas entity in `tools/` (e.g., `assignments.py`, `quizzes.py`)
- Core utilities: `core/` (client, config, cache, validation, dates, types, anonymization, response_formatter)
- Each tool module exports a single `register_*_tools(mcp)` function
- Resources/prompts: `resources/` directory

**Naming Conventions:**
- Files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes: `PascalCase` (TypedDict types in `core/types.py`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `INITIAL_BACKOFF_SECONDS`)
- Test classes: `Test{FeatureName}` (e.g., `TestCreateAssignment`)
- Test functions: `test_{scenario}` (e.g., `test_success`, `test_api_error`)

**Import Order (enforced by Ruff isort):**
- stdlib -> third-party -> local (`from ..core import ...`)
- Relative imports within package (`from ..core.client import make_canvas_request`)

### Development Workflow Rules

**Git & Branching:**
- Feature branches: `feature/{descriptive-name}` (e.g., `feature/module-creation-tool`)
- PR-based workflow — changes merge via pull requests
- Tag-triggered releases publish to PyPI + MCP Registry (via `publish-mcp.yml`)

**CI/CD Pipeline:**
- `canvas-mcp-testing.yml`: Runs pytest on PR/push
- `security-testing.yml`: 6-job pipeline (pytest, Bandit, Semgrep, pip-audit, TruffleHog, CodeQL)
- `claude-code-review.yml`: AI-assisted code review
- `auto-update-docs.yml`: Documentation synchronization
- `weekly-maintenance.yml`: Scheduled dependency checks

**Release Process:**
- Version defined in `src/canvas_mcp/__init__.py` (Hatch reads from there)
- Also update `server.json` version field to match
- Tag-triggered: push a git tag to trigger PyPI publish

**Adding a New Tool (checklist):**
1. Create `src/canvas_mcp/tools/{feature}.py` with `register_{feature}_tools(mcp)` function
2. Import and export from `tools/__init__.py`
3. Call registration in `server.py:register_all_tools()` (respect user_type conditionals)
4. Write tests in `tests/tools/test_{feature}.py` (minimum 3 per tool)
5. Update `AGENTS.md` tool table and `tools/TOOL_MANIFEST.json`
6. Update `tools/README.md` with full documentation

### Critical Don't-Miss Rules

**Canvas API Gotchas:**
- Messaging endpoints (`/conversations`) MUST use `use_form_data=True` — JSON silently fails
- Canvas returns `[]` (empty list) not `404` for endpoints with no results — handle both
- Rate limit: ~700 requests/10 minutes; `make_canvas_request` auto-retries 429s with exponential backoff
- File uploads are 3-step: request slot -> upload to S3 -> confirm with Canvas; use `upload_file_multipart()`
- Canvas async operations (bulk grade, content migration) return Progress objects — use `poll_canvas_progress()`
- `include[]` params must be repeated per value, not comma-separated (httpx handles this with lists)

**Anonymization / FERPA:**
- Anonymization is transparent to the tool layer — applied at HTTP response level in `client.py`
- Never log or expose real student names when `ENABLE_DATA_ANONYMIZATION=true`
- Real user IDs are preserved (needed for API calls); only names/emails are anonymized
- `skip_anonymization=True` exists for internal tools (e.g., building anonymization maps)

**Anti-Patterns to Avoid:**
- NEVER use httpx directly — always go through `make_canvas_request()`
- NEVER raise exceptions in tool functions — return error dicts
- NEVER hardcode course IDs — always accept `course_identifier` and resolve
- NEVER return raw Canvas API JSON — always format through `format_response()`
- NEVER create a new HTTP client — use `_get_http_client()` singleton
- NEVER manually paginate — use `fetch_all_paginated_results()`

**Security:**
- API token lives in `.env`, loaded via python-dotenv — never commit `.env`
- Code execution sandbox (TypeScript) is optional — controlled by `ENABLE_TS_SANDBOX`
- Input validation via `@validate_params` decorator — always apply to tool functions
- No SQL injection risk (Canvas is REST-only), but validate all user inputs

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-03-12
