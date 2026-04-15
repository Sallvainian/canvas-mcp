# Project Overview

**Project:** canvas-mcp · **Version:** 1.0.6 · **License:** MIT
**Generated:** 2026-04-14 (full rescan, exhaustive)

---

## Purpose

**canvas-mcp** is a [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes the Canvas LMS REST API to AI-enabled clients (Claude Desktop, Cursor, Zed, etc.) as typed, role-gated, FERPA-aware tools. It lets educators and students drive Canvas workflows — grading, messaging, analytics, peer reviews, discussion participation — through natural-language conversation with an AI assistant.

The server is designed around four operating pillars:

1. **Role-gated surface area** — One binary, three personas. `CANVAS_MCP_USER_TYPE` controls whether 121 (educator), 126 (student), or all 129 tools register.
2. **FERPA-first privacy** — All student PII passes through a hash-based anonymization layer at the HTTP response boundary. Real user IDs remain intact so messaging/grading still works; names, emails, SIS IDs are redacted.
3. **Token economy** — Responses are formatted in `COMPACT` mode by default (pipe-delimited, abbreviated labels, ~40–85% token reduction vs. standard JSON). Bulk operations execute in a TypeScript sandbox so datasets never enter the LLM context (verified ~99.7% reduction on bulk-grade workflows).
4. **Type-coerced inputs** — Every MCP tool runs through `@validate_params`, which handles Union types, Optional types, JSON-string → list, and comma-separated → list. Client-side type sloppiness is absorbed.

---

## Executive Summary

| | |
|---|---|
| Repository type | Monolith (single part) |
| Primary language | Python 3.12+ |
| Secondary language | TypeScript 5.3+ (bulk-operation submodule, used by `code_execution.py`) |
| Framework | [FastMCP](https://github.com/jlowin/fastmcp) ≥2.14.0 (stdio transport) |
| MCP tools | **129** across 23 tool modules |
| MCP resources | **3** (course syllabus, assignment description, code-api file) |
| MCP prompts | **1** (`summarize-course`) |
| Dependencies (runtime) | httpx, pydantic v2, python-dotenv, python-dateutil, markdown, requests |
| Dev toolchain | pytest, pytest-asyncio, black 26, ruff, mypy (strict) |
| Build | hatchling → wheel; installable via `uv pip install -e .` |
| Distribution | PyPI (`canvas-mcp`), MCP Registry (`io.github.vishalsachdev/canvas-mcp`) |
| Container | `python:3.12-slim` + uv + non-root user + HEALTHCHECK |
| Tests | 328 test functions across 23 files (14 tool modules covered; 10 lack tests) |
| CI workflows | 9 GitHub Actions (test, security, publish, Claude auto-review, auto-update-docs, …) |

---

## Tech Stack (Table)

### Runtime — Python
| Category | Technology | Version | Justification |
|----------|------------|---------|---------------|
| Language | Python | ≥3.12 | PEP 604 `T \| None`, modern typing |
| MCP | FastMCP | ≥2.14.0 | Sole framework dependency; stdio transport |
| HTTP | httpx | ≥0.28.1 | Async, pooled, Link-header aware |
| HTTP fallback | requests | ≥2.32.0 | Script-side sync calls |
| Validation | Pydantic | ≥2.12.0 | Type schemas |
| Config | python-dotenv | ≥1.0.0 | `.env` on import |
| Dates | python-dateutil | ≥2.8.0 | Flexible human parsing |
| Markdown | markdown | ≥3.7.0 | Assignment body conversion |

### Runtime — TypeScript (code_api submodule)
| Category | Technology | Version | Use |
|----------|------------|---------|-----|
| Runtime | Node.js | ≥20 | Sandbox execution (container image `node:20-alpine`) |
| Language | TypeScript | ^5.3.3 | Strict mode, ES2022 ESM |
| HTTP | node-fetch | ^3.3.2 | Canvas client |
| Exec | tsx, ts-node | ^4.20.6 / ^10.9.2 | TS execution in Node |

### Build & packaging
| Tool | Purpose |
|------|---------|
| hatchling | Python build backend |
| uv | Recommended installer + lockfile (`uv.lock`) |
| tsc | TS compilation (rootDir `src/canvas_mcp/code_api`, outDir `dist`) |
| hatchling wheel | PyPI distribution |

### Dev / CI
| Tool | Role |
|------|------|
| pytest ≥7.0.0 | Unit + integration tests |
| pytest-asyncio ≥0.21.0 | Async test support |
| pytest-cov | Coverage in security CI |
| black 26.3.1 | Formatter (line 88) |
| ruff ≥0.1.0 | Lint (E, W, F, I, B, C4, UP) |
| mypy ≥1.5.0 | Strict type-check |
| pip-audit | CVE scan (weekly) |

---

## Architecture Type

**Layered, registrar-pattern monolith with a single HTTP choke point.**

```
MCP Client (Claude/Cursor/Zed)
    └─ stdio JSON-RPC
        └─ FastMCP Server (server.py)
            ├─ Tool Layer (23 modules, 129 tools)
            ├─ Resources + Prompts
            └─ Core Utilities
                └─ make_canvas_request() ← only way out
                    └─ Canvas LMS REST API
```

All tool modules depend on `core/client.py::make_canvas_request`, `core/cache.py::get_course_id`, and `core/validation.py::validate_params`. No tool module talks to Canvas directly. See [architecture.md](./architecture.md) §4 for component details.

A separate **TypeScript submodule** at `src/canvas_mcp/code_api/` provides bulk-operation functions (`bulkGrade`, `bulkGradeDiscussion`, `listSubmissions`, etc.) that the `execute_typescript` MCP tool invokes inside a Node.js sandbox (local or container mode).

---

## Repository Structure

```
canvas-mcp/
├── src/canvas_mcp/       # Python package (core, tools, resources, code_api)
├── tests/                # pytest suite (tools/*, security/*)
├── tools/                # Tool-reference docs (README, TOOL_MANIFEST.json)
├── examples/             # Workflow tutorials
├── docs/                 # ← This documentation
├── config/overlays/      # env preset files (baseline, enterprise, public)
├── .github/workflows/    # 9 CI workflows
├── archive/              # Legacy reference code
├── Dockerfile            # python:3.12-slim + uv + non-root
├── pyproject.toml        # Python build (hatchling)
├── package.json          # TS submodule config
├── tsconfig.json         # TS compiler config
├── server.json           # MCP Registry metadata
├── README.md             # Primary entry
├── AGENTS.md             # AI-agent guide
└── SECURITY.md           # Security policy
```

Full annotated tree: [source-tree-analysis.md](./source-tree-analysis.md).

---

## Links to Detailed Documentation

| Topic | File |
|-------|------|
| Master index | [index.md](./index.md) |
| Architecture walkthrough | [architecture.md](./architecture.md) |
| Source tree (annotated) | [source-tree-analysis.md](./source-tree-analysis.md) |
| All 129 MCP tools catalogued | [api-contracts.md](./api-contracts.md) |
| Local dev / testing | [development-guide.md](./development-guide.md) |
| Docker / PyPI / MCP Registry | [deployment-guide.md](./deployment-guide.md) |
| Developer conventions (TDD, doc source-of-truth) | [CLAUDE.md](./CLAUDE.md) |
| End-user educator guide | [EDUCATOR_GUIDE.md](./EDUCATOR_GUIDE.md) |
| End-user student guide | [STUDENT_GUIDE.md](./STUDENT_GUIDE.md) |
| AI agent usage | [../AGENTS.md](../AGENTS.md) |
| Full tool reference (human) | [../tools/README.md](../tools/README.md) |

---

## What Changed Since the Previous Scan (2026-03-12 → 2026-04-14)

Git commits since the previous documentation scan:

| Commit | Change |
|--------|--------|
| `0307c55` | **fix:** switch `grading_export` to per-assignment `/submissions` endpoint |
| `a4630f7` | **feat:** add `grading_export` bulk submission export tool |
| `bd03679` | **fix:** dependabot security alerts for `black` and `authlib` |
| `0978b59` | **refactor:** codebase cleanup — fix all mypy/ruff errors, split oversized modules, migrate prints to logging |
| `fb8d4f1` | **docs:** add project context for AI agents, fix overly broad gitignore |

**Impact on docs:**
- Added `grading_export.py` tool module (1 new MCP tool) with 33 new tests in `test_grading_export.py`
- Tool count grew from ~100 (prior scan estimate) to **129** (verified count by `grep -c "@mcp.tool"`)
- Python version requirement bumped from 3.10+ to **3.12+** (verified in `pyproject.toml`)
- `black` bumped to 26.3.1 (dependabot)
- Logging: all `print()` calls in source replaced with `log_info`/`log_error`/etc.
