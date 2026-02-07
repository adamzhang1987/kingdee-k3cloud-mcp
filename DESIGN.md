# 金蝶云星空 MCP Server 设计文档

## 设计决策记录

### 1. 技术选型

**MCP 框架：`mcp[cli]` (FastMCP)**
- 选择理由：Anthropic 官方 Python SDK，装饰器模式最简洁，社区活跃
- 备选方案：自行实现 MCP 协议（过于复杂，无必要）

**传输方式：stdio**
- 选择理由：Claude Desktop 默认支持，配置最简单，无需网络端口
- 备选方案：SSE（适合远程/多客户端场景，启动时改 `mcp.run(transport="sse")` 即可切换）

**凭证管理：环境变量 + `.env`**
- 选择理由：安全（不进版本控制）、灵活（Claude Desktop 的 `env` 字段也可传递）
- 备选方案：金蝶 SDK 自带的 `conf.ini`（不够灵活，且不适合 MCP 场景）

**包管理：uv**
- 选择理由：MCP 官方推荐，速度快，`uv run` 自动管理虚拟环境

**单文件架构：`server.py`**
- 选择理由：金蝶 SDK 接口本身就是简单函数调用，无需额外抽象层。9 个工具 + SDK 初始化，总代码约 260 行，单文件完全可控
- 何时拆分：如果后续工具数量超过 20 个或需要复杂的数据转换逻辑

### 2. 工具设计

**通用型而非专用型**
- 决定：通过 `form_id` 参数支持所有金蝶表单，而非为每种表单（物料、客户、订单等）单独建工具
- 理由：金蝶有数百种表单，逐一建工具不现实。LLM 通过 docstring 中的 FormId 列表即可正确选择
- 权衡：降低了 LLM 的使用门槛（需要知道 FormId），但大幅减少了工具数量和维护成本

**SDK 直接初始化**
- 决定：模块级直接初始化 `api_sdk`，不使用延迟加载
- 理由：密钥或网络配置有误应当在启动时就暴露错误，而非在用户首次调用工具时才失败。MCP 客户端（Claude Desktop / Code）的 `env` 字段保证环境变量在启动前已就绪

**参数设计**
- `numbers` 参数用逗号分隔的字符串而非 JSON 数组，降低 LLM 调用难度
- `model_data` 用 JSON 字符串传递，自动补充 `Model` 包装层
- 所有工具直接返回 SDK 原始 JSON 字符串，不做二次加工

### 3. 覆盖的 9 个工具

| 工具 | SDK 方法 | 用途 |
|------|----------|------|
| `query_bill` | `ExecuteBillQuery` | 列表查询（二维数组） |
| `query_bill_json` | `BillQuery` | 列表查询（JSON 格式） |
| `view_bill` | `View` | 查看单条详情 |
| `save_bill` | `Save` | 保存/新增单据 |
| `submit_bill` | `Submit` | 提交单据 |
| `audit_bill` | `Audit` | 审核单据 |
| `unaudit_bill` | `UnAudit` | 反审核单据 |
| `delete_bill` | `Delete` | 删除单据 |
| `execute_operation` | `ExcuteOperation` | 禁用/启用等操作 |

### 4. 未纳入第一批的接口（后续可扩展）

- `BatchSave` — 批量保存
- `Allocate` / `CancelAllocate` — 分配/取消分配
- `GroupSave` / `GroupDelete` / `QueryGroupInfo` — 分组操作
- `attachmentUpload` / `attachmentDownLoad` — 附件操作
- `getSysReportData` — 系统报表
- `SendMsg` — 消息发送
- `SwitchOrg` — 切换组织
- `FlexSave` — 弹性域
- `Execute` — 自定义服务端点

### 5. 金蝶 SDK 注意事项

- `K3CloudApiSdk(server_url)` 构造函数要求 `server_url` 为第一个参数（必传）
- `InitConfig` 的参数名为 `app_secret`（不是 `app_sec`），环境变量名用 `KD_APP_SEC` 是为了简短
- 所有 SDK 方法返回 JSON 字符串，需要 `json.loads()` 解析
- SDK 方法名有拼写不一致：`ExcuteOperation`（少了个 e），这是 SDK 本身的命名

---

## 项目结构

```
jdyxk-mcp-server/                      # 仓库根目录
├── jdyxk-mcp-server/                  # MCP Server（uv 项目）
│   ├── server.py                      # 主文件（9 个 MCP 工具）
│   ├── pyproject.toml                 # 项目配置
│   ├── README.md                      # 使用说明
│   ├── CLAUDE.md                      # AI 助手参考
│   ├── .env.example                   # 环境变量模板
│   ├── .gitignore
│   └── uv.lock
└── DESIGN.md                          # 本文档
```

## 使用方式

### Claude Desktop 配置

在 `~/Library/Application Support/Claude/claude_desktop_config.json` 中：

```json
{
  "mcpServers": {
    "kingdee-k3cloud": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/jdyxk-mcp-server",
        "run",
        "server.py"
      ],
      "env": {
        "KD_ACCT_ID": "your_acct_id",
        "KD_USERNAME": "your_username",
        "KD_APP_ID": "your_app_id",
        "KD_APP_SEC": "your_app_secret",
        "KD_SERVER_URL": "https://your-server/k3cloud/",
        "KD_LCID": "2052"
      }
    }
  }
}
```

### Claude Code 配置

在项目目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "kingdee-k3cloud": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/jdyxk-mcp-server",
        "run",
        "server.py"
      ],
      "env": {
        "KD_ACCT_ID": "your_acct_id",
        "KD_USERNAME": "your_username",
        "KD_APP_ID": "your_app_id",
        "KD_APP_SEC": "your_app_secret",
        "KD_SERVER_URL": "https://your-server/k3cloud/",
        "KD_LCID": "2052"
      }
    }
  }
}
```

### 调试

```bash
cd jdyxk-mcp-server/jdyxk-mcp-server

# MCP Inspector 可视化调试
uv run mcp dev server.py

# 直接运行（stdio 模式）
uv run server.py
```

---

*创建于: 2026-02-07*
