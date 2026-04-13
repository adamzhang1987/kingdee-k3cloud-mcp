# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-04-13

### Changed
- 版本号与 `kingdee-k3cloud-skill` 对齐至 `1.3.0`，便于用户按版本号配套使用两个 repo。无功能变更。

## [1.2.0] - 2026-04-13

### Added
- **`query_bill_all(form_id, field_keys, filter_string, order_string, max_rows, page_size)`**：服务端自动翻页，无需模型手动循环。拉完所有数据后返回 `{rows, row_count, exhausted}`；达到 `max_rows` 安全上限时提前截断并返回 `next_start_row`。
- **`query_bill_to_file(form_id, field_keys, filter_string, output_path, format, page_size, max_rows)`**：流式落盘，不在内存中累积数据，适合万行以上的大批量导出。支持 `ndjson`（每行一个 JSON 对象）和 `csv` 格式；返回 `{path, row_count, bytes, format}`。
- **`query_bill_range(form_id, field_keys, date_field, date_from, date_to, extra_filter, chunk, output_path, page_size)`**：日期自动分片 + 翻页包装器，将 `[date_from, date_to)` 按 `month/week/day` 切成 N 段依次查询。`output_path` 为空时内联合并返回（受 1 MB MCP 限制）；非空时流式落盘，返回 `{path, row_count, bytes, chunks, format}`。适合跨年查询。

## [1.1.0] - 2026-04-13

### Added
- **`count_bill(form_id, filter_string)`**：新增行数探测工具，仅查询主键字段估算结果行数，不返回数据内容。返回 `{estimated_rows, is_exact, hint}`，适合大批量查询前的预判。`is_exact=false` 表示实际行数 ≥ 5000。
- **分页截断元数据**：`query_bill` 和 `query_bill_json` 的返回结果现在包装为 envelope 格式：`{rows, row_count, truncated, next_start_row?, hint?}`。当返回行数达到 `min(top_count, limit)` 上限时，`truncated=true` 并提供 `next_start_row` 以便连续翻页，解决了原先"返回 2000 行但无截断信号"导致模型误判数据完整的问题。

## [1.0.0] - 2026-04-12

### Added

**Core MCP tools (11 total)**

| Tool | Type | Description |
|------|------|-------------|
| `query_bill` | query | 按字段键列表查询单据，支持过滤、排序、分页 |
| `query_bill_json` | query | 查询单据并返回完整 JSON 字段（适合字段名未知时探索） |
| `view_bill` | query | 按单据 ID 或单号查询单条完整单据 |
| `query_metadata` | query | 查询表单元数据与字段定义 |
| `query_by_number` | query | 批量按单号查询单据 |
| `query_business_info` | query | 查询扩展业务数据视图 |
| `save_bill` | write | 新建或更新单据 |
| `submit_bill` | write | 提交单据审批 |
| `audit_bill` | write | 审核通过单据 |
| `unaudit_bill` | write | 撤销单据审核 |
| `delete_bill` | write | 删除草稿单据 |
| `execute_operation` | write | 调用金蝶 K/3 Cloud 任意业务操作 |
| `push_bill` | write | 单据下推，将源单转换为下游单据类型 |

**Transport & auth**
- Three transport protocols: `stdio` (default), `SSE`, `streamable-http`
- Optional Bearer-token authentication via `MCP_API_KEY` env var (SSE / streamable-http only); stdio mode is unaffected
- `--mode readonly` flag (and `MCP_MODE=readonly` env var) to expose only the 4 query tools — safe for read-only deployments

**Session management**
- `RetryableK3CloudApiSdk`: automatic session recovery when K/3 Cloud returns "会话信息已丢失"
- Fire-and-forget SID reset: on expiry, clears stale `cookiesStore` and makes one call to establish a fresh SID; returns the error immediately instead of blocking
- 300-second cooldown prevents back-to-back resets from destroying a newly-issued SID before it activates server-side
- Unicode-escaped session expiry messages correctly detected (`\u4f1a\u8bdd...`)
- `hasattr` guard on `cookiesStore` reset for forward-compatibility with future SDK versions

**Package & tooling**
- Proper `src/` layout, fully PEP 621 compliant `pyproject.toml`
- Dependency upper bounds: `kingdee-cdp-webapi-sdk>=8.2.0,<9`, `mcp>=1.26.0,<2`, `python-dotenv>=1.2.1,<2`
- `py.typed` marker for downstream `mypy` support
- Apache 2.0 license
- GitHub Actions CI matrix (Python 3.10 / 3.11 / 3.12)
- GitHub Actions release workflow with PyPI Trusted Publishing (OIDC)

[1.3.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/releases/tag/v1.0.0
