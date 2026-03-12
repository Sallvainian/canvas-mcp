# Canvas MCP - Architecture Document

**Generated:** 2026-03-12 | **Scan Level:** Exhaustive

---

## 1. Architecture Overview

Canvas MCP follows a **layered modular architecture** with conditional tool registration. The server acts as a bridge between MCP clients (Claude Desktop, Cursor, etc.) and the Canvas LMS REST API.

```
MCP Client (Claude/Cursor/Zed)
    │ (stdio transport)
    ▼
┌─────────────────────────────────┐
│         FastMCP Server          │  server.py
│   (tool registration, lifecycle)│
├─────────────────────────────────┤
│      Tool Layer (23 modules)    │  tools/*.py
│  ┌───────┬──────────┬─────────┐ │
│  │Student│ Educator │ Shared  │ │  Conditional registration
│  │(5)    │ (40+)    │ (17+)   │ │  based on user_type
│  └───────┴──────────┴─────────┘ │
├─────────────────────────────────┤
│      Core Utilities Layer       │  core/*.py
│  ┌──────┬───────┬──────┬──────┐ │
│  │Config│Client │Cache │Valid.│ │
│  │      │(httpx)│      │      │ │
│  ├──────┼───────┼──────┼──────┤ │
│  │Dates │Format │Anon. │Types │ │
│  └──────┴───────┴──────┴──────┘ │
├─────────────────────────────────┤
│    Privacy Layer (optional)     │  core/anonymization.py
│  SHA256 ID mapping, PII removal │
├─────────────────────────────────┤
│    Code Execution (optional)    │  code_api/*.ts
│  TypeScript bulk ops + sandbox  │
└─────────────────────────────────┘
         │
         ▼ (HTTPS + Bearer token)
    Canvas LMS REST API
```

## 2. Component Architecture

### 2.1 Server Entry Point (`server.py`, 229 lines)

The server orchestrates startup, tool registration, and lifecycle management.

**Key responsibilities:**
- Creates `FastMCP` instance with configurable server name
- Registers tools conditionally based on `CANVAS_MCP_USER_TYPE` (educator/student/all)
- Handles CLI arguments (`--test`, `--config`)
- Manages graceful shutdown with HTTP client cleanup

**Tool registration flow:**
```python
def register_all_tools(mcp):
    # Always registered (shared tools)
    register_course_tools(mcp)
    register_discussion_tools(mcp)
    register_page_tools(mcp)
    register_module_tools(mcp)
    register_other_tools(mcp)
    register_search_helpers(mcp)

    # Educator-only tools
    if user_type != "student":
        register_assignment_tools(mcp)
        register_rubric_tools(mcp)
        register_analytics_tools(mcp)
        register_messaging_tools(mcp)
        register_enrollment_tools(mcp)
        register_peer_review_tools(mcp)
        register_gradebook_tools(mcp)
        register_quiz_tools(mcp)
        register_accessibility_tools(mcp)
        register_content_migration_tools(mcp)

    # Student-only tools
    if user_type != "educator":
        register_student_tools(mcp)

    # Developer tools
    register_discovery_tools(mcp)
    register_code_execution_tools(mcp)
```

### 2.2 Configuration System (`core/config.py`, 171 lines)

**Pattern:** Singleton with lazy initialization

```python
_config_instance = None

def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
```

**Configuration categories:**
| Category | Variables | Examples |
|----------|----------|---------|
| Required | 2 | `CANVAS_API_TOKEN`, `CANVAS_API_URL` |
| Server | 4 | `MCP_SERVER_NAME`, `DEBUG`, `API_TIMEOUT`, `CACHE_TTL` |
| Privacy | 2 | `ENABLE_DATA_ANONYMIZATION`, `ANONYMIZATION_DEBUG` |
| Sandbox | 10 | `ENABLE_TS_SANDBOX`, `TS_SANDBOX_MODE`, limits |
| Display | 2 | `CANVAS_MCP_VERBOSITY`, `CANVAS_MCP_USER_TYPE` |
| Metadata | 2 | `INSTITUTION_NAME`, `TIMEZONE` |

### 2.3 HTTP Client (`core/client.py`, 435 lines)

The central HTTP communication layer with these features:

**Rate limit handling:**
- Exponential backoff (1s, 2s, 4s)
- Respects `Retry-After` header from Canvas API
- 3 retry attempts for 429/5xx errors
- No retries on 4xx client errors

**Pagination:**
- `fetch_all_paginated_results()` collects all pages automatically
- Configurable `per_page` parameter (default varies by endpoint)
- Follows Canvas `Link` header pagination

**Anonymization integration:**
- Endpoint-based routing determines if anonymization applies
- Applies to: user data, discussions, submissions, assignments
- Transparent to tool layer - anonymization happens at HTTP response level

**File upload:**
- 3-step Canvas file upload (request slot, upload to S3, confirm)
- Multipart form data support
- S3 redirect handling

**Progress polling:**
- `poll_canvas_progress()` for async Canvas operations
- Adaptive interval: 1s initial, grows to 5s max
- Configurable timeout

### 2.4 Validation System (`core/validation.py`, 220 lines)

**Pattern:** Decorator-based parameter validation

```python
@validate_params
async def my_tool(course_id: str, limit: int = 10, include_users: bool = False):
    ...
```

The `@validate_params` decorator:
1. Introspects type hints via `get_type_hints()`
2. Validates and coerces each parameter (str, int, float, bool, list, dict, Union, Optional)
3. Handles JSON string parsing for complex types
4. Returns standardized error responses for invalid input

### 2.5 Response Formatting (`core/response_formatter.py`, 460 lines)

Three verbosity levels for token efficiency:

| Level | Style | Token Savings | Example |
|-------|-------|--------------|---------|
| COMPACT | Pipe-delimited, 1-letter bools | ~70% | `HW1\|100pts\|Y\|Jan 21` |
| STANDARD | Label: Value | ~30% | `Due: Jan 21, Points: 100` |
| VERBOSE | Full labels | 0% | `Due Date: 2026-01-21T23:59:00Z` |

### 2.6 Anonymization System (`core/anonymization.py`, 297 lines)

**FERPA compliance via source-level anonymization:**

```
Real Data → SHA256 Hash → Student_XXXXXXXX
"Jane Doe" → hash("user_12345") → "Student_a7b3c2d1"
```

- Consistent mapping: same real ID always produces same anonymous ID
- Session-scoped cache for performance
- PII removal from discussion text (email, phone, SSN patterns)
- Preserves essential fields (Canvas IDs, timestamps, roles)
- Educator-only feature (students access only their own data)

### 2.7 Peer Review Analytics (`core/peer_reviews.py` + `peer_review_comments.py`, ~1,168 lines)

Sophisticated analytics engine for peer review management:

- **Completion tracking:** Reviewer-to-reviewee mapping, completion rates
- **Follow-up system:** Prioritized lists (urgent/medium/low) with recommended actions
- **Comment quality scoring (0-5):** Word count, constructiveness, specificity, sentiment
- **Problematic review detection:** Too short, generic, harsh language, copy-paste
- **Report generation:** Markdown, CSV, JSON formats

### 2.8 Code Execution API (`code_api/`, 17 TypeScript files)

Parallel TypeScript runtime for token-efficient bulk operations:

```
Claude Context                    Local Execution
─────────────                    ───────────────
"Grade 90 submissions"    →      bulkGrade({
(3.5K tokens)                      courseId: "60366",
                                   assignmentId: "123",
                                   gradingFunction: (sub) => {
                                     // Process locally
                                     return { points: 100 };
                                   }
                                 });
                          ←      Summary: "90 graded, 0 failed"
```

**Available operations:**
| Module | Functions |
|--------|-----------|
| `grading/` | `bulkGrade`, `gradeWithRubric` |
| `assignments/` | `listSubmissions` |
| `discussions/` | `listDiscussions`, `postEntry`, `bulkGradeDiscussion` |
| `courses/` | `listCourses`, `getCourseDetails` |
| `communications/` | `sendMessage` |

**Sandbox options:**
- Default: Runs with local user permissions
- Optional: Docker/Podman container isolation
- Configurable: Timeout, memory, CPU limits, network allowlist

## 3. Data Flow

### 3.1 Standard Tool Call Flow

```
MCP Client → FastMCP Server → Tool Function → @validate_params
    → Core Client (make_canvas_request)
    → Rate Limit Check → HTTP Request → Canvas API
    → Response → Anonymization (if enabled) → Response Formatter
    → Tool Output → FastMCP → MCP Client
```

### 3.2 Bulk Operation Flow (Code Execution)

```
MCP Client → execute_typescript tool
    → Write TS code to temp file
    → Spawn Node.js process (sandbox optional)
    → TS code calls Canvas API directly via client.ts
    → Local processing (no context cost)
    → Return summary to MCP Client
```

### 3.3 Course ID Resolution Flow

```
Input (any format) → get_course_id()
    → Is numeric? → Return directly
    → Check code_to_id cache → Return if found
    → Refresh cache from API → Check again
    → Try SIS format (sis_course_id:xxx) → Return if found
    → Return original (may fail at API level)
```

## 4. Security Architecture

### 4.1 Authentication
- Canvas API Bearer token stored in `.env` file
- Token loaded at startup, validated before server starts
- No MCP-level authentication (relies on local execution model)

### 4.2 Privacy Controls
- Anonymization enabled per environment (`ENABLE_DATA_ANONYMIZATION`)
- Applied at HTTP response level, transparent to tools
- Local CSV mapping files for educator de-anonymization

### 4.3 Code Execution Safety
- Optional sandbox via Docker/Podman
- Resource limits: timeout, memory, CPU seconds
- Network allowlist for outbound connections
- Temp file isolation with auto-cleanup

### 4.4 Input Validation
- Type coercion and validation via `@validate_params` decorator
- Path validation for file access (code API resources)
- No SQL (Canvas is REST-only), XSS mitigated by Canvas platform

## 5. Testing Architecture

| Test Category | Files | Tests | Focus |
|--------------|-------|-------|-------|
| Tool tests | 13 | ~100+ | MCP tool input/output, error handling |
| Analytics tests | 1 | 16 | Analytics accuracy, edge cases |
| Date tests | 1 | 17 | Date parsing, relative formatting |
| Token efficiency | 1 | 12 | Verbosity savings verification |
| Security tests | 5 | ~30+ | Auth, FERPA, injection, sandboxing |

**Test patterns:**
- AsyncMock for Canvas API calls
- Shared fixtures in `conftest.py` (sample data, mock resolvers)
- `get_tool_function()` helper to extract registered tools from FastMCP
- Success + error + edge case coverage per tool

## 6. Deployment Architecture

### Docker
- Base: `python:3.12-slim`
- Uses `uv` for fast dependency installation
- Non-root user (`mcp`) for security
- Health check: Python import verification
- Requires `CANVAS_API_TOKEN` and `CANVAS_API_URL` at runtime

### CI/CD (GitHub Actions)
- **publish-mcp.yml:** Tag-triggered PyPI + MCP Registry publishing (OIDC)
- **security-testing.yml:** 6-job pipeline (pytest, Bandit, Semgrep, pip-audit, TruffleHog, CodeQL)
- **canvas-mcp-testing.yml:** PR/push test automation
- **auto-update-docs.yml:** Documentation synchronization
- **claude-code-review.yml:** AI-assisted code review
- **weekly-maintenance.yml:** Scheduled dependency checks

### Configuration Overlays
Three tiers for progressive security hardening:
- **baseline.env:** Sandbox enabled, localhost binding, log redaction
- **public.env:** + Network blocking, token encryption hints
- **enterprise.env:** + Client auth placeholders, audit logging, SIEM forwarding
