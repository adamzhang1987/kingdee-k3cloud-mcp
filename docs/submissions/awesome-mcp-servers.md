# Awesome-MCP-Servers 提交草稿

提交目标：https://github.com/punkpeye/awesome-mcp-servers

## 条目内容（粘贴到 README.md 对应分类）

在 **ERP** 或 **Business Tools** 分类下（若无该分类可建议新增），插入以下一行：

```markdown
- [kingdee-k3cloud-mcp](https://github.com/adamzhang1987/kingdee-k3cloud-mcp) - MCP Server for Kingdee K3Cloud ERP (金蝶云星空). Connect AI assistants to your ERP system for querying bills, submitting orders, managing inventory, and more via natural language. `Python` `MIT`
```

> 注：按 awesome-mcp-servers 规范，license badge 需与实际对齐（本项目为 Apache-2.0），请在提交时核对目录的 license 标注格式。

## PR 标题

```
Add kingdee-k3cloud-mcp: MCP Server for Kingdee K3Cloud ERP
```

## PR 描述

```markdown
## Description

Adding [kingdee-k3cloud-mcp](https://github.com/adamzhang1987/kingdee-k3cloud-mcp) to the ERP / Business Tools section.

**What it does:**  
MCP Server for Kingdee K3Cloud (金蝶云星空) — one of the most widely used ERP systems in China. Connects AI assistants (Claude Desktop, Cursor, Cline, Cherry Studio, etc.) to Kingdee ERP via natural language.

**Key features:**
- 15 MCP tools covering query, bulk export, create, submit, audit, unaudit, push-down
- Universal `form_id` parameter supports all Kingdee form types (sales orders, purchase orders, inventory, materials, customers, etc.)
- Auto-pagination helpers (`query_bill_all`, `query_bill_range`) — no manual looping needed
- Read-only mode to prevent accidental writes
- Auto session recovery (handles Kingdee session timeouts transparently)
- Supports stdio, SSE, and streamable-http transports

**Stats:**  
- PyPI: https://pypi.org/project/kingdee-k3cloud-mcp/
- Stars: (growing)
- License: Apache-2.0
- Python 3.10–3.13

**Checklist:**
- [x] Followed the contribution guidelines
- [x] Added to the correct category
- [x] Link is functional
- [x] Description is concise and accurate
```

## 操作步骤

1. Fork https://github.com/punkpeye/awesome-mcp-servers
2. 在 README.md 中找到 ERP / Business 分类，插入上述条目（按字母顺序 `k` 位置）
3. Commit: `Add kingdee-k3cloud-mcp to ERP section`
4. 开 PR，使用上述标题和描述
