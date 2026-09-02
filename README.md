# 金蝶MCP Server（Kingdee K3Cloud MCP）

[English](README.en.md) | [中文](README.md)

[金蝶MCP 官网](https://adamzhang1987.github.io/kingdee-k3cloud-mcp/) | [GitHub](https://github.com/adamzhang1987/kingdee-k3cloud-mcp) | [PyPI](https://pypi.org/project/kingdee-k3cloud-mcp/)

[![PyPI version](https://img.shields.io/pypi/v/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![Downloads](https://img.shields.io/pypi/dm/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/kingdee-k3cloud-mcp)](https://pypi.org/project/kingdee-k3cloud-mcp/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/adamzhang1987/kingdee-k3cloud-mcp/actions/workflows/ci.yml)

金蝶MCP Server（Kingdee K3Cloud MCP）面向金蝶云星空 ERP，让 AI 助手（Claude Desktop、Claude Code、Cursor、Windsurf、Cline、Continue、Cherry Studio 等任意支持 MCP 协议的客户端）通过自然语言查询和操作金蝶系统。标准 PyPI 包，`pip install` 或 `uvx` 均可直接运行，无需绑定特定包管理器。

> **提示**：通过 [Openclaw](https://docs.openclaw.ai/) 等支持 MCP 的 Agent 平台接入后，可在其支持的 IM 渠道（如微信、Telegram）中用自然语言查库存、查单据，无需打开金蝶网页端。支持 Skill 机制的 AI Agent（Claude Code、Openclaw 等）还可配合 [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 获得更佳体验——Skill 为 Agent 注入金蝶表单字段、常用查询模式和工作流知识，大幅减少试错次数，但**并非必需**，MCP Server 本身即可独立配合任意 MCP 客户端使用全部工具。

```
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  kingdee-k3cloud    │───▶│  kingdee-k3cloud    │───▶│  K3Cloud Web API │
│  -skill             │    │  -mcp               │    │  (金蝶云星空)     │
│  知识库 / 工作流     │    │  执行引擎 / MCP工具  │    │                  │
└─────────────────────┘    └─────────────────────┘    └──────────────────┘
      支持 Skill 的 Agent          所有 MCP 客户端通用
```

MCP Server for Kingdee K3Cloud ERP. Connect AI assistants to your ERP system via the [Model Context Protocol](https://modelcontextprotocol.io/).

## 功能特性

- **15 个 MCP 工具**：覆盖查询、大数据量导出、新增、提交、审核、反审核、删除、下推等核心操作
- **通用接口设计**：单一 `form_id` 参数支持物料、客户、销售订单、采购订单等所有表单，无需为每种业务单独配置
- **高阶查询原语**：`query_bill_all`（自动翻页）、`query_bill_to_file`（流式落盘）、`query_bill_range`（日期分片），彻底消除模型手动循环的负担
- **只读/读写模式**：可限制 AI 只能查询，防止误操作
- **认证失败诊断**：启动即校验凭据，凭据/授权配置错误会返回可操作的修复指引，而不是金蝶那句误导的「会话信息已丢失」
- **多传输协议**：支持 stdio（本地）、SSE、streamable-http（远程共享）
- **标准 Python 包**：`pip install` 即可安装，仅需 Python 3.10+，无强制包管理器依赖
- **类型安全的入参校验**：所有工具入参基于类型注解，由 FastMCP 在调用时自动做 Pydantic 运行时校验，参数结构错误会在到达金蝶 API 之前被拦截

## 5 分钟快速开始

1. 安装：`pip install kingdee-k3cloud-mcp`（或用 `uvx kingdee-k3cloud-mcp` 免安装直接跑）
2. 在金蝶云星空「第三方系统登录授权」中申请应用 ID/密钥，拿到 5 个必填环境变量（见下方[配置](#配置)）
3. 把变量填进你的 MCP 客户端配置（见下方[客户端配置](#客户端配置)），保存重启
4. 直接用自然语言提问，例如：
   - 「查一下上周已审核的销售订单，按金额排序」
   - 「XX 物料现在各仓库库存分别是多少」
   - 「把 3 月份所有销售出库单导出成 csv」

## 快速开始

### 方式一：pip 安装（推荐，无需 uv）

```bash
pip install kingdee-k3cloud-mcp
kingdee-k3cloud-mcp
```

标准 PyPI 包，仅需 Python 3.10+，不依赖 `uv`。**注意**：服务启动时必须提供 5 个必填环境变量（`KD_SERVER_URL`、`KD_ACCT_ID`、`KD_USERNAME`、`KD_APP_ID`、`KD_APP_SEC`），否则会报错退出。

**在 MCP 客户端中使用**（推荐，见下方"客户端配置"章节）：通过客户端配置的 `env` 字段传入。

**手动测试时**，可通过以下任一方式提供环境变量：

```bash
# 方式 A：在当前目录创建 .env 文件（服务启动时自动加载）
cp .env.example .env   # 填写真实值后再运行
kingdee-k3cloud-mcp

# 方式 B：在命令行临时导出
export KD_SERVER_URL=https://your-server/k3cloud/
export KD_ACCT_ID=your_acct_id
export KD_USERNAME=your_username
export KD_APP_ID=your_app_id
export KD_APP_SEC=your_app_secret
kingdee-k3cloud-mcp
```

### 方式二：uvx 直接运行（免安装）

无需 `pip install`，`uvx` 会自动创建隔离环境并运行，用法与上面完全一致，把 `kingdee-k3cloud-mcp` 换成 `uvx kingdee-k3cloud-mcp` 即可：

```bash
cp .env.example .env
uvx kingdee-k3cloud-mcp
```

### 方式三：从源码运行

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
| `KD_STARTUP_CHECK` | 启动时是否校验凭据（默认开启，`0` 关闭） | `1` |
| `KD_STARTUP_CHECK_TIMEOUT` | 启动自检的超时秒数（默认 5） | `5` |

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

以下所有客户端配置都用 `"command": "uvx"` 免安装启动；若已 `pip install kingdee-k3cloud-mcp`，把 `"command": "uvx"` 改成 `"command": "kingdee-k3cloud-mcp"` 并删掉 `"args"` 中的包名（保留其余参数如 `--mode readonly`）即可，两种方式效果完全一致。

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

### Cursor / Windsurf

Cursor：`Settings → MCP → Add new MCP Server`；Windsurf：编辑 `~/.codeium/windsurf/mcp_config.json`。两者配置格式与 Claude Desktop 一致：

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

### Cline / Continue / Cherry Studio 及其他 MCP 客户端

配置结构与上面完全一致——`command` + `args` + `env`，填入相同的 `uvx kingdee-k3cloud-mcp` 与 5 个环境变量即可。具体填写位置参考各客户端自己的 MCP 配置文档：

- Cline（VS Code 插件）：MCP Servers 面板 → Configure MCP Servers
- Continue：`~/.continue/config.json` 的 `mcpServers` 字段
- Cherry Studio：设置 → MCP 服务器 → 添加服务器

### Openclaw（IM / 移动端接入）

[Openclaw](https://docs.openclaw.ai/) 是支持 Skill 机制的 Agent 平台，可将本 MCP Server 接入其支持的 IM 渠道（如微信、Telegram），实现"发一句话查金蝶库存/单据"。配置方式同样是标准 MCP Server 声明（`command`/`args`/`env`），具体接入步骤参考 [Openclaw 官方文档](https://docs.openclaw.ai/)；配合 [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 使用可进一步减少字段试错。IM 渠道的具体支持范围由 Openclaw 平台决定。

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

## 数据权限

MCP Server 本身**不实现**数据权限模型——它以「第三方系统登录授权」方式接入金蝶云星空，身份固定为 `.env` 中的 `KD_ACCT_ID`（账套）+ `KD_USERNAME`（集成用户）+ `KD_ORG_NUM`（组织，默认 `0`）。所有工具调用共享这一个身份，不支持按调用方切换用户，因此 **AI 能看到什么数据，完全由这个集成用户在星空里的权限配置决定**。

### 在星空侧配置

1. 使用专用集成用户（参见上文「不建议使用管理员账号」），进入「系统管理」→ 用户管理 → 用户授权
2. 分配**功能权限**：允许访问的表单（如 `SAL_SaleOrder`）+ 允许的操作（查询/新增/提交/审核）
3. 分配**数据权限**：可访问的组织范围、数据规则（按客户/部门/业务员等过滤）、字段权限
4. 如需将查询默认限定在单一组织，可设置 `KD_ORG_NUM`

### MCP 侧的两道补充闸门

这两者是权限的**补充**，不能替代星空侧的权限配置：

- `--mode readonly` / `MCP_MODE=readonly`：全局禁用所有写入工具
- `MCP_API_KEY`：SSE / streamable-http 传输下的连接鉴权（stdio 模式不涉及）

### 排查：权限问题的两种表现

| 现象 | 原因 | 处理 |
|------|------|------|
| 报错 500，错误信息原样透传 | 功能权限不足 | 在星空给集成用户补齐对应表单/操作权限 |
| 查询**不报错**，但行数偏少或为空 | 数据规则**静默过滤** | 用同一集成用户账号登录星空 Web 端，跑同样的查询条件对比行数，确认是否被权限过滤 |

⚠️ 第二种情况容易被误判为"该时间段确实没有数据"——`count_bill` / `query_bill*` 拿到的是权限过滤后的结果，本身无法区分"真没数据"和"被权限挡了"。

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

## 适用场景

金蝶 ERP 的 MCP 集成方案不止一种，各有侧重。本项目更适合以下场景：

- **需要长期稳定运行的生产环境 AI Agent**：`--mode readonly` 提供只读边界；启动时自动校验凭据，配置错误在启动日志里就能看到，不必等到第一次工具调用；认证失败会返回明确的诊断而非误导文案，排障不靠猜
- **数据量较大的查询/导出需求**：`query_bill_all`（自动翻页）、`query_bill_to_file`（流式落盘）、`query_bill_range`（日期分片）三个高阶原语专门处理万行级数据，避免让模型手写翻页循环
- **有自定义字段 / 二次开发的金蝶部署**：`query_metadata` 工具可让 AI 在查询前自行发现表单的实际字段结构，不依赖预置字段表；配合 [kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 还可把企业专属的表单/字段/审批流封装成可复用的知识
- **需要多种接入方式共存**：同一个 Server 支持 stdio（本地 IDE）、SSE、streamable-http（远程共享部署），也可作为 Openclaw 工具接入 IM 渠道

如果你的场景是个人轻量试用、追求几分钟内跑通第一次查询，本项目同样支持 `pip install` 一步安装、开箱即用；具体选哪个方案，取决于你更看重「装上就能用」还是「长期在生产环境里稳定跑」。

## 为什么选择 MCP 而非直接调用？

让 AI 直接通过 Skill 构造 HTTP 请求访问 ERP，技术上可行，但会引入一系列安全隐患。MCP 的进程隔离模型从根本上解决了这些问题。

### 凭证不进入 LLM 上下文

MCP Server 以独立进程运行，凭证（`KD_APP_SEC`、服务器地址、账套 ID）通过环境变量注入，**模型永远看不到这些信息**。如果改用 Skill 直接调用，凭证必须出现在提示词或对话上下文中，一旦对话日志被导出、上下文被截图，或模型意外将其输出，机密就泄露了。

### 强制权限边界，而非依赖提示词约束

Skill 是"建议"——模型可能理解有误，也可能被精心构造的输入绕过。MCP Server 的 `--mode readonly` 则是**物理限制**：写入工具根本不存在于工具列表中，模型想用也用不了。这是"告诉实习生不要删数据"和"实习生根本没有 DELETE 权限"之间的本质区别。

### 网络隔离

MCP Server 部署在企业内网（或本机），可直接访问内部 ERP；LLM 运行在云端，**从不直接接触内部网络**。使用 stdio 传输时，所有 ERP 流量都在本机进程间流转，不经过任何外部网络。

### 完整的审计链路

每一次工具调用都经过 MCP Server，可在此统一记录操作类型、参数、时间戳和调用来源。直接调用方式下，AI 的每次请求对企业安全团队来说是不可见的黑盒。

### 最小权限原则

集成用户（`KD_USERNAME`）可在金蝶系统内被限制为特定模块、只读权限。MCP Server 继承并传递这些限制，LLM 无需感知权限边界，权限边界自然生效。

### 个人见解

将 LLM 视为**不可信的外部调用方**（而非可信的内部系统）是正确的零信任设计思路。MCP 层的存在，使 Skill 和 MCP 的职责分离清晰：Skill 负责"什么时候用、怎么用"（策略），MCP 负责"能做什么"（机制）。即使未来模型能力更强，或出现提示词注入攻击，最坏情况下的爆炸半径也被 MCP Server 的权限模型所限定，而不是依赖模型的"自觉"。

---

## 配套 Skill（支持 Skill 的 Agent）

[kingdee-k3cloud-skill](https://github.com/adamzhang1987/kingdee-k3cloud-skill) 是面向支持 Skill 机制的 AI Agent（Claude Code、openclaw、hermes 等）的配套 Skill，提供：

- 常用表单 ID 速查表（BD_MATERIAL、SAL_SaleOrder 等）
- 已验证字段名列表（避免字段名错误导致 500）
- 日报、客户查询、销售分析、库存分析、订单追踪等完整工作流

安装后 Agent 可自动掌握金蝶 ERP 的正确查询方式，无需反复试错。

## 开发

```bash
git clone https://github.com/adamzhang1987/kingdee-k3cloud-mcp.git
cd kingdee-k3cloud-mcp
uv sync --dev

make test    # 运行测试（覆盖率报告）
make lint    # ruff check + mypy
make format  # ruff format + fix
make build   # uv build + twine check
```

安装 pre-commit hooks（可选，与 CI 保持一致）：

```bash
uv run pre-commit install
```

## 贡献者

<a href="https://github.com/adamzhang1987/kingdee-k3cloud-mcp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=adamzhang1987/kingdee-k3cloud-mcp" alt="Contributors" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)
