#!/usr/bin/env bash
# Idempotent environment setup for Power Query Quack.
#
# Installs the package with dev (test/lint) extras so `pytest` and `ruff` work.
# Used by the Claude Code SessionStart hook and is safe to run manually.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"

echo "🦆 Setting up Power Query Quack..."
"$PYTHON" -m pip install --quiet --upgrade pip
"$PYTHON" -m pip install --quiet -e ".[dev]"
echo "🦆 Setup complete. Run: pytest && ruff check ."
