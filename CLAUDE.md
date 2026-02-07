# jdyxk-mcp-server

金蝶云星空 K3Cloud MCP Server — 通过 MCP 协议暴露金蝶 Web API，供 AI 助手调用。

## 项目结构

```
jdyxk-mcp-server/                          # 仓库根目录 / 工作目录
├── jdyxk-mcp-server/                      # MCP Server 代码（uv 项目）
│   ├── server.py                          # 主文件（9 个 MCP 工具）
│   ├── pyproject.toml                     # 项目配置
│   ├── README.md                          # 用户使用说明
│   ├── .env.example                       # 环境变量模板
│   ├── .gitignore
│   └── uv.lock
├── SDK_Python3.0_V8.2.0/                  # 金蝶官方 SDK 及调用示例（参考用）
│   ├── python_sdk_v8.2.0/*.whl           # SDK 包（PyPI 亦有发布：kingdee-cdp-webapi-sdk）
│   └── python_sdk_demo/                   # 调用示例
└── CLAUDE.md                              # 本文档
```

## 金蝶 SDK 技术注意事项

- `K3CloudApiSdk(server_url)` 构造函数要求 `server_url` 为第一个参数（必传）
- `InitConfig` 的参数名为 `app_secret`（不是 `app_sec`），环境变量名用 `KD_APP_SEC` 是为了简短
- 所有 SDK 方法返回 JSON 字符串，需要 `json.loads()` 解析
- SDK 方法名有拼写不一致：`ExcuteOperation`（少了个 e），这是 SDK 本身的命名

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

### 未纳入第一批的接口（后续可扩展）

`BatchSave`、`Allocate` / `CancelAllocate`、`GroupSave` / `GroupDelete` / `QueryGroupInfo`、`attachmentUpload` / `attachmentDownLoad`、`getSysReportData`、`SendMsg`、`SwitchOrg`、`FlexSave`、`Execute`

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

## 设计决策

**MCP 框架：`mcp[cli]` (FastMCP)** — Anthropic 官方 Python SDK，装饰器模式最简洁

**传输方式：stdio** — Claude Desktop 默认支持，配置最简单。备选 SSE（`mcp.run(transport="sse")`）

**凭证管理：环境变量 + `.env`** — 安全且灵活，Claude Desktop 的 `env` 字段也可传递

**包管理：uv** — MCP 官方推荐，速度快，`uv run` 自动管理虚拟环境

**单文件架构** — 9 个工具 + SDK 初始化约 250 行，单文件完全可控。超过 20 个工具时再拆分

**通用型工具** — 通过 `form_id` 参数支持所有金蝶表单，而非为每种表单单独建工具

**SDK 直接初始化** — 模块级直接初始化 `api_sdk`，密钥或网络配置有误应在启动时暴露错误

**参数设计** — `numbers` 用逗号分隔字符串（降低 LLM 调用难度）；`model_data` 用 JSON 字符串传递，自动补充 `Model` 包装层；所有工具直接返回 SDK 原始 JSON

## 运行与调试

```bash
cd jdyxk-mcp-server
uv sync                       # 安装依赖
uv run server.py              # 启动（stdio 模式）
uv run mcp dev server.py      # MCP Inspector 可视化调试
```
