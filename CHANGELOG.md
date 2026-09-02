# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-09-02

### Removed
- **删除整套会话恢复机制**（`RetryableK3CloudApiSdk`）。三轮实证测试（约 230 次只读请求，
  记录见 `docs/session-auth-experiments.md`）证明它针对的是一个**不存在的故障模式**：
  - 新 SID **不需要**「激活时间」，`_RESET_COOLDOWN = 300` 所依据的假设已被证伪；
  - SID 陈旧、无效或为空时请求**本就会成功**——服务端静默换发新 SID；
  - 真正会触发「会话信息已丢失」的是**认证失败**，而清 SID 重试不可能修复凭据错误。
  连带移除了「为取新 SID 而重放原始请求」的行为——写操作（`save_bill` / `audit_bill` /
  `delete_bill` / `push_bill` 等）**不再有第二次请求**，消除了重复提单的不确定性。

### Changed
- **`RetryableK3CloudApiSdk` → `DiagnosticK3CloudApiSdk`**：只标注认证失败，从不重试。
- **认证失败的返回形态**：不再原样透传金蝶那句误导的「会话信息已丢失，请重新登录」，
  改为返回带可操作诊断的 envelope：

  ```json
  {"error": "authentication_failed", "message": "...", "hint": "...", "original": {...}}
  ```

  `hint` 给出正确的修复顺序（先核对 `KD_USERNAME` / `KD_APP_ID` / `KD_APP_SEC` / `KD_LCID`
  与金蝶端第三方登录授权是否一致，改正后再重启使 `.env` 生效），并说明重试无效、
  以及在改正配置之前重启只会让问题从偶发变成持续。
- **检测判据改为 `MsgCode == 1`**，不再依赖单一中文子串。实测 14 次认证失败全部为 1，
  而业务错误分别为 4 / 9 / 8，判据不会误伤。消息串仅在 `MsgCode` 缺失（或为 `null`）时兜底——
  响应里有显式错误码时以错误码为准，业务错误即使消息中带上「会话信息已丢失」也不会被误判。

### Added
- **启动时凭据自检**：`setup()` 后发一次最轻量的只读查询，凭据错误立即在启动日志中告警，
  不必等到第一次工具调用。**只告警、不阻断启动**，可用 `KD_STARTUP_CHECK=0` 关闭。
  自检跑在 `mcp.run()` 之前，因此带独立的超时上界：`KD_STARTUP_CHECK_TIMEOUT`（默认 5 秒，
  连接与读取各自计时），结束后无条件还原 SDK 原本的 120 秒超时——业务请求不受影响。
  没有这个上界时，金蝶不可达会让启动阻塞到分钟级，进而拖垮 MCP 握手。
- `KD_STARTUP_CHECK` / `KD_STARTUP_CHECK_TIMEOUT` 已补入 README 环境变量表与 `.env.example`。
- `docs/session-auth-experiments.md`：三轮实证测试的完整流程、探针方法论与复现指南。

### Fixed
- `_check_expired`（现 `_check_auth_failure`）的三条未捕获 `AttributeError` 崩溃路径：
  `ResponseStatus` 为 `null`、`Result` 是数组、`Errors` 元素是字符串时会直接抛异常。
- 顶层 `ResponseStatus`（不在 `Result` 下）的响应形态此前会漏检。
- 删除一条**恒真的无效断言**（原 `test_expired_outside_cooldown_updates_reset_timestamp`：
  `time.monotonic` 被冻结，断言退化为 `1000.0 >= 1000.0`，实现怎么写都会通过）。

## [1.3.2] - 2026-05-29

### Fixed
- **分页 Bug**：`query_bill` / `query_bill_json` 在 `start_row > 0` 时 `TopRowCount` 未随偏移量增加，导致请求窗口落在结果集之外，翻页返回空数据。修复方式：将 `TopRowCount` 改为 `start_row + top_count`，`Limit` 改为 `top_count`（`top_count > 0` 时）。
- **自动翻页 Bug**：`_paginate_bill`（`query_bill_all` / `query_bill_range`）和 `_stream_to_file_handle`（`query_bill_to_file`）内部翻页循环同样受此影响，第二页起 `TopRowCount` 固定为 `page_size` 而非 `current_start + page_size`，导致翻页后返回空。已同步修复。
- 更新 `_wrap_query_result` 的 hint 文案，去掉误导性的"缩小时间范围"提示，明确引导用户用 `next_start_row` 继续翻页。

## [1.3.1] - 2026-04-14

### Changed
- PyPI keywords 补充 `mcp-server`、`金蝶`、`claude`，提升在 PyPI 和目录搜索中的可发现性

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

[Unreleased]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.3.2...v1.4.0
[1.3.2]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/adamzhang1987/kingdee-k3cloud-mcp/releases/tag/v1.0.0
