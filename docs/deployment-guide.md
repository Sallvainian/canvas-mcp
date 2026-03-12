# Canvas MCP - Deployment Guide

**Generated:** 2026-03-12 | **Scan Level:** Exhaustive

---

## Deployment Models

Canvas MCP supports three deployment models:

| Model | Use Case | Startup |
|-------|----------|---------|
| **MCP Client Managed** | Standard use (Claude Desktop, Cursor, etc.) | Client starts server automatically |
| **Manual/Script** | Development, testing | `canvas-mcp-server` or `start_canvas_server.sh` |
| **Docker Container** | Isolated deployment, CI/CD | `docker run` with env vars |

## Local Deployment (Standard)

### Prerequisites
- Python 3.10+ with virtualenv
- Canvas API token and URL

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp env.template .env
# Edit .env with CANVAS_API_TOKEN and CANVAS_API_URL
```

### MCP Client Configuration
Point your MCP client to the virtualenv binary:
```
/absolute/path/to/canvas-mcp/.venv/bin/canvas-mcp-server
```

### Verification
```bash
canvas-mcp-server --test    # Test API connection
canvas-mcp-server --config  # Display configuration
```

## Docker Deployment

### Dockerfile Details

```dockerfile
FROM python:3.12-slim
# Uses uv for fast installs
# Creates non-root user "mcp"
# Health check: python -c "import canvas_mcp; print('OK')"
# Entrypoint: canvas-mcp-server
```

### Build and Run

```bash
# Build image
docker build -t canvas-mcp .

# Run with required env vars
docker run -e CANVAS_API_TOKEN=your_token \
           -e CANVAS_API_URL=https://your-institution.instructure.com \
           canvas-mcp

# Run with full configuration
docker run \
  -e CANVAS_API_TOKEN=your_token \
  -e CANVAS_API_URL=https://your-institution.instructure.com \
  -e ENABLE_DATA_ANONYMIZATION=true \
  -e CANVAS_MCP_USER_TYPE=educator \
  -e CANVAS_MCP_VERBOSITY=COMPACT \
  canvas-mcp
```

### Security Notes
- Runs as non-root user (`mcp`)
- No volume mounts needed for basic operation
- Token passed via environment variable (not baked into image)
- `ENABLE_DATA_ANONYMIZATION` defaults to `false` in container

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Publishing (`publish-mcp.yml`)
**Trigger:** Git tags matching `v*`

```
Tag Push → Build & Test (Python 3.10, uv)
    → pytest suite
    → python -m build
    → Publish to PyPI (OIDC, no tokens)
    → Publish to MCP Registry (github-oidc)
```

**Dependencies:** PyPI Trusted Publisher configured for repository.

#### 2. Security Testing (`security-testing.yml`)
**Trigger:** Push to main/development, PRs to main, weekly (Sunday 00:00)

6 parallel jobs:
1. **Security Tests:** `pytest tests/security/` with coverage
2. **SAST Scan:** Bandit + Semgrep analysis
3. **Dependency Scan:** pip-audit + Safety check
4. **Secret Detection:** detect-secrets + TruffleHog
5. **CodeQL Analysis:** GitHub security-and-quality queries
6. **Security Summary:** Aggregates all results

#### 3. Test Automation (`canvas-mcp-testing.yml`)
**Trigger:** Push to main/development (tools paths), PRs to main

- Python 3.11, pytest with asyncio
- Test report generation (markdown)
- PR comment with results
- Performance regression check (optional)

#### 4. Other Workflows
- **auto-update-docs.yml** - Documentation synchronization
- **claude-code-review.yml** - AI-assisted code review
- **auto-label-issues.yml** - Issue labeling automation
- **weekly-maintenance.yml** - Scheduled dependency/maintenance checks

### MCP Registry Publishing

Server metadata in `server.json`:
```json
{
  "name": "io.github.vishalsachdev/canvas-mcp",
  "version": "1.0.6",
  "transport": "stdio",
  "packageRegistry": {
    "name": "pypi",
    "packageName": "canvas-mcp"
  }
}
```

Validation: `jsonschema -i server.json /tmp/mcp-schema.json`

## Configuration Overlays

Three deployment tiers in `config/overlays/`:

### Baseline (`baseline.env`)
- Sandbox enabled for code execution
- MCP binds localhost only
- Anonymization toggle preserved from user config
- Log redaction enabled

### Public (`public.env`)
Baseline + additional hardening:
- No outbound network from code execution
- Token storage via keyring/envelope (placeholder)
- Log rotation hints

### Enterprise (`enterprise.env`)
Baseline + full enterprise controls:
- Authenticated MCP clients (API key/mTLS placeholders)
- Centralized secret store integration
- Outbound allowlist enforcement
- Audit logging with retention policies
- SIEM/syslog forwarding

### Release Gating by Tier
| Tier | Required Checks |
|------|----------------|
| Baseline | Lint + unit tests |
| Public | + Smoke bundle (dependency, sandbox, token, log redaction) |
| Enterprise | + Full security suite, SAST, dependency + secret scanning, checklist sign-off |

## Environment Configuration Reference

### Required
```bash
CANVAS_API_TOKEN=           # Canvas API access token
CANVAS_API_URL=             # Canvas instance URL (https://...)
```

### Server
```bash
MCP_SERVER_NAME=canvas-mcp  # Server display name
DEBUG=false                 # Debug mode
API_TIMEOUT=30              # HTTP timeout (seconds)
CACHE_TTL=300               # Cache lifetime (seconds)
MAX_CONCURRENT_REQUESTS=10  # Concurrent API limit
```

### Privacy
```bash
ENABLE_DATA_ANONYMIZATION=false  # FERPA anonymization (educators: set true)
ANONYMIZATION_DEBUG=false        # Debug anonymization mapping
```

### Display
```bash
CANVAS_MCP_VERBOSITY=COMPACT    # COMPACT|STANDARD|VERBOSE
CANVAS_MCP_USER_TYPE=all        # all|educator (filters available tools)
```

### Code Execution Sandbox
```bash
ENABLE_TS_SANDBOX=false         # Enable sandboxing
TS_SANDBOX_MODE=auto            # auto|docker|local
TS_SANDBOX_TIMEOUT=120000       # Timeout (ms)
TS_SANDBOX_MEMORY_MB=512        # Memory limit
TS_SANDBOX_CPU_SECONDS=60       # CPU limit
TS_SANDBOX_NETWORK_BLOCK=false  # Block outbound network
TS_SANDBOX_OUTBOUND_ALLOWLIST=  # Allowed domains
TS_SANDBOX_CONTAINER_IMAGE=node:20-alpine
```

### Development
```bash
LOG_LEVEL=INFO                  # Logging level
LOG_API_REQUESTS=false          # Log HTTP requests
INSTITUTION_NAME=               # Institution display name
TIMEZONE=                       # Default timezone
```
