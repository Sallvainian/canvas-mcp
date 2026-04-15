# Canvas MCP — Documentation Index

**Project:** canvas-mcp · **Version:** 1.0.6 · **License:** MIT
**Generated:** 2026-04-14 (full rescan, exhaustive)

> Primary entry point for AI-assisted development on this codebase. Point your brownfield PRD / planning tools at this file.

---

## Project Overview

- **Type:** Monolith (1 part) — Python FastMCP backend MCP server
- **Primary language:** Python 3.12+
- **Secondary language:** TypeScript 5.3+ (bulk-operation submodule at `src/canvas_mcp/code_api/`)
- **Architecture pattern:** Layered + registrar pattern with a single HTTP choke point (`core/client.py::make_canvas_request`)
- **Framework:** FastMCP ≥2.14.0 (stdio transport)
- **Distribution:** PyPI `canvas-mcp` + MCP Registry `io.github.vishalsachdev/canvas-mcp`

---

## Quick Reference

- **Tech stack:** Python 3.12+ · FastMCP ≥2.14 · httpx ≥0.28 · Pydantic ≥2.12 · python-dotenv · markdown · dateutil
- **Entry point:** `src/canvas_mcp/server.py::main()` (CLI command: `canvas-mcp-server`)
- **Architecture pattern:** MCP client → FastMCP server → tool layer (23 modules, 129 tools) → core utilities → `make_canvas_request` → Canvas LMS
- **TypeScript submodule:** `src/canvas_mcp/code_api/` invoked via `tools/code_execution.py` (sandbox: local or container `node:20-alpine`)
- **Key env vars:** `CANVAS_API_TOKEN`, `CANVAS_API_URL`, `CANVAS_MCP_USER_TYPE` (all/educator/student), `CANVAS_MCP_VERBOSITY` (compact/standard/verbose), `ENABLE_DATA_ANONYMIZATION`
- **Tool surface:** 129 MCP tools · 3 resources · 1 prompt · ~100 Canvas endpoints touched

---

## Generated Documentation (this scan)

- [Project Overview](./project-overview.md) — tech stack, purpose, what changed since last scan
- [Architecture](./architecture.md) — components, data flow, testing strategy, security controls
- [Source Tree Analysis](./source-tree-analysis.md) — annotated directory tree with per-file descriptions
- [API Contracts](./api-contracts.md) — every one of the 129 MCP tools + 3 resources + 1 prompt catalogued
- [Development Guide](./development-guide.md) — setup, TDD rules, adding a new tool, troubleshooting
- [Deployment Guide](./deployment-guide.md) — PyPI, Docker, MCP Registry, CI/CD, release process

---

## Existing Documentation (preserved)

### Developer-facing (in `docs/`)
- [CLAUDE.md](./CLAUDE.md) — Developer conventions: TDD enforcement, tool doc source-of-truth matrix, architecture patterns
- [best-practices.md](./best-practices.md) — Operational guidance
- [course_documentation_prompt_template.md](./course_documentation_prompt_template.md) — Template for per-course docs

### User-facing (in `docs/`)
- [EDUCATOR_GUIDE.md](./EDUCATOR_GUIDE.md) — End-user guide for the educator persona
- [STUDENT_GUIDE.md](./STUDENT_GUIDE.md) — End-user guide for the student persona
- [educator-guide.html](./educator-guide.html), [student-guide.html](./student-guide.html), [bulk-grading.html](./bulk-grading.html), [index.html](./index.html) — GitHub Pages rendering (published at the domain in `CNAME`)

### Project root
- [../README.md](../README.md) — Primary entry for humans; installation, overview
- [../AGENTS.md](../AGENTS.md) — Authoritative tool reference for AI agents/MCP clients
- [../SECURITY.md](../SECURITY.md) — Security policy
- [../SECURITY_IMPLEMENTATION_GUIDE.md](../SECURITY_IMPLEMENTATION_GUIDE.md) — Security controls documentation
- [../PROJECT_COMPLETION_SUMMARY.md](../PROJECT_COMPLETION_SUMMARY.md) — Release-level summary
- [../LICENSE](../LICENSE) — MIT
- [../tools/README.md](../tools/README.md) — Comprehensive human-facing tool reference
- [../tools/TOOL_MANIFEST.json](../tools/TOOL_MANIFEST.json) — Machine-readable tool catalog
- [../examples/](../examples/) — 5 workflow tutorials: `educator_quickstart`, `student_quickstart`, `bulk_grading_example`, `real_world_workflows`, `common_issues`

---

## Getting Started

### For developers
1. Read [project-overview.md](./project-overview.md) for the 30-second picture
2. Skim [source-tree-analysis.md](./source-tree-analysis.md) to know where things live
3. Read [architecture.md](./architecture.md) §4 (component details) and §6 (tool conventions)
4. Follow [development-guide.md](./development-guide.md) to set up your environment
5. Consult [CLAUDE.md](./CLAUDE.md) before writing code (TDD rules, documentation source-of-truth)

### For AI agents using this server
1. Read [../AGENTS.md](../AGENTS.md) — the authoritative tool + workflow reference
2. Use [api-contracts.md](./api-contracts.md) to look up specific tool signatures
3. Use `list_code_api_modules` / `search_canvas_tools` (if `user_type=all`) to discover bulk-ops

### For deployers
1. Read [deployment-guide.md](./deployment-guide.md) for PyPI/Docker/Registry flow
2. Review [../SECURITY.md](../SECURITY.md) and set `CANVAS_MCP_USER_TYPE` explicitly

---

## Tool Count Summary

| Category | Count |
|----------|-------|
| Tool modules | 23 |
| MCP tools | **129** |
| MCP resources | 3 |
| MCP prompts | 1 |
| TS submodule exports | 9 |
| Tests | 328 across 23 files |
| CI workflows | 9 |

**Role gating:**
- `CANVAS_MCP_USER_TYPE=all` → 129 tools + resources + prompts (default)
- `CANVAS_MCP_USER_TYPE=educator` → 121 tools (no student / developer)
- `CANVAS_MCP_USER_TYPE=student` → 126 tools (no developer)

Full breakdown per module: [source-tree-analysis.md](./source-tree-analysis.md#tool-count-summary).

---

## Regenerating This Documentation

To refresh every generated doc (this file plus the six others listed above):

1. Invoke the `/bmad-document-project` skill
2. When prompted, select **1. Full re-scan** and **3. Exhaustive scan**
3. The workflow archives the old `project-scan-report.json`, re-detects the project type, and rewrites the auto-generated docs while preserving human-authored ones

Human-authored docs (`CLAUDE.md`, `EDUCATOR_GUIDE.md`, `STUDENT_GUIDE.md`, `best-practices.md`, HTML pages) are **not** touched.
