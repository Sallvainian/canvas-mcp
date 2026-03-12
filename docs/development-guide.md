# Canvas MCP - Development Guide

**Generated:** 2026-03-12 | **Scan Level:** Exhaustive

---

## Prerequisites

| Requirement | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Primary runtime |
| Node.js | 20+ | TypeScript code execution API |
| uv | latest | Python package manager (recommended) |
| Git | any | Version control |
| Docker | optional | Container deployment |

## Installation

```bash
# Clone repository
git clone https://github.com/vishalsachdev/canvas-mcp.git
cd canvas-mcp

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package (editable mode)
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Install Node.js dependencies (for code execution API)
npm install
```

## Environment Setup

```bash
# Copy template
cp env.template .env

# Edit with your credentials
# Required:
#   CANVAS_API_TOKEN=your_token_here
#   CANVAS_API_URL=https://your-institution.instructure.com
```

### Key Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CANVAS_API_TOKEN` | Yes | - | Canvas API access token |
| `CANVAS_API_URL` | Yes | - | Canvas instance URL |
| `MCP_SERVER_NAME` | No | `canvas-mcp` | Server display name |
| `DEBUG` | No | `false` | Enable debug mode |
| `API_TIMEOUT` | No | `30` | HTTP timeout (seconds) |
| `CACHE_TTL` | No | `300` | Cache lifetime (seconds) |
| `MAX_CONCURRENT_REQUESTS` | No | `10` | Concurrent API limit |
| `ENABLE_DATA_ANONYMIZATION` | No | `false` | FERPA anonymization |
| `CANVAS_MCP_USER_TYPE` | No | `all` | Tool filtering (all/educator) |
| `CANVAS_MCP_VERBOSITY` | No | `COMPACT` | Response detail level |
| `ENABLE_TS_SANDBOX` | No | `false` | Code execution sandbox |

## Running

```bash
# Start MCP server (standard mode)
canvas-mcp-server

# Test Canvas API connection
canvas-mcp-server --test

# Display configuration
canvas-mcp-server --config

# Via shell script (loads .env automatically)
./start_canvas_server.sh
```

## Build

```bash
# Build Python package
python -m build

# Build TypeScript (compile to dist/)
npm run build
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v --tb=short

# Run specific test file
pytest tests/tools/test_assignments.py

# Run specific test class
pytest tests/tools/test_assignments.py::TestCreateAssignment

# Run security tests only
pytest tests/security/

# Run with coverage
pytest --cov=src/canvas_mcp --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_analytics.py        # 16 tests - analytics tools
├── test_dates.py            # 17 tests - date formatting
├── test_token_efficiency.py # 12 tests - token savings
├── tools/                   # Tool-specific tests
│   ├── test_assignments.py  # Assignment CRUD, grading
│   ├── test_courses.py      # Course listing, details
│   ├── test_discussions.py  # Discussion management
│   ├── test_gradebook.py    # Grade export, groups
│   ├── test_messaging.py    # Conversations, bulk send
│   ├── test_modules.py      # Module CRUD
│   ├── test_pages.py        # Page CRUD
│   ├── test_peer_reviews.py # Peer review tracking
│   ├── test_quizzes.py      # Quiz management
│   ├── test_rubrics.py      # Rubric CRUD, grading
│   ├── test_search_helpers.py # Fuzzy search
│   └── test_student_tools.py  # Student tools
└── security/                # Security-focused tests
    ├── test_authentication.py    # Token/auth
    ├── test_code_execution.py    # Sandbox safety
    ├── test_dependencies.py      # Dependency audit
    ├── test_ferpa_compliance.py  # Anonymization
    └── test_input_validation.py  # Injection prevention
```

### Test Conventions

- **Framework:** pytest with `pytest-asyncio` for async tests
- **Mocking:** `unittest.mock.AsyncMock` for Canvas API calls
- **Fixtures:** Shared in `conftest.py` (sample data, mock resolvers)
- **Coverage target:** 3+ tests per tool (success, error, edge case)
- **Tool extraction:** `get_tool_function()` helper for FastMCP tools

### Writing New Tests

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from mcp.server.fastmcp import FastMCP

def get_tool_function(mcp_server, tool_name):
    """Extract registered tool function from FastMCP server."""
    tools = mcp_server._tool_manager._tools
    return tools[tool_name].fn

@pytest.mark.asyncio
class TestMyNewTool:
    async def test_success(self, mock_canvas_request, mock_course_id_resolver):
        # Arrange
        mock_canvas_request.return_value = {"id": 1, "name": "Test"}
        mcp = FastMCP("test")
        register_my_tools(mcp)
        tool_fn = get_tool_function(mcp, "my_tool_name")

        # Act
        result = await tool_fn(course_id="12345")

        # Assert
        assert "Test" in result
        mock_canvas_request.assert_called_once()
```

## Code Quality

### Linting and Formatting

```bash
# Lint with ruff
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format with black
black src/ tests/

# Type check with mypy
mypy src/canvas_mcp/
```

### Configuration

- **ruff:** Configured in `pyproject.toml` - E, W, F, I, B, C4, UP rules, 88-char line length
- **black:** 88-char lines, Python 3.10 target
- **mypy:** Strict mode with mandatory type hints (except tests)

## Adding New Tools

### 1. Create Tool Module

```python
# src/canvas_mcp/tools/my_feature.py
from mcp.server.fastmcp import FastMCP
from canvas_mcp.core import (
    make_canvas_request,
    get_course_id,
    validate_params,
    format_response,
    format_header,
)

def register_my_feature_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    @validate_params
    async def my_tool(
        course_id: str,
        limit: int = 10,
        include_details: bool = False,
    ) -> str:
        """Tool description shown in MCP clients."""
        resolved_id = await get_course_id(course_id)
        data = await make_canvas_request(
            f"courses/{resolved_id}/my_endpoint",
            params={"per_page": limit}
        )
        return format_response("My Tool Results", data)
```

### 2. Register in Server

```python
# In server.py register_all_tools():
from canvas_mcp.tools.my_feature import register_my_feature_tools
register_my_feature_tools(mcp)
```

### 3. Export from __init__.py

```python
# In tools/__init__.py
from canvas_mcp.tools.my_feature import register_my_feature_tools
```

### 4. Write Tests (3+ per tool)

```python
# tests/tools/test_my_feature.py
# Success case, error case, edge case minimum
```

## Coding Standards

### Mandatory
- Type hints on all function signatures (return types included)
- `@mcp.tool()` decorator for all MCP tools
- `@validate_params` decorator for parameter validation
- `async def` for all tool functions
- Use `Union[str, None]` or `Optional[str]` for optional params
- `use_form_data=True` for Canvas POST/PUT requiring form encoding
- ISO 8601 dates for Canvas API interactions

### Conventions
- Tool names: `snake_case` matching Canvas concepts
- Parameters: `course_id` (not course), `assignment_id` (not assignment)
- Responses: Use `format_response()` / `format_header()` for token efficiency
- Errors: Return error dict via `format_error()`, never raise exceptions in tools
- Canvas IDs: Accept any format (numeric, code, SIS), resolve via `get_course_id()`

## MCP Client Configuration

### Claude Desktop
```json
{
  "mcpServers": {
    "canvas-api": {
      "command": "/path/to/canvas-mcp/.venv/bin/canvas-mcp-server"
    }
  }
}
```

### Cursor / Windsurf / Continue
Same JSON format in respective config files. Use absolute path to virtualenv binary.

### Zed
```json
{
  "context_servers": {
    "canvas-api": {
      "command": {
        "path": "/path/to/canvas-mcp/.venv/bin/canvas-mcp-server"
      }
    }
  }
}
```
