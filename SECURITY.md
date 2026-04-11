# Security Policy

## Reporting a Vulnerability

Please **do not** report security vulnerabilities through public GitHub issues.

Instead, email **adamzhang1987@gmail.com** with:
- A description of the vulnerability
- Steps to reproduce
- Potential impact

You should receive a response within 48 hours. If you don't, please follow up to ensure the original message was received.

## Scope

This project is a local MCP server that relays requests to your own Kingdee K3Cloud instance. Key security considerations:

- **Credentials are never stored by this project** — they are passed via environment variables only
- **SSE/streamable-http mode** exposes an HTTP server; use `MCP_API_KEY` to enable Bearer Token authentication in production
- **Read-only mode** (`--mode readonly` or `MCP_MODE=readonly`) limits the server to query-only tools, reducing the blast radius of AI mistakes
