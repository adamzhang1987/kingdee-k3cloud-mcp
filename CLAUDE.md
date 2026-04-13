# Claude Code 工作指南 — kingdee-k3cloud-mcp

## 项目概述

金蝶云星空 MCP Server，基于 FastMCP + kingdee-cdp-webapi-sdk，发布到 PyPI。

## 每次 commit & push 后的版本检查

完成修改并推送后，**必须主动判断**是否需要升版本号和发布，不要等用户询问。

| 变更类型 | 版本策略 | 是否 Release |
|---------|---------|-------------|
| 新增 MCP tool | minor bump（1.0.x → 1.1.0） | 是 |
| 返回格式/行为变更（影响调用方） | minor bump | 是 |
| Bug fix | patch bump（1.1.0 → 1.1.1） | 是 |
| Breaking change（删除 tool / 入参不兼容） | major bump（1.x → 2.0.0） | 是 |
| 仅文档 / 注释 / 测试 | 不变 | 否 |

### 发布步骤

1. 更新 `pyproject.toml` 中 `version`
2. 将 `CHANGELOG.md` 的 `[Unreleased]` 改为 `[X.Y.Z] - YYYY-MM-DD`，补充底部 compare URL
3. `git add pyproject.toml CHANGELOG.md && git commit`
4. `git tag vX.Y.Z && git push && git push origin vX.Y.Z`
   → 触发 GitHub Actions Release workflow → 自动发布到 PyPI

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/kingdee_k3cloud_mcp/server.py` | 所有 MCP tool 定义 |
| `pyproject.toml` | 版本号、依赖 |
| `CHANGELOG.md` | 每次 release 必须更新 |
| `tests/test_server.py` | 单元测试，新增 tool 需补测试 |

## 与 skill repo 的关系

新增 MCP tool 后，通常需要同步更新 `kingdee-k3cloud-skill` 的 SKILL.md 决策树或字段文档。
