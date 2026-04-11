# Contributing to kingdee-k3cloud-mcp

Thank you for your interest in contributing!

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Access to a Kingdee K3Cloud instance (for manual testing)

## Setup

```bash
git clone https://github.com/adamzhang1987/kingdee-k3cloud-mcp.git
cd kingdee-k3cloud-mcp
uv sync
```

## Running Tests

```bash
uv run pytest
```

## Making Changes

1. Fork the repo and create a feature branch from `main`
2. Make your changes
3. Add or update tests if applicable
4. Run `uv run pytest` to ensure tests pass
5. Submit a pull request

## Reporting Issues

Please open an issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Kingdee K3Cloud version if relevant

## Security Issues

Please do **not** open public issues for security vulnerabilities. See [SECURITY.md](SECURITY.md) instead.
