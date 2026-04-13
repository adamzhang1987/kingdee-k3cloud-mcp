# Kingdee K3Cloud MCP

[![PyPI version](https://img.shields.io/pypi/v/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml)

金蝶云星空 K3Cloud MCP Server，让 AI 助手（Claude Desktop、Claude Code、Cursor、Cline、Cherry Studio、Openclaw 等任意支持 MCP 协议的客户端）通过自然语言查询和操作金蝶 ERP 系统。

> **提示**：Claude Code 用户可配合 [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 获得更佳体验。Skill 为 Claude Code 注入金蝶表单字段、常用查询模式和工作流知识，大幅减少试错次数。

```
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  kingdee-k3cloud    │───▶│  kingdee-k3cloud    │───▶│  K3Cloud Web API │
│  -skill             │    │  -mcp               │    │  (金蝶云星空)     │
│  知识库 / 工作流     │    │  执行引擎 / MCP工具  │    │                  │
└─────────────────────┘    └─────────────────────┘    └──────────────────┘
      Claude Code 专属            所有 MCP 客户端通用
```

MCP Server for Kingdee K3Cloud ERP. Connect AI assistants to your ERP system via the [Model Context Protocol](https://modelcontextprotocol.io/).

## 功能特性

- **15 个 MCP 工具**：覆盖查询、大数据量导出、新增、提交、审核、反审核、删除、下推等核心操作
- **通用接口设计**：单一 `form_id` 参数支持物料、客户、销售订单、采购订单等所有表单，无需为每种业务单独配置
- **高阶查询原语**：`query_bill_all`（自动翻页）、`query_bill_to_file`（流式落盘）、`query_bill_range`（日期分片），彻底消除模型手动循环的负担
- **只读/读写模式**：可限制 AI 只能查询，防止误操作
- **自动会话恢复**：长时间运行时自动处理会话超时，无需人工干预
- **多传输协议**：支持 stdio（本地）、SSE、streamable-http（远程共享）

## 快速开始

### 方式一：uvx 直接运行（推荐）

无需克隆仓库，直接通过 uvx 运行。**注意**：服务启动时必须提供 5 个必填环境变量（`KD_SERVER_URL`、`KD_ACCT_ID`、`KD_USERNAME`、`KD_APP_ID`、`KD_APP_SEC`），否则会报错退出。

**在 MCP 客户端中使用**（推荐，见下方"客户端配置"章节）：通过客户端配置的 `env` 字段传入，`uvx` 进程会自动读取。

**手动测试时**，可通过以下任一方式提供环境变量：

```bash
# 方式 A：在当前目录创建 .env 文件（服务启动时自动加载）
cp .env.example .env   # 填写真实值后再运行
uvx kingdee-k3cloud-mcp

# 方式 B：在命令行临时导出
export KD_SERVER_URL=https://your-server/k3cloud/
export KD_ACCT_ID=your_acct_id
export KD_USERNAME=your_username
export KD_APP_ID=your_app_id
export KD_APP_SEC=your_app_secret
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
| `KD_USERNAME` | 集成用户账号 | `your_username` |
| `KD_APP_ID` | 应用 ID | `your_app_id` |
| `KD_APP_SEC` | 应用密钥 | `your_app_secret` |
| `KD_LCID` | 语言（默认 2052 中文） | `2052` |
| `KD_ORG_NUM` | 组织编码（可选） | |

> 第三方应用 ID 和密钥需在金蝶云星空管理端的「第三方系统登录授权」中申请。

### 环境变量配置说明

在金蝶云星空产品中配置第三方系统集成，需按以下步骤获取 5 个环境变量：

#### 1. 登录金蝶云星空管理后台

1. 使用管理员账号登录金蝶云星空系统，进入「系统管理」菜单下的「第三方系统登录授权」。
2. 点击新增按钮，进入新增第三方系统登录授权功能页面。
3. 点击”获取应用 ID”按钮，根据提示跳转到 [Open 网站](https://open.kingdee.com/) 的第三方系统登录授权页面，点击“新增授权”。
4. Open 网站用户根据自身信息进行表单填写。
5. 提交成功后会生成应用信息，复制应用信息填入金蝶云星空产品 - 第三方系统登录授权 - 获取应用 ID - 应用信息框中，点击“确认”按钮。
6. 配置集成用户。
7. 点击“保存”按钮，保存成功后点击“生成测试链接”，测试链接是否成功。

> **注意**：当前数据库中心 ID（即账套 ID）可以通过生成测试链接弹出的信息中获取。

#### 2. 获取 KD_SERVER_URL

金蝶服务器地址，格式为 `https://your-server/k3cloud/`，其中：
- `your-server` 为金蝶云星空服务器的域名或 IP 地址
- 一般以 `/k3cloud/` 结尾
- 示例：`https://erp.company.com/k3cloud/`

#### 3. 获取 KD_ACCT_ID - 账套 ID


#### 4. 获取 KD_USERNAME - 集成用户账号

使用具有相关模块操作权限的账号，**不建议使用管理员账号**。建议新建一个专门的集成用户账号，并为其分配所需的模块操作权限。

#### 5. 获取 KD_APP_ID - 应用 ID 和 KD_APP_SEC - 应用密钥

> **注意**：如需查看 APP_SECRET，可随时在应用详情中查看；如遗失，也可通过「重置」功能重新生成。

#### 6. 验证配置

配置完成后，可通过以下命令验证连接：

```bash
cd kingdee-k3cloud-mcp
cp .env.example .env
# 编辑 .env 填写上述 5 个环境变量
uvx kingdee-k3cloud-mcp
```

如看到「MCP Server running」或类似输出，表示配置成功。

---

参考文档：[金蝶云星空第三方系统集成配置指南](https://vip.kingdee.com/knowledge/specialDetail/229961573895771136?category=229963554177453824&id=298030366575393024&type=Knowledge&productLineId=1&lang=zh-CN)

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

### 查询工具（只读模式下可用）

| 工具 | 说明 |
|------|------|
| `query_bill` | 查询单据数据（返回二维数组） |
| `query_bill_json` | 查询单据数据（返回 JSON，字段名作为 key） |
| `count_bill` | 估算查询结果行数，用于大数据量查询前的探测 |
| `query_bill_all` | 自动翻页查询直到拉完或达到安全上限，返回合并结果 |
| `query_bill_to_file` | 自动翻页并流式写入本地文件（ndjson / csv），适合万行以上导出 |
| `query_bill_range` | 按日期自动分片（月/周/日）+ 翻页，适合跨月/跨年查询，支持落盘 |
| `view_bill` | 查看单条记录完整详情 |
| `query_metadata` | 查询表单字段结构（元数据） |

### 写入工具（读写模式下可用）

| 工具 | 说明 |
|------|------|
| `save_bill` | 保存/新增单据 |
| `submit_bill` | 提交单据 |
| `audit_bill` | 审核单据 |
| `unaudit_bill` | 反审核单据 |
| `delete_bill` | 删除单据 |
| `execute_operation` | 执行自定义操作（禁用、反禁用等） |
| `push_bill` | 下推单据（如销售订单→发货通知单） |

所有工具通过 `form_id` 参数支持任意表单（物料、客户、供应商、销售订单、采购订单等）。

## 只读模式

通过 `--mode readonly` 或 `MCP_MODE=readonly` 限制服务器只暴露 8 个查询工具，防止 AI 误操作写入数据。

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
AI 助手（Claude Desktop / Claude Code / Cursor / Cline / Openclaw 等）
        │  MCP 协议
        ▼
kingdee-k3cloud-mcp（本项目）
        │  Kingdee Web API SDK
        ▼
金蝶云星空 K3Cloud
```

本项目使用官方金蝶 Python SDK（[kingdee-cdp-webapi-sdk](https://pypi.org/project/kingdee-cdp-webapi-sdk/)）与 K3Cloud API 通信，并通过 [FastMCP](https://github.com/modelcontextprotocol/python-sdk) 将其封装为标准 MCP 工具。

## 配套 Skill（Claude Code 用户）

[kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 是面向 Claude Code 的配套 Skill，提供：

- 常用表单 ID 速查表（BD_MATERIAL、SAL_SaleOrder 等）
- 已验证字段名列表（避免字段名错误导致 500）
- 日报、客户查询、销售分析、库存分析、订单追踪等完整工作流

安装后 Claude Code 可自动掌握金蝶 ERP 的正确查询方式，无需反复试错。

## 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)
