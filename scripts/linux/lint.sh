#!/bin/bash
set -euo pipefail

# Wildcards-gen Local Linting Script
# Runs formatting checks, linting, and type checking in the correct order.

echo "--- Running Ruff Format Check ---"
uv run ruff format --check .

echo "--- Running Ruff Lint Check ---"
uv run ruff check .

echo "--- Running Mypy Type Check ---"
uv run mypy .

echo "--- All checks passed! ---"
