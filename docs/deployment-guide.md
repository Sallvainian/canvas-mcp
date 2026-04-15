# Deployment Guide

**Project:** canvas-mcp · **Version:** 1.0.6
**Generated:** 2026-04-14 (full rescan, exhaustive)

---

## Deployment Options

| Mode | Audience | Command |
|------|----------|---------|
| Local CLI (pip install) | End users with local MCP clients | `canvas-mcp-server` (after `pip install canvas-mcp`) |
| Docker container | Server deployments, CI, shared hosts | `docker run -e CANVAS_API_TOKEN=… -e CANVAS_API_URL=… canvas-mcp` |
| Legacy shell wrapper | Existing `.env`-based setups | `./start_canvas_server.sh` |

All three produce the same FastMCP process with stdio transport. Choose based on where the client that consumes it runs.

---

## PyPI Installation (End-user deploy)

The package is published to PyPI as [`canvas-mcp`](https://pypi.org/project/canvas-mcp/).

```bash
# With uv (recommended)
uv pip install canvas-mcp

# With pip
pip install canvas-mcp
```

After install, `canvas-mcp-server` is on your PATH. Configure your MCP client to launch it (stdio transport).

### Example: Claude Desktop config

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent on Windows/Linux:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "canvas-mcp-server",
      "env": {
        "CANVAS_API_TOKEN": "<your token>",
        "CANVAS_API_URL": "https://canvas.example.edu/api/v1",
        "CANVAS_MCP_USER_TYPE": "educator"
      }
    }
  }
}
```

---

## Docker Deployment

### Image description

`Dockerfile` builds on `python:3.12-slim`:

1. `pip install uv`
2. Copies `pyproject.toml`, `LICENSE`, `README.md`, `env.template`, `src/`
3. `uv pip install --system --no-cache -e .` (installs canvas-mcp in editable mode)
4. Creates non-root user `mcp`, `chown -R mcp:mcp /app`
5. Sets env defaults:
   - `MCP_SERVER_NAME=canvas-mcp`
   - `ENABLE_DATA_ANONYMIZATION=false`
   - `ANONYMIZATION_DEBUG=false`
6. `USER mcp`
7. `HEALTHCHECK`: `python -c "import canvas_mcp; print('OK')"` every 30s, 3 retries
8. `CMD ["canvas-mcp-server"]`

### Build + run

```bash
docker build -t canvas-mcp:local .

docker run --rm -it \
  -e CANVAS_API_TOKEN=<token> \
  -e CANVAS_API_URL=https://canvas.example.edu/api/v1 \
  -e CANVAS_MCP_USER_TYPE=educator \
  -e ENABLE_DATA_ANONYMIZATION=true \
  canvas-mcp:local
```

For stdio transport you'll typically run this behind an MCP client launcher that spawns the container.

---

## Environment Variables

Full schema in [`env.template`](../env.template). Minimal production surface:

### Required
- `CANVAS_API_TOKEN` — Canvas personal access token
- `CANVAS_API_URL` — Full URL with `/api/v1`

### Recommended for production
- `CANVAS_MCP_USER_TYPE` — set to `educator` or `student` to lock down the surface (default `all`)
- `ENABLE_DATA_ANONYMIZATION=true` — required for FERPA workflows
- `LOG_LEVEL=INFO`, `LOG_API_REQUESTS=false`, `DEBUG=false`

### Sandbox (if enabling `execute_typescript`)
- `ENABLE_TS_SANDBOX=true`
- `TS_SANDBOX_MODE=container` (prefer container for untrusted code)
- `TS_SANDBOX_CONTAINER_IMAGE=node:20-alpine` (default)
- `TS_SANDBOX_BLOCK_OUTBOUND_NETWORK=true` (with allowlist)
- `TS_SANDBOX_ALLOWLIST_HOSTS=canvas.example.edu`
- `TS_SANDBOX_CPU_LIMIT=1000` (millicpus — container mode only)
- `TS_SANDBOX_MEMORY_LIMIT_MB=512`
- `TS_SANDBOX_TIMEOUT_SEC=60`

### Config overlays

`config/overlays/{baseline,public,enterprise}.env` provide layered presets:

```bash
source config/overlays/enterprise.env    # before starting
canvas-mcp-server
```

---

## MCP Registry Publication

The project publishes to the Model Context Protocol registry under `io.github.vishalsachdev/canvas-mcp`.

Registry metadata lives in [`server.json`](../server.json):

- `transport.type`: `stdio`
- `packages[0]`:
  - `registryType`: `pypi`
  - `identifier`: `canvas-mcp`
  - `version`: `1.0.6`
  - `transport.python.module`: `canvas_mcp.server`
- `configuration.env`:
  - `CANVAS_API_TOKEN` (required)
  - `CANVAS_API_URL` (required)
  - `ENABLE_DATA_ANONYMIZATION` (default `false`)
  - `ANONYMIZATION_DEBUG` (default `false`)

Registry entry: <https://static.modelcontextprotocol.io/…>.

---

## Release Process

### 1. Prepare release

```bash
# Bump version in pyproject.toml AND src/canvas_mcp/__init__.py AND server.json
# Update README/CHANGELOG if applicable
git add pyproject.toml src/canvas_mcp/__init__.py server.json
git commit -m "chore: bump version to vX.Y.Z"
git push
```

### 2. Tag

```bash
git tag vX.Y.Z
git push --tags
```

### 3. `publish-mcp.yml` runs automatically on `v*` tag

Steps (from `.github/workflows/publish-mcp.yml`):

1. Set up Python 3.12
2. `pip install uv` → `uv pip install --system -e .`
3. `uv pip install --system pytest pytest-asyncio` → `pytest tests/` (non-blocking if no tests)
4. `uv pip install --system build` → `python -m build`
5. **Publish to PyPI** via `pypa/gh-action-pypi-publish@release/v1` with `skip-existing: true`
6. **Install MCP Publisher** + push `server.json` to the MCP Registry (uses OIDC id-token)

### 4. Verify

- <https://pypi.org/project/canvas-mcp/> shows the new version
- Registry search finds the new version
- Test install in a clean venv: `uv pip install canvas-mcp==X.Y.Z && canvas-mcp-server --config`

---

## CI/CD Pipelines

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `canvas-mcp-testing.yml` | push/PR to main,development · paths: `src/canvas_mcp/tools/discussions.py` or `tests/**` | Narrow pytest smoke |
| `security-testing.yml` | push/PR + Sunday cron | `pytest tests/security/ --cov=src/canvas_mcp`; uploads coverage artifact |
| `publish-mcp.yml` | tag `v*` | PyPI + MCP Registry publish |
| `auto-update-docs.yml` | PR touching `src/canvas_mcp/tools/**` or `server.py` | Claude Code Action pushes doc updates |
| `auto-claude-review.yml` | PR `opened` | Posts `@claude` comment to trigger review |
| `claude-code-review.yml` | PR events | Claude PR review |
| `claude.yml` | `@claude` mentions (issue/PR comment, review) | Claude Code responder |
| `auto-label-issues.yml` | issue opened | Claude issue triage + labels |
| `weekly-maintenance.yml` | Sunday 00:00 UTC + manual | Maintenance tasks |

All workflows use **Python 3.12**. Publishing uses `uv`.

---

## Infrastructure Requirements

- **Compute:** One process per MCP client session. stdio transport → no listening ports. Memory footprint typically <150 MB RSS idle; scales with cache size + concurrent HTTP requests (`MAX_CONCURRENT_REQUESTS` default 10).
- **Network:** Outbound HTTPS to `CANVAS_API_URL` only. If using container sandbox, additionally Docker/Podman socket.
- **Storage:** No persistent storage required. All state is in-process. Logs to stderr.
- **Secrets:** `CANVAS_API_TOKEN` must be supplied via env; **never commit to git**. Use your platform's secret manager (systemd credentials, Docker secrets, Kubernetes Secret, etc.).

---

## Health Check / Smoke Tests

```bash
# 1. Connectivity — calls GET /users/self
canvas-mcp-server --test
# Expected: ✓ Successfully connected as <your name>

# 2. Config — print resolved env (tokens redacted)
canvas-mcp-server --config

# 3. Import sanity (used in Dockerfile HEALTHCHECK)
python -c "import canvas_mcp; print('OK')"

# 4. Inside container
docker exec -it <container> python -c "import canvas_mcp; print('OK')"
```

---

## Rollback

If a release breaks production:

```bash
# End users
uv pip install canvas-mcp==<previous-version>

# Registry
# Previous versions remain available; point clients at the older version in server.json
```

PyPI publishes are immutable (you cannot overwrite `X.Y.Z`); publish `X.Y.Z+1` with a fix rather than trying to yank.

---

## Security Considerations for Production

- **Token scope** — Prefer tokens tied to a non-human service account with only the permissions your tools need. Treat every MCP session as acting on behalf of that account's Canvas identity.
- **`ENABLE_DATA_ANONYMIZATION=true`** is the default recommended stance when distributing responses outside the educator's own LLM session.
- **`CANVAS_MCP_USER_TYPE`** — set explicitly in prod to `educator` or `student` rather than the default `all`, which includes developer tools like `execute_typescript`.
- **TS sandbox** — If enabling `execute_typescript`, prefer `TS_SANDBOX_MODE=container` over `local` for untrusted code. `local` runs in-process with limited isolation.
- **Logs** — `LOG_API_REQUESTS=false` by default; keep it false in prod to avoid writing URLs with query-param tokens. `tests/security/test_authentication.py` verifies tokens never leak into error messages.
- **Weekly scan** — `security-testing.yml` + `weekly-maintenance.yml` run `pip-audit` for CVE detection (`tests/security/test_dependencies.py`).

See [SECURITY.md](../SECURITY.md) and [SECURITY_IMPLEMENTATION_GUIDE.md](../SECURITY_IMPLEMENTATION_GUIDE.md).
