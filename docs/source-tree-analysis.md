# Canvas MCP - Source Tree Analysis

**Generated:** 2026-03-12 | **Scan Level:** Exhaustive

---

## Directory Structure

```
canvas-mcp/                          # Project root
├── pyproject.toml                   # Python project config (hatchling build)
├── package.json                     # Node.js config for TypeScript code API
├── tsconfig.json                    # TypeScript compiler configuration
├── uv.lock                          # Locked Python dependencies
├── package-lock.json                # Locked Node.js dependencies
├── env.template                     # Environment variable template
├── Dockerfile                       # Docker deployment (Python 3.12-slim)
├── server.json                      # MCP registry metadata (v1.0.6)
├── start_canvas_server.sh           # Startup script with env loading
├── LICENSE                          # MIT License
├── README.md                        # * Primary project documentation
├── AGENTS.md                        # * AI agent usage guide
├── SECURITY.md                      # * Security policy
│
├── src/
│   └── canvas_mcp/                  # Main Python package
│       ├── __init__.py              # Package init, version (1.0.6), entry point
│       ├── server.py                # * MCP server entry point, tool registration
│       │
│       ├── core/                    # Core utilities layer
│       │   ├── __init__.py          # Barrel exports (27 functions/classes)
│       │   ├── config.py            # * Config singleton (20+ env vars)
│       │   ├── client.py            # * HTTP client, retry, pagination, anonymization
│       │   ├── cache.py             # Bidirectional course code/ID cache
│       │   ├── validation.py        # Parameter validation decorator
│       │   ├── types.py             # TypedDict definitions (Course, Assignment, Page, Announcement)
│       │   ├── dates.py             # Date parsing, smart formatting (compact/relative)
│       │   ├── logging.py           # Structured logging with context
│       │   ├── anonymization.py     # * FERPA anonymization (SHA256-based IDs)
│       │   ├── response_formatter.py # Token-efficient formatting (COMPACT/STANDARD/VERBOSE)
│       │   ├── peer_reviews.py      # * Peer review analytics engine
│       │   └── peer_review_comments.py # * Comment quality analysis
│       │
│       ├── tools/                   # MCP tool implementations (23 modules)
│       │   ├── __init__.py          # Tool registration orchestrator
│       │   ├── courses.py           # Course listing, details, content overview
│       │   ├── assignments.py       # * Assignment CRUD, submissions, grading
│       │   ├── discussions.py       # Discussion topics, entries, replies
│       │   ├── rubrics.py           # * Rubric CRUD, association, grading
│       │   ├── student_tools.py     # Student-specific tools (grades, deadlines, TODO)
│       │   ├── messaging.py         # * Conversations, bulk messaging, reminders
│       │   ├── analytics.py         # * Student/course/assignment analytics
│       │   ├── enrollment.py        # User enrollment, group management
│       │   ├── modules.py           # Module CRUD, items management
│       │   ├── pages.py             # Page CRUD, bulk updates
│       │   ├── quizzes.py           # Quiz CRUD, questions, statistics
│       │   ├── peer_reviews.py      # Peer review tracking, assignments
│       │   ├── peer_review_comments.py # Comment extraction, quality analysis
│       │   ├── gradebook.py         # Grade export, assignment groups, late policy
│       │   ├── discussion_analytics.py # Discussion participation analytics
│       │   ├── discovery.py         # Code API tool discovery
│       │   ├── code_execution.py    # * TypeScript execution with sandboxing
│       │   ├── accessibility.py     # UDOIT accessibility scanning
│       │   ├── message_templates.py # Message template rendering
│       │   ├── other_tools.py       # Conversation management, unread counts
│       │   ├── search_helpers.py    # Fuzzy search for assignments/students/discussions
│       │   └── content_migrations.py # Course content copy operations
│       │
│       ├── resources/               # MCP resources and prompts
│       │   ├── __init__.py          # Barrel export
│       │   └── resources.py         # Course syllabus, assignment desc, code API files
│       │
│       └── code_api/                # TypeScript code execution API
│           ├── client.ts            # * HTTP client with retry, pagination
│           ├── index.ts             # Main entry, re-exports
│           └── canvas/
│               ├── index.ts         # Module re-exports
│               ├── assignments/
│               │   ├── index.ts
│               │   └── listSubmissions.ts  # Paginated submission fetching
│               ├── grading/
│               │   ├── index.ts
│               │   ├── bulkGrade.ts        # * Concurrent bulk grading
│               │   └── gradeWithRubric.ts  # Rubric-based grading
│               ├── discussions/
│               │   ├── index.ts
│               │   ├── listDiscussions.ts  # Discussion topic listing
│               │   ├── postEntry.ts        # Post to discussions
│               │   └── bulkGradeDiscussion.ts # * Discussion participation grading
│               ├── courses/
│               │   ├── index.ts
│               │   ├── listCourses.ts      # Course listing
│               │   └── getCourseDetails.ts # Course detail fetching
│               └── communications/
│                   ├── index.ts
│                   └── sendMessage.ts      # Canvas inbox messaging
│
├── tests/                           # Test suite (~4,800 lines)
│   ├── conftest.py                  # * Shared fixtures (mocks, sample data)
│   ├── test_analytics.py            # Analytics tool tests (16 tests)
│   ├── test_dates.py                # Date formatting tests (17 tests)
│   ├── test_token_efficiency.py     # Token savings verification (12 tests)
│   ├── tools/                       # Tool-specific tests
│   │   ├── test_assignments.py
│   │   ├── test_courses.py
│   │   ├── test_discussions.py
│   │   ├── test_discussion_analytics.py
│   │   ├── test_gradebook.py
│   │   ├── test_messaging.py
│   │   ├── test_modules.py
│   │   ├── test_pages.py
│   │   ├── test_peer_reviews.py
│   │   ├── test_quizzes.py
│   │   ├── test_rubrics.py
│   │   ├── test_search_helpers.py
│   │   └── test_student_tools.py
│   └── security/                    # Security tests
│       ├── test_authentication.py
│       ├── test_code_execution.py
│       ├── test_dependencies.py
│       ├── test_ferpa_compliance.py
│       └── test_input_validation.py
│
├── tools/                           # External tool documentation
│   ├── README.md                    # Comprehensive tool reference
│   └── TOOL_MANIFEST.json           # Machine-readable tool catalog
│
├── examples/                        # Usage examples
│   ├── educator_quickstart.md
│   ├── student_quickstart.md
│   ├── bulk_grading_example.md
│   ├── common_issues.md
│   └── real_world_workflows.md
│
├── config/
│   └── overlays/                    # Deployment tier configs
│       ├── baseline.env             # Base security settings
│       ├── public.env               # Public deployment hardening
│       └── enterprise.env           # Enterprise with audit logging
│
├── docs/                            # Documentation and GitHub Pages
│   ├── CLAUDE.md                    # Developer architecture reference
│   ├── EDUCATOR_GUIDE.md            # Educator setup and usage
│   ├── STUDENT_GUIDE.md             # Student setup and usage
│   ├── best-practices.md            # Development workflow practices
│   ├── course_documentation_prompt_template.md
│   ├── index.html                   # GitHub Pages site
│   ├── styles.css                   # GitHub Pages styles
│   ├── educator-guide.html          # GitHub Pages
│   ├── student-guide.html           # GitHub Pages
│   ├── bulk-grading.html            # GitHub Pages
│   └── CNAME                        # GitHub Pages custom domain
│
├── .github/workflows/               # CI/CD pipelines
│   ├── publish-mcp.yml              # * PyPI + MCP Registry publishing
│   ├── security-testing.yml         # * 6-job security pipeline
│   ├── canvas-mcp-testing.yml       # Test automation
│   ├── auto-update-docs.yml         # Doc auto-updates
│   ├── claude-code-review.yml       # AI code review
│   └── weekly-maintenance.yml       # Scheduled maintenance
│
└── archive/                         # Legacy monolithic implementation
```

**Legend:** `*` = Critical file for understanding architecture

## Critical Folders

| Directory | Purpose | Files |
|-----------|---------|-------|
| `src/canvas_mcp/core/` | Core utilities, HTTP client, config, privacy | 11 files |
| `src/canvas_mcp/tools/` | MCP tool implementations (100+ tools) | 23 files |
| `src/canvas_mcp/code_api/` | TypeScript bulk operation API | 17 files |
| `tests/` | Test suite with tool + security coverage | 21 files |
| `.github/workflows/` | CI/CD automation | 6+ workflows |
| `config/overlays/` | Deployment tier configurations | 3 files |

## Entry Points

| Entry Point | Path | Purpose |
|------------|------|---------|
| CLI | `canvas-mcp-server` (via pyproject.toml scripts) | Primary entry, starts MCP server |
| Python | `src/canvas_mcp/__init__.py:main()` | Package entry point |
| Server | `src/canvas_mcp/server.py:main()` | Server creation, tool registration, CLI args |
| Docker | `Dockerfile` → `canvas-mcp-server` | Container entrypoint |
| Shell | `start_canvas_server.sh` | Manual startup with env loading |

## File Statistics

| Category | Count | ~Lines |
|----------|-------|--------|
| Python source (core) | 11 | ~3,300 |
| Python source (tools) | 23 | ~10,000+ |
| Python source (resources) | 2 | ~180 |
| Python source (server) | 2 | ~245 |
| TypeScript source | 17 | ~1,500 |
| Python tests | 21 | ~4,800 |
| Config files | 8 | ~300 |
| Documentation (md) | 15+ | ~5,000+ |
| CI/CD workflows | 6+ | ~500+ |
| **Total source** | **~55** | **~15,000+** |
