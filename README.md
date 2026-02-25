# jdyxk-mcp-server

MCP server that exposes 金蝶云星空 (Kingdee K3 Cloud) Web API so AI assistants (e.g. Claude Desktop) can query and operate ERP data via natural language.

## What’s in this repo

| Path | Description |
|------|-------------|
| **`jdyxk-mcp-server/`** | The MCP server (Python, uv). **Run and configure from here.** |
| `SDK_Python3.0_V8.2.0/` | Official Kingdee SDK and demos (reference only) |

## Quick start

1. **Go into the server directory and install:**

   ```bash
   cd jdyxk-mcp-server
   uv sync
   ```

2. **Configure:** copy `jdyxk-mcp-server/.env.example` to `jdyxk-mcp-server/.env` and set `KD_SERVER_URL`, `KD_ACCT_ID`, `KD_USERNAME`, `KD_APP_ID`, `KD_APP_SEC`.

3. **Run:** from `jdyxk-mcp-server/` run `uv run server.py` (stdio). Point your MCP client at this directory and command.

Full setup, client config (Claude Desktop / Claude Code), and tool list are in **[jdyxk-mcp-server/README.md](jdyxk-mcp-server/README.md)**.
