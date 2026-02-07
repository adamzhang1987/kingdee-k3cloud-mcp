# jdyxk-mcp-server

金蝶云星空 K3Cloud MCP Server — 通过 MCP 协议暴露金蝶 Web API，供 AI 助手调用。

## 关键文件

- `server.py` — MCP Server 主文件，包含 9 个工具和 SDK 初始化
- `pyproject.toml` — 项目依赖配置
- `.env.example` — 环境变量模板
- `../DESIGN.md` — 设计决策文档

## 金蝶 SDK 技术注意事项

- **构造函数**: `K3CloudApiSdk(server_url)` — `server_url` 为必传参数
- **InitConfig 参数名**: `app_secret`（不是 `app_sec`），环境变量 `KD_APP_SEC` 是为了简短
- **方法名拼写**: `ExcuteOperation`（SDK 本身少了个 e，不是 typo）
- **返回值**: 所有 SDK 方法返回 JSON 字符串

## 9 个工具与金蝶接口对应关系

| MCP 工具 | SDK 方法 | 用途 |
|----------|----------|------|
| `query_bill` | `ExecuteBillQuery` | 列表查询（二维数组） |
| `query_bill_json` | `BillQuery` | 列表查询（JSON 格式） |
| `view_bill` | `View` | 查看单条详情 |
| `save_bill` | `Save` | 保存/新增单据 |
| `submit_bill` | `Submit` | 提交单据 |
| `audit_bill` | `Audit` | 审核单据 |
| `unaudit_bill` | `UnAudit` | 反审核单据 |
| `delete_bill` | `Delete` | 删除单据 |
| `execute_operation` | `ExcuteOperation` | 禁用/启用等操作 |

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `KD_SERVER_URL` | 金蝶服务器地址 | 是 |
| `KD_ACCT_ID` | 账套 ID | 是 |
| `KD_USERNAME` | 用户名 | 是 |
| `KD_APP_ID` | 应用 ID | 是 |
| `KD_APP_SEC` | 应用密钥 | 是 |
| `KD_LCID` | 语言（默认 2052） | 否 |
| `KD_ORG_NUM` | 组织编码 | 否 |

## 运行与调试

```bash
uv sync              # 安装依赖
uv run server.py     # 启动（stdio 模式）
uv run mcp dev server.py  # MCP Inspector 调试
```
