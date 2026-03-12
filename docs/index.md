# Canvas MCP - Documentation Index

**Version:** 1.0.6 | **Generated:** 2026-03-12 | **Scan:** Exhaustive

---

## Project Overview

- **Type:** Monolith (single cohesive codebase)
- **Primary Language:** Python 3.10+ with TypeScript code execution API
- **Framework:** FastMCP (MCP server framework)
- **Architecture:** Layered modular with conditional tool registration
- **Purpose:** MCP server bridging AI assistants and Canvas LMS

### Quick Reference

- **Tech Stack:** Python/FastMCP + httpx + Pydantic + TypeScript/Node.js
- **Entry Point:** `canvas-mcp-server` CLI (via `src/canvas_mcp/server.py:main()`)
- **Architecture Pattern:** Layered modular - Config > Client > Tools > Privacy
- **Tools:** 100+ MCP tools across 23 modules (student, educator, shared, developer)
- **Tests:** ~4,800 lines across 21 test files (tools, security, efficiency)
- **CI/CD:** 6+ GitHub Actions workflows (publish, security, testing, docs)
- **Deployment:** Local (MCP client managed), Docker, config overlays

---

## Generated Documentation

- [Project Overview](./project-overview.md) - Executive summary, tech stack, capabilities
- [Architecture](./architecture.md) - Technical architecture, component design, data flows
- [Source Tree Analysis](./source-tree-analysis.md) - Annotated directory structure, entry points
- [API Contracts](./api-contracts.md) - Canvas API endpoint catalog by tool module
- [Development Guide](./development-guide.md) - Setup, build, test, coding standards
- [Deployment Guide](./deployment-guide.md) - Docker, CI/CD, configuration overlays

## Existing Documentation (Verified Accurate)

- [Developer Architecture Reference](./CLAUDE.md) - In-depth coding standards, API patterns, architecture details
- [Educator Guide](./EDUCATOR_GUIDE.md) - Complete educator setup, FERPA compliance, 30+ tool reference
- [Student Guide](./STUDENT_GUIDE.md) - Student setup, 5 personal tools + shared tools
- [Development Best Practices](./best-practices.md) - Claude Code workflow, session management
- [Course Documentation Template](./course_documentation_prompt_template.md) - Hybrid documentation approach

## Root-Level Documentation

- [README.md](../README.md) - Primary project documentation with installation
- [AGENTS.md](../AGENTS.md) - AI agent usage guide, tool catalog, decision trees
- [SECURITY.md](../SECURITY.md) - Security policy, vulnerability reporting, best practices
- [Tool Documentation](../tools/README.md) - Comprehensive tool reference
- [Tool Manifest](../tools/TOOL_MANIFEST.json) - Machine-readable tool catalog

## Examples

- [Educator Quickstart](../examples/educator_quickstart.md)
- [Student Quickstart](../examples/student_quickstart.md)
- [Bulk Grading Example](../examples/bulk_grading_example.md)
- [Real-World Workflows](../examples/real_world_workflows.md)
- [Common Issues](../examples/common_issues.md)

---

## Getting Started

### For Development
1. Review [Development Guide](./development-guide.md) for setup instructions
2. Read [Architecture](./architecture.md) for system understanding
3. Check [CLAUDE.md](./CLAUDE.md) for coding standards and patterns
4. Run `pytest` to verify test suite passes

### For New Features (Brownfield PRD)
1. Read [Architecture](./architecture.md) for component design and data flows
2. Check [API Contracts](./api-contracts.md) for existing Canvas API usage
3. Review [Source Tree](./source-tree-analysis.md) for file locations
4. Follow the "Adding New Tools" section in [Development Guide](./development-guide.md)

### AI-Assisted Development
When using this documentation with AI assistants for brownfield development:
- **Point to this index** as the primary context source
- **Architecture doc** provides component boundaries and integration patterns
- **API contracts** show existing endpoint usage to avoid duplication
- **Source tree** helps locate files for modification
- **Development guide** ensures coding standards compliance
