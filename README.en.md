# Kingdee K3Cloud MCP

[English](README.en.md) | [中文](README.md)

[![PyPI version](https://img.shields.io/pypi/v/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml)

MCP Server for Kingdee K3Cloud ERP. Lets AI assistants (Claude Desktop, Claude Code, Cursor, Cline, Cherry Studio, Openclaw, and any MCP-compatible client) query and operate your Kingdee ERP system through natural language.

> **Tip**: Claude Code users can pair this with [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) for a better experience. The Skill injects K3Cloud form field knowledge, common query patterns, and workflow guidance into Claude Code, significantly reducing trial and error.

```
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  kingdee-k3cloud    │───▶│  kingdee-k3cloud    │───▶│  K3Cloud Web API │
│  -skill             │    │  -mcp               │    │  (Kingdee Cloud) │
│  Knowledge / Flows  │    │  Execution / Tools  │    │                  │
└─────────────────────┘    └─────────────────────┘    └──────────────────┘
      Claude Code only            All MCP clients
```

## Features

- **15 MCP tools**: covers query, bulk export, create, submit, audit, unaudit, delete, push-down, and more
- **Universal interface design**: a single `form_id` parameter supports materials, customers, sales orders, purchase orders, and all other forms — no per-form configuration needed
- **Advanced query primitives**: `query_bill_all` (auto-pagination), `query_bill_to_file` (streaming to disk), `query_bill_range` (date sharding) — eliminate the need for manual looping
- **Read-only / read-write modes**: restrict AI to query-only operations to prevent accidental writes
- **Automatic session recovery**: handles session timeouts gracefully during long-running sessions
- **Multiple transport protocols**: stdio (local), SSE, streamable-http (remote / shared)

## Quick Start

### Option 1: Run with uvx (Recommended)

No need to clone the repo — run directly via uvx. **Note**: five required environment variables must be set at startup (`KD_SERVER_URL`, `KD_ACCT_ID`, `KD_USERNAME`, `KD_APP_ID`, `KD_APP_SEC`); the server will exit with an error if any are missing.

**In an MCP client** (recommended — see the "Client Configuration" section below): pass the variables via the client config's `env` field; the `uvx` process reads them automatically.

**For manual testing**, provide the environment variables in one of these ways:

```bash
# Option A: create a .env file in the current directory (loaded automatically on startup)
cp .env.example .env   # fill in real values, then run
uvx kingdee-k3cloud-mcp

# Option B: export temporarily in the shell
export KD_SERVER_URL=https://your-server/k3cloud/
export KD_ACCT_ID=your_acct_id
export KD_USERNAME=your_username
export KD_APP_ID=your_app_id
export KD_APP_SEC=your_app_secret
uvx kingdee-k3cloud-mcp
```

### Option 2: Run from Source

```bash
git clone https://github.com/adamzhang1987/kingdee-k3cloud-mcp.git
cd kingdee-k3cloud-mcp
uv sync
uv run kingdee-k3cloud-mcp
```

## Configuration

Copy the environment variable template and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|----------|-------------|---------|
| `KD_SERVER_URL` | Kingdee server URL (must end with `/k3cloud/`) | `https://your-server/k3cloud/` |
| `KD_ACCT_ID` | Account set ID | `your_acct_id` |
| `KD_USERNAME` | Integration user account | `your_username` |
| `KD_APP_ID` | Application ID | `your_app_id` |
| `KD_APP_SEC` | Application secret | `your_app_secret` |
| `KD_LCID` | Language code (default 2052 = Simplified Chinese) | `2052` |
| `KD_ORG_NUM` | Organization number (optional) | |

> The Application ID and Secret must be obtained from the "Third-party System Login Authorization" section in the Kingdee K3Cloud admin console.

### How to Obtain Credentials

#### 1. Log in to the Kingdee K3Cloud Admin Console

1. Log in with an admin account, navigate to **System Settings → Third-party System Login Authorization**.
2. Click **New** to open the authorization creation page.
3. Click **Get Application ID**, which redirects you to [open.kingdee.com](https://open.kingdee.com/). Click **New Authorization**.
4. Fill in the form with your information and submit.
5. After submission, copy the generated application info back into the K3Cloud console and click **Confirm**.
6. Configure the integration user account.
7. Click **Save**, then click **Generate Test Link** to verify the connection.

> **Note**: the current database center ID (account set ID) can be found in the information shown after generating the test link.

#### 2. KD_SERVER_URL

Format: `https://your-server/k3cloud/`, where `your-server` is the domain or IP of your Kingdee server. Example: `https://erp.company.com/k3cloud/`.

#### 3. KD_ACCT_ID — Account Set ID

#### 4. KD_USERNAME — Integration User Account

Use an account that has the necessary module permissions. **Do not use the admin account.** Create a dedicated integration account with only the required permissions.

#### 5. KD_APP_ID / KD_APP_SEC

> **Note**: the APP_SECRET can be viewed in the application detail at any time; if lost, it can be regenerated via the **Reset** function.

#### 6. Verify Configuration

```bash
cd kingdee-k3cloud-mcp
cp .env.example .env
# fill in the 5 environment variables, then run:
uvx kingdee-k3cloud-mcp
```

If you see "MCP Server running" or similar output, the configuration is correct.

---

Reference: [Kingdee K3Cloud Third-party Integration Configuration Guide](https://vip.kingdee.com/knowledge/specialDetail/229961573895771136?category=229963554177453824&id=298030366575393024&type=Knowledge&productLineId=1&lang=zh-CN)

## Client Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "kingdee-k3cloud": {
      "command": "uvx",
      "args": ["kingdee-k3cloud-mcp"],
      "env": {
        "KD_SERVER_URL": "https://your-server/k3cloud/",
        "KD_ACCT_ID": "your_acct_id",
        "KD_USERNAME": "your_username",
        "KD_APP_ID": "your_app_id",
        "KD_APP_SEC": "your_app_secret",
        "KD_LCID": "2052"
      }
    }
  }
}
```

### Claude Code

Create `.mcp.json` in your project directory:

```json
{
  "mcpServers": {
    "kingdee-k3cloud": {
      "command": "uvx",
      "args": ["kingdee-k3cloud-mcp"],
      "env": {
        "KD_SERVER_URL": "https://your-server/k3cloud/",
        "KD_ACCT_ID": "your_acct_id",
        "KD_USERNAME": "your_username",
        "KD_APP_ID": "your_app_id",
        "KD_APP_SEC": "your_app_secret",
        "KD_LCID": "2052"
      }
    }
  }
}
```

### Cursor / Windsurf and Other MCP Clients

Configuration is similar to Claude Desktop. Refer to your client's MCP documentation and use the same `uvx` command and environment variables.

### SSE Mode (Remote / Shared)

To share a single server instance across multiple users:

```bash
# Start the SSE server (default port 8000)
FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8080 uvx kingdee-k3cloud-mcp --transport sse
```

Client connection URL: `http://your-server:8080/sse`

Enable Bearer Token authentication via the `MCP_API_KEY` environment variable.

## Available Tools

### Query Tools (available in read-only mode)

| Tool | Description |
|------|-------------|
| `query_bill` | Query bill data (returns a 2D array) |
| `query_bill_json` | Query bill data (returns JSON with field names as keys) |
| `count_bill` | Estimate the number of result rows — useful before large queries |
| `query_bill_all` | Auto-paginate until all data is fetched or the safety limit is reached |
| `query_bill_to_file` | Auto-paginate and stream results to a local file (ndjson / csv) — suitable for 10,000+ row exports |
| `query_bill_range` | Auto-shard by date (month / week / day) + paginate — suitable for multi-month / multi-year queries, supports disk output |
| `view_bill` | View complete details of a single record |
| `query_metadata` | Query form field structure (metadata) |

### Write Tools (available in read-write mode)

| Tool | Description |
|------|-------------|
| `save_bill` | Save / create a bill |
| `submit_bill` | Submit a bill for approval |
| `audit_bill` | Audit (approve) a bill |
| `unaudit_bill` | Un-audit (unapprove) a bill |
| `delete_bill` | Delete a draft bill |
| `execute_operation` | Execute a custom operation (disable, un-disable, etc.) |
| `push_bill` | Push down a bill (e.g. sales order → delivery order) |

All tools accept a `form_id` parameter to target any form (materials, customers, suppliers, sales orders, purchase orders, etc.).

## Read-Only Mode

Use `--mode readonly` or `MCP_MODE=readonly` to restrict the server to the 8 query tools, preventing accidental AI writes.

```json
"args": ["kingdee-k3cloud-mcp", "--mode", "readonly"]
```

Or:

```json
"env": {
  "MCP_MODE": "readonly",
  ...
}
```

## Debugging

Use the MCP Inspector visual debugging tool:

```bash
uvx mcp dev src/kingdee_k3cloud_mcp/server.py
```

## Architecture

```
AI Assistant (Claude Desktop / Claude Code / Cursor / Cline / Openclaw, etc.)
        │  MCP Protocol
        ▼
kingdee-k3cloud-mcp (this project)
        │  Kingdee Web API SDK
        ▼
Kingdee K3Cloud
```

This project uses the official Kingdee Python SDK ([kingdee-cdp-webapi-sdk](https://pypi.org/project/kingdee-cdp-webapi-sdk/)) to communicate with the K3Cloud API, and wraps it as standard MCP tools via [FastMCP](https://github.com/modelcontextprotocol/python-sdk).

## Companion Skill (Claude Code Users)

[kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) is a companion Skill for Claude Code that provides:

- Common form ID quick-reference (BD_MATERIAL, SAL_SaleOrder, etc.)
- Verified field name lists (avoid 500 errors from incorrect field names)
- Complete workflows for daily reports, customer queries, sales analysis, inventory analysis, order tracking, and more

Once installed, Claude Code automatically knows the correct way to query Kingdee ERP without repeated trial and error.

## Development

```bash
git clone https://github.com/adamzhang1987/kingdee-k3cloud-mcp.git
cd kingdee-k3cloud-mcp
uv sync --dev

make test    # run tests with coverage report
make lint    # ruff check + mypy
make format  # ruff format + fix
make build   # uv build + twine check
```

Install pre-commit hooks (optional, mirrors CI):

```bash
uv run pre-commit install
```

## Contributors

<a href="https://github.com/adamzhang1987/kingdee-k3cloud-mcp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=adamzhang1987/kingdee-k3cloud-mcp" alt="Contributors" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## License

Apache License 2.0 — see [LICENSE](LICENSE)
