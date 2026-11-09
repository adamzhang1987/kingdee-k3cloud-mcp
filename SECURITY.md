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
- **Read-only mode** (`--mode readonly` or `MCP_MODE=readonly`) disables ERP write operations. Query tools can still create restricted export files as described below.

## File Export Boundary (1.4.2+)

`query_bill_to_file` and `query_bill_range` accept only plain filenames in
`output_path`. Absolute paths, subdirectories, traversal, and Windows special
filenames are rejected. Files are created exclusively: existing files, hard links,
and symbolic links (including dangling links) cannot be overwritten or followed.

The operator may set `KD_EXPORT_DIR` to an existing writable absolute directory.
Invalid configuration fails startup. Without it, each instance creates a private
directory inside the system temporary directory (POSIX mode `0700`; new exports
`0600`). Exports remain after exit and may later be removed by OS temporary-file
cleanup. Use the returned absolute `path` to locate an export.

Configured directories and their parents must be managed by trusted operators and
dedicated to exports. This boundary limits MCP callers; it does not defend against
local processes running with the server account's privileges. Remote clients still
require connection authentication and share the instance's export directory.

Issue #47 concerns arbitrary file creation/overwrite/truncation, rather than file
reading: the vulnerable implementation in 1.4.1 and earlier opened caller-controlled paths in write
mode. When upgrading, configure the old export directory as `KD_EXPORT_DIR` and
pass only the filename instead of an absolute path. Read-only mode also applies
this export boundary, rather than disabling exports entirely.
