# 目录上架文案

统一文案，适用于 mcp.so、PulseMCP、smithery.ai 等目录提交。

---

## 项目名称

```
kingdee-k3cloud-mcp
```

## 中文简介（约 150 字）

```
金蝶云星空 K3Cloud MCP Server。让 Claude Desktop、Cursor、Cline、Cherry Studio 等任意支持 MCP 协议的 AI 客户端，通过自然语言直接查询和操作金蝶 ERP 系统。

15 个 MCP 工具覆盖查询、大数据量导出、新增、提交、审核、反审核、下推等核心操作。通用接口设计——单一 form_id 参数支持销售订单、采购订单、库存、物料、客户、供应商等所有表单，无需逐单配置。内置自动翻页、流式落盘、日期分片三大高阶查询工具，彻底消除模型手动循环的负担。支持只读模式（防误操作）和自动会话恢复，适合生产环境长期运行。
```

## 英文简介（约 200 字）

```
MCP Server for Kingdee K3Cloud (金蝶云星空) — one of China's most widely adopted ERP systems.

Connect any MCP-compatible AI assistant (Claude Desktop, Cursor, Cline, Cherry Studio, Openclaw, etc.) to your Kingdee ERP via natural language. Query bills, submit orders, audit documents, push down workflows, and bulk-export data — all without touching the Kingdee web interface.

15 MCP tools with a universal form_id design: one tool covers all form types (sales orders, purchase orders, inventory, materials, customers, suppliers). Advanced helpers — query_bill_all (auto-pagination), query_bill_to_file (streaming to disk), query_bill_range (date-range sharding) — eliminate the need for manual looping in AI sessions. Read-only mode prevents accidental writes. Auto session recovery handles Kingdee session timeouts transparently. Supports stdio, SSE, and streamable-http transports.

Claude Code users can pair it with kingdee-k3cloud-skill for injected domain knowledge (field names, query patterns, workflows).
```

## Feature Bullets（5 条，英文）

```
• 15 MCP tools: query, bulk export, create, submit, audit, unaudit, push-down
• Universal form_id interface — covers all Kingdee form types with a single tool
• Auto-pagination & streaming export — query_bill_all / query_bill_to_file / query_bill_range
• Read-only mode + auto session recovery for safe production use
• Multi-transport: stdio (local), SSE, streamable-http (remote/shared)
```

## 关键链接

| 用途 | 链接 |
|------|------|
| GitHub | https://github.com/adamzhang1987/kingdee-k3cloud-mcp |
| PyPI | https://pypi.org/project/kingdee-k3cloud-mcp/ |
| 配套 Skill | https://github.com/adamzhang1987/kingdee-k3cloud-skill |
| Issues | https://github.com/adamzhang1987/kingdee-k3cloud-mcp/issues |

## 分类标签

```
erp, kingdee, k3cloud, business, enterprise, china, mcp-server
```

## 安装命令（供目录展示）

```bash
uvx kingdee-k3cloud-mcp
```

或在 MCP 客户端 config 中：

```json
{
  "mcpServers": {
    "kingdee": {
      "command": "uvx",
      "args": ["kingdee-k3cloud-mcp"],
      "env": {
        "KD_SERVER_URL": "https://your-server/k3cloud/",
        "KD_ACCT_ID": "your_acct_id",
        "KD_USERNAME": "your_username",
        "KD_APP_ID": "your_app_id",
        "KD_APP_SEC": "your_app_secret"
      }
    }
  }
}
```

---

## 各平台提交入口

| 平台 | 提交链接 | 备注 |
|------|---------|------|
| mcp.so | https://mcp.so/submit | 填写网页表单，粘贴上述英文简介 |
| PulseMCP | https://pulsemcp.com/submit | 填写网页表单 |
| smithery.ai | https://smithery.ai | 可能需要连接 GitHub repo，按引导操作 |
