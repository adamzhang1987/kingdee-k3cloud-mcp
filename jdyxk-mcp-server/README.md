# jdyxk-mcp-server

金蝶云星空 K3Cloud MCP Server，让 AI 助手（Claude Desktop、Claude Code 等）通过自然语言操作金蝶 ERP 系统。

支持查询、查看、保存、提交、审核、反审核、删除单据及执行自定义操作，覆盖金蝶云星空 Web API 核心接口。

## 前提条件

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- 金蝶云星空第三方系统登录授权（应用 ID + 应用密钥）

## 安装

```bash
git clone <repo-url>
cd jdyxk-mcp-server
uv sync
```

## 配置

复制环境变量模板并填写：

```bash
cp .env.example .env
```

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `KD_SERVER_URL` | 金蝶服务器地址 | `https://your-server/k3cloud/` |
| `KD_ACCT_ID` | 账套 ID | `your_acct_id` |
| `KD_USERNAME` | 用户名 | `your_username` |
| `KD_APP_ID` | 应用 ID | `your_app_id` |
| `KD_APP_SEC` | 应用密钥 | `your_app_secret` |
| `KD_LCID` | 语言（默认 2052 中文） | `2052` |
| `KD_ORG_NUM` | 组织编码（可选） | |

## 客户端配置

### Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）：

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

### Claude Code

在需要使用的项目目录下创建 `.mcp.json`：

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

### 其他 MCP 客户端（stdio）

本 server 默认使用 stdio 传输，启动命令：

```bash
uv --directory /path/to/jdyxk-mcp-server run server.py
```

任何支持 MCP stdio 协议的客户端均可接入。

### SSE 模式（HTTP 服务）

如需通过 HTTP 共享同一服务实例（适用于 Claude.ai Web、Cursor 等），可启动 SSE 模式：

```bash
cd /path/to/jdyxk-mcp-server
uv run server.py --transport sse
```

自定义绑定地址和端口：

```bash
FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8080 uv run server.py --transport sse
```

也可在 `.env` 中配置（参见 `.env.example`）。启动后客户端连接地址：

- SSE 端点：`http://127.0.0.1:8000/sse`
- 消息端点：`http://127.0.0.1:8000/messages/`

### SSE 鉴权

设置 `MCP_API_KEY` 后，所有 SSE 请求需携带 Bearer Token：

```bash
# .env 中配置
MCP_API_KEY=your-secret-api-key

# 客户端连接时添加 Header
Authorization: Bearer your-secret-api-key
```

不设置 `MCP_API_KEY` 则不启用鉴权（适用于本地开发或已有网络隔离的场景）。stdio 模式不受此配置影响。

## 可用工具

| 工具 | 类型 | 说明 |
|------|------|------|
| `query_bill` | 查询 | 查询单据数据（返回二维数组） |
| `query_bill_json` | 查询 | 查询单据数据（返回 JSON，字段名作为 key） |
| `view_bill` | 查询 | 查看单条记录完整详情 |
| `query_metadata` | 查询 | 查询表单字段结构（元数据） |
| `save_bill` | 写入 | 保存/新增单据 |
| `submit_bill` | 写入 | 提交单据 |
| `audit_bill` | 写入 | 审核单据 |
| `unaudit_bill` | 写入 | 反审核单据 |
| `delete_bill` | 写入 | 删除单据 |
| `execute_operation` | 写入 | 执行自定义操作（禁用、反禁用等） |
| `push_bill` | 写入 | 下推单据（如销售订单→发货通知单） |

所有工具通过 `form_id` 参数支持金蝶的各类表单（物料、客户、销售订单、采购订单等），无需为每种表单单独配置。

## 只读模式

通过 `--mode` 参数或 `MCP_MODE` 环境变量可限制服务器只暴露查询类工具（4 个），写入类工具（7 个）将不会注册，AI 无法调用。

**CLI 参数：**

```bash
uv run server.py --mode readonly
```

**环境变量（适合 Claude Desktop `env` 块）：**

```json
"env": {
  "MCP_MODE": "readonly",
  ...
}
```

启动时 stderr 会打印当前模式和工具数量，例如：`[k3cloud] mode=readonly, tools=4`。

## 调试

使用 MCP Inspector 可视化调试：

```bash
cd /path/to/jdyxk-mcp-server
uv run mcp dev server.py
```

## TODO

- [ ] 发布到 PyPI，支持 `uvx jdyxk-mcp-server` 直接运行
