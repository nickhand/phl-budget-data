default:
    just --list

# Format code (autofix)
fmt:
    uv run ruff format packages/
    uv run ruff check --fix packages/

# Lint only (no autofix — for CI)
lint:
    uv run ruff format --check packages/
    uv run ruff check packages/

# Type check both packages
typecheck:
    uv run mypy

# Run all checks
check: lint typecheck
