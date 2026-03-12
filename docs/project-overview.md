# Canvas MCP - Project Overview

**Version:** 1.0.6 | **License:** MIT | **Author:** Vishal Sachdev
**Generated:** 2026-03-12 | **Scan Level:** Exhaustive

---

## Executive Summary

Canvas MCP is a Model Context Protocol (MCP) server that bridges AI assistants and the Canvas Learning Management System (LMS). It provides 100+ MCP tools enabling natural language interactions with Canvas data through any MCP-compatible client (Claude Desktop, Cursor, Zed, Windsurf, Continue).

The server targets two primary user types:
- **Students** - Assignment tracking, grade monitoring, peer review management, course content access
- **Educators** - Assignment/grading management, student analytics, peer review facilitation, FERPA-compliant communication, bulk operations

A secondary TypeScript code execution API enables token-efficient bulk operations (99.7% token savings for large batch processing).

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.10+ | Primary server implementation |
| Language | TypeScript | 5.3+ | Code execution API for bulk operations |
| Framework | FastMCP | 2.14+ | MCP server framework with tool registration |
| HTTP Client | httpx | 0.28+ | Async HTTP with connection pooling |
| Validation | Pydantic | 2.12+ | Data validation and settings management |
| Config | python-dotenv | 1.0+ | Environment-based configuration |
| Dates | python-dateutil | 2.8+ | Flexible date parsing |
| Markdown | markdown | 3.7+ | Markdown-to-HTML conversion |
| Build | hatchling | - | Python package build backend |
| Package Mgr | uv | - | Fast Python dependency management |
| Runtime (TS) | Node.js (ts-node/tsx) | 20+ | TypeScript execution environment |
| Linting | ruff | 0.1+ | Python linting and formatting |
| Formatting | black | 23+ | Python code formatting |
| Type Check | mypy | 1.5+ | Static type analysis |
| Testing | pytest | 7.0+ | Test framework with async support |
| Container | Docker | - | Deployment (Python 3.12-slim base) |

## Architecture Classification

- **Repository Type:** Monolith (single cohesive codebase)
- **Architecture Pattern:** Layered modular with tool registration
- **Transport:** stdio (MCP standard)
- **API Integration:** Canvas LMS REST API v1
- **Deployment:** Local process (started by MCP clients), Docker optional

## Architecture Layers

1. **Entry Point** - CLI handling, server lifecycle (`server.py`)
2. **Configuration** - Environment-based config with validation (`core/config.py`)
3. **Transport/Client** - Async HTTP with retry, pagination, rate limiting (`core/client.py`)
4. **Tool Registration** - 23 modular tool files registered conditionally by user type
5. **Core Utilities** - Caching, validation, date handling, response formatting
6. **Privacy Layer** - FERPA-compliant anonymization before AI processing
7. **Code Execution** - TypeScript API for bulk operations with optional sandboxing
8. **Resources** - MCP resources (syllabus, descriptions) and prompts

## Key Capabilities

### For Students (5 personal tools + shared tools)
- Upcoming assignment tracking with deadlines
- Grade monitoring across all courses
- Submission status and peer review management
- Course content and discussion access

### For Educators (40+ tools)
- Assignment CRUD, grading (individual and bulk), rubric management
- Student analytics, performance tracking, risk identification
- Peer review facilitation with quality analysis and follow-up campaigns
- Discussion management and participation grading
- FERPA-compliant messaging and announcements
- Module and page management (7 module tools, 5 page tools)
- Quiz management (6 tools)
- Accessibility scanning (UDOIT integration)

### Developer Tools (3 tools)
- `search_canvas_tools` - Discover available code API operations
- `execute_typescript` - Run TypeScript locally for bulk operations
- `list_code_api_modules` - Browse code API module structure

## Security & Privacy

- **FERPA Compliance:** Source-level data anonymization (names to Student_XXXXXXXX)
- **PII Protection:** Email masking, phone/SSN removal from content
- **Local Processing:** All data processed locally, no external transmission
- **Token Security:** Environment-based credential management
- **Code Execution Sandbox:** Optional Docker/Podman isolation with resource limits
- **Configurable Privacy:** `ENABLE_DATA_ANONYMIZATION=true` for educators

## Links to Detailed Documentation

- [Architecture](./architecture.md) - Technical architecture deep dive
- [Source Tree Analysis](./source-tree-analysis.md) - Annotated directory structure
- [API Contracts](./api-contracts.md) - Canvas API endpoint catalog
- [Development Guide](./development-guide.md) - Setup, build, test instructions
- [Deployment Guide](./deployment-guide.md) - Docker and CI/CD details
