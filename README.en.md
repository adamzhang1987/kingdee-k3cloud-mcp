# Kingdee K3Cloud MCP

[English](README.en.md) | [中文](README.md)

[![PyPI version](https://img.shields.io/pypi/v/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![Downloads](https://img.shields.io/pypi/dm/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml)

MCP Server for Kingdee K3Cloud ERP. Lets AI assistants (Claude Desktop, Claude Code, Cursor, Windsurf, Cline, Continue, Cherry Studio, and any MCP-compatible client) query and operate your Kingdee ERP system through natural language. A standard PyPI package — `pip install` or `uvx` both work out of the box, with no dependency on a specific package manager.

> **Tip**: Connect through an MCP-capable agent platform like [Openclaw](https://docs.openclaw.ai/) to query stock levels or bills via natural language directly from the IM channels it supports (e.g. WeChat, Telegram) — no need to open the K3Cloud web UI. Agents that support the Skill mechanism (Claude Code, Openclaw, etc.) can additionally pair this with [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) for a better experience — the Skill injects K3Cloud form field knowledge, common query patterns, and workflow guidance, significantly reducing trial and error — but it's **not required**: the MCP server works standalone with the full tool set on any MCP client.

```
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  kingdee-k3cloud    │───▶│  kingdee-k3cloud    │───▶│  K3Cloud Web API │
│  -skill             │    │  -mcp               │    │  (Kingdee Cloud) │
│  Knowledge / Flows  │    │  Execution / Tools  │    │                  │
└─────────────────────┘    └─────────────────────┘    └──────────────────┘
      Skill-capable agents        All MCP clients
```

## Features

- **15 MCP tools**: covers query, bulk export, create, submit, audit, unaudit, delete, push-down, and more
- **Universal interface design**: a single `form_id` parameter supports materials, customers, sales orders, purchase orders, and all other forms — no per-form configuration needed
- **Advanced query primitives**: `query_bill_all` (auto-pagination), `query_bill_to_file` (streaming to disk), `query_bill_range` (date sharding) — eliminate the need for manual looping
- **Read-only / read-write modes**: restrict AI to query-only operations to prevent accidental writes
- **Authentication diagnostics**: credentials are verified at startup, and auth/authorization misconfiguration returns actionable remediation instead of Kingdee's misleading "session lost" message
- **Multiple transport protocols**: stdio (local), SSE, streamable-http (remote / shared)
- **Standard Python package**: install with `pip install`, requires only Python 3.10+, no mandatory package manager
- **Type-safe argument validation**: every tool's parameters are type-annotated and validated at call time by FastMCP's automatic Pydantic runtime validation — malformed input is rejected before it ever reaches the K3Cloud API

## 5-Minute Quick Start

1. Install: `pip install kingdee-k3cloud-mcp` (or run without installing via `uvx kingdee-k3cloud-mcp`)
2. Request an app ID/secret under "Third-party System Login Authorization" in K3Cloud, and get the 5 required environment variables (see [Configuration](#configuration) below)
3. Add them to your MCP client config (see [Client Configuration](#client-configuration) below) and restart
4. Start asking in natural language, e.g.:
   - "Show me last week's audited sales orders, sorted by amount"
   - "What's the current stock of material XX across all warehouses?"
   - "Export all March sales outbound bills to CSV"

## Quick Start

### Option 1: pip install (Recommended, no uv required)

```bash
pip install kingdee-k3cloud-mcp
kingdee-k3cloud-mcp
```

A standard PyPI package requiring only Python 3.10+ — no dependency on `uv`. **Note**: five required environment variables must be set at startup (`KD_SERVER_URL`, `KD_ACCT_ID`, `KD_USERNAME`, `KD_APP_ID`, `KD_APP_SEC`); the server will exit with an error if any are missing.

**In an MCP client** (recommended — see the "Client Configuration" section below): pass the variables via the client config's `env` field.

**For manual testing**, provide the environment variables in one of these ways:

```bash
# Option A: create a .env file in the current directory (loaded automatically on startup)
cp .env.example .env   # fill in real values, then run
kingdee-k3cloud-mcp

# Option B: export temporarily in the shell
export KD_SERVER_URL=https://your-server/k3cloud/
export KD_ACCT_ID=your_acct_id
export KD_USERNAME=your_username
export KD_APP_ID=your_app_id
export KD_APP_SEC=your_app_secret
kingdee-k3cloud-mcp
```

### Option 2: Run with uvx (no install step)

No `pip install` needed — `uvx` creates an isolated environment and runs it automatically. Usage is identical to above; just swap `kingdee-k3cloud-mcp` for `uvx kingdee-k3cloud-mcp`:

```bash
cp .env.example .env
uvx kingdee-k3cloud-mcp
```

### Option 3: Run from Source

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

All configs below use `"command": "uvx"` to run without installing; if you've already run `pip install kingdee-k3cloud-mcp`, change `"command": "uvx"` to `"command": "kingdee-k3cloud-mcp"` and drop the package name from `"args"` (keep other flags like `--mode readonly`) — both are equivalent.

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

### Cursor / Windsurf

Cursor: `Settings → MCP → Add new MCP Server`; Windsurf: edit `~/.codeium/windsurf/mcp_config.json`. Both use the same format as Claude Desktop:

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

### Cline / Continue / Cherry Studio and Other MCP Clients

Same `command` + `args` + `env` structure as above — use `uvx kingdee-k3cloud-mcp` and the same 5 environment variables. Where to put it varies by client:

- Cline (VS Code extension): MCP Servers panel → Configure MCP Servers
- Continue: the `mcpServers` field in `~/.continue/config.json`
- Cherry Studio: Settings → MCP Servers → Add Server

### Openclaw (IM / mobile access)

[Openclaw](https://docs.openclaw.ai/) is a Skill-capable agent platform that can connect this MCP server to the IM channels it supports (e.g. WeChat, Telegram) — ask a question, get your K3Cloud stock or bill data back. Configuration is the same standard MCP server declaration (`command`/`args`/`env`); see the [Openclaw docs](https://docs.openclaw.ai/) for setup steps. Pairing it with [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) further reduces field-name trial and error. Which IM channels are supported is determined by the Openclaw platform.

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

## Data Permissions

The MCP server itself **does not implement** a data-permission model — it connects to K3Cloud via third-party app authorization, using a fixed identity built from `KD_ACCT_ID` (account set) + `KD_USERNAME` (integration user) + `KD_ORG_NUM` (org, default `0`) in `.env`. Every tool call shares this one identity; there's no per-request user switching. As a result, **what the AI can see is entirely determined by this integration user's permission configuration inside K3Cloud.**

### Configure it in K3Cloud

1. Use a dedicated integration user (see "not recommended to use an admin account" above), go to System Management → User Management → User Authorization
2. Assign **function permissions**: which forms (e.g. `SAL_SaleOrder`) and operations (query/create/submit/audit) are allowed
3. Assign **data permissions**: accessible org scope, data rules (filter by customer/department/salesperson, etc.), field-level permissions
4. To pin queries to a single org by default, set `KD_ORG_NUM`

### Two supplementary gates on the MCP side

These *complement* K3Cloud-side permissions — they don't replace them:

- `--mode readonly` / `MCP_MODE=readonly`: globally disables all write tools
- `MCP_API_KEY`: connection auth for SSE / streamable-http transports (not applicable to stdio)

### Troubleshooting: two symptoms of permission issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| 500 error, message passed through verbatim | Insufficient function permission | Grant the integration user the missing form/operation permission in K3Cloud |
| Query succeeds but returns fewer rows or none, **no error** | Data rule filtering applied **silently** | Log in to the K3Cloud web UI with the same integration user and run the same query to compare row counts |

⚠️ The second case is easy to mistake for "there's genuinely no data in this period" — `count_bill` / `query_bill*` return results *after* permission filtering, and can't tell you whether it's "no data" or "filtered out."

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

## When Is This a Good Fit?

There's more than one way to integrate AI with Kingdee ERP, and different approaches optimize for different things. This project tends to fit best when:

- **You need a long-running, production-grade AI agent**: `--mode readonly` provides a read-only boundary; credentials are checked at startup so misconfiguration shows up in the startup log rather than on the first tool call; and authentication failures come back with a precise diagnosis instead of a misleading message, so troubleshooting isn't guesswork
- **You're querying or exporting large volumes of data**: `query_bill_all` (auto-pagination), `query_bill_to_file` (streaming to disk), and `query_bill_range` (date sharding) are purpose-built for tens-of-thousands-of-rows workloads, so the model doesn't have to hand-roll pagination loops
- **Your K3Cloud deployment has custom fields or customizations**: the `query_metadata` tool lets the AI discover a form's actual field structure at query time instead of relying on a fixed field list; pairing it with [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) lets you encode your own custom forms, fields, and approval flows as reusable knowledge
- **You need multiple access paths to coexist**: the same server supports stdio (local IDE), SSE, and streamable-http (remote/shared deployment), and can also be wired into IM channels as an Openclaw tool

If what you want is a quick personal trial and a working first query within minutes, this project supports that too — `pip install` gets you running immediately. Which approach to pick mostly comes down to whether you value "works the moment you install it" or "runs reliably in production over the long haul."

## Why MCP Instead of Direct API Calls?

Having an AI construct raw HTTP requests to your ERP through a Skill is technically feasible, but it introduces a class of security problems that MCP's process-isolation model eliminates at the architectural level.

### Credentials never enter the LLM context

The MCP server runs as a separate process. Secrets (`KD_APP_SEC`, server URL, account set ID) are injected via environment variables — **the model never sees them**. A skill-only approach requires credentials to appear in the prompt or conversation context, where they can leak through exported logs, screenshots, or accidental model output.

### Hard enforcement, not prompt-level suggestions

A Skill is a suggestion — the model may misinterpret it or be steered around it by a crafted input. `--mode readonly` on the MCP server is a **physical constraint**: write tools simply don't exist in the tool list, so the model cannot invoke them no matter what. This is the difference between "I told the intern not to delete records" and "the intern doesn't have DELETE permission."

### Network isolation

The MCP server runs inside the corporate network (or on localhost) with direct access to the ERP. The LLM runs in the cloud and **never touches the internal network**. With stdio transport, all ERP traffic flows between local processes and never traverses an external network.

### A complete audit trail

Every tool call passes through the MCP server, where you can log the operation type, parameters, timestamp, and caller identity in one place. With direct API calls from a Skill, every ERP request the AI makes is invisible to your security team.

### Principle of least privilege

The integration user (`KD_USERNAME`) can be scoped to specific modules and read-only access within Kingdee's own permission system. The MCP server inherits and propagates those limits automatically — the LLM doesn't need to know the boundaries exist; they're just enforced.

### Author's perspective

Treating the LLM as an **untrusted external caller** — not a trusted internal system — is the right zero-trust design posture. The MCP layer makes the separation of concerns clean: the Skill owns *policy* (when and how to use tools), the MCP server owns *mechanism* (what is physically possible). Even if a future model becomes more capable, or a prompt-injection attack succeeds, the blast radius is bounded by the MCP server's permission model — not by the model's compliance with instructions.

---

## Companion Skill (Skill-Capable Agents)

[kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) is a companion Skill for any Skill-capable agent (Claude Code, openclaw, hermes, etc.) that provides:

- Common form ID quick-reference (BD_MATERIAL, SAL_SaleOrder, etc.)
- Verified field name lists (avoid 500 errors from incorrect field names)
- Complete workflows for daily reports, customer queries, sales analysis, inventory analysis, order tracking, and more

Once installed, the agent automatically knows the correct way to query Kingdee ERP without repeated trial and error.

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
