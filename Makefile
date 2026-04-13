.PHONY: test lint format build dev

test:
	uv run pytest --cov=src --cov-report=term-missing

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run ruff format src/ tests/
	uv run ruff check src/ tests/ --fix

build:
	uv build
	uv run --with twine twine check dist/*

dev:
	uv run python -m kingdee_k3cloud_mcp
