# Kingdee K3Cloud MCP

[![PyPI version](https://img.shields.io/pypi/v/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml)

金蝶云星空 K3Cloud MCP Server，让 AI 助手（Claude Desktop、Claude Code、Cursor 等）通过自然语言查询和操作金蝶 ERP 系统。

> **提示**：配合 [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 使用效果更佳。Skill 为 Claude Code 提供金蝶表单字段、常用查询模式和工作流知识，大幅减少试错次数。

MCP Server for Kingdee K3Cloud ERP. Connect AI assistants to your ERP system via the [Model Context Protocol](https://modelcontextprotocol.io/).

## 功能特性

- **11 个 MCP 工具**：覆盖查询、新增、提交、审核、反审核、删除、下推等核心操作
- **通用接口设计**：单一 `form_id` 参数支持物料、客户、销售订单、采购订单等所有表单，无需为每种业务单独配置
- **只读/读写模式**：可限制 AI 只能查询，防止误操作
- **自动会话恢复**：长时间运行时自动处理会话超时，无需人工干预
- **多传输协议**：支持 stdio（本地）、SSE、streamable-http（远程共享）

## 快速开始

### 方式一：uvx 直接运行（推荐）

无需克隆仓库，直接通过 uvx 运行：

```bash
# 确保已安装 uv: https://docs.astral.sh/uv/
uvx kingdee-k3cloud-mcp
```

### 方式二：从源码运行

```bash
git clone https://github.com/adamzhang1987/kingdee-k3cloud-mcp.git
cd kingdee-k3cloud-mcp
uv sync
uv run kingdee-k3cloud-mcp
```

## 配置

复制环境变量模板并填写：

```bash
cp .env.example .env
```

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `KD_SERVER_URL` | 金蝶服务器地址（必须以 `/k3cloud/` 结尾） | `https://your-server/k3cloud/` |
| `KD_ACCT_ID` | 账套 ID | `your_acct_id` |
| `KD_USERNAME` | 用户名 | `your_username` |
| `KD_APP_ID` | 第三方应用 ID | `your_app_id` |
| `KD_APP_SEC` | 第三方应用密钥 | `your_app_secret` |
| `KD_LCID` | 语言（默认 2052 中文） | `2052` |
| `KD_ORG_NUM` | 组织编码（可选） | |

> 第三方应用 ID 和密钥需在金蝶云星空管理端的「第三方系统登录授权」中申请。

## 客户端配置

### Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）：

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

在项目目录下创建 `.mcp.json`：

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

### Cursor / Windsurf 及其他 MCP 客户端

配置方式与 Claude Desktop 类似，参考各客户端的 MCP 配置文档，使用相同的 `uvx` 命令和环境变量。

### SSE 模式（远程共享）

如需多人共用同一个服务实例：

```bash
# 启动 SSE 服务（默认端口 8000）
FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8080 uvx kingdee-k3cloud-mcp --transport sse
```

客户端连接地址：`http://your-server:8080/sse`

可通过 `MCP_API_KEY` 环境变量启用 Bearer Token 鉴权。

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

所有工具通过 `form_id` 参数支持任意表单（物料、客户、供应商、销售订单、采购订单等）。

## 只读模式

通过 `--mode readonly` 或 `MCP_MODE=readonly` 限制服务器只暴露 4 个查询工具，防止 AI 误操作写入数据。

```json
"args": ["kingdee-k3cloud-mcp", "--mode", "readonly"]
```

或：

```json
"env": {
  "MCP_MODE": "readonly",
  ...
}
```

## 调试

使用 MCP Inspector 可视化调试工具：

```bash
uvx mcp dev src/kingdee_k3cloud_mcp/server.py
```

## 架构说明

```
AI 助手（Claude / Cursor 等）
        │  MCP 协议
        ▼
kingdee-k3cloud-mcp（本项目）
        │  Kingdee Web API SDK
        ▼
金蝶云星空 K3Cloud
```

本项目使用官方金蝶 Python SDK（[kingdee-cdp-webapi-sdk](https://pypi.org/project/kingdee-cdp-webapi-sdk/)）与 K3Cloud API 通信，并通过 [FastMCP](https://github.com/modelcontextprotocol/python-sdk) 将其封装为标准 MCP 工具。

## 配套 Skill（Claude Code 用户推荐）

[kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 是配套的 Claude Code Skill，提供：

- 常用表单 ID 速查表（BD_MATERIAL、SAL_SaleOrder 等）
- 已验证字段名列表（避免字段名错误导致 500）
- 日报、客户查询、销售分析、库存分析、订单追踪等完整工作流

安装后 Claude Code 可自动掌握金蝶 ERP 的正确查询方式，无需反复试错。

## 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)
