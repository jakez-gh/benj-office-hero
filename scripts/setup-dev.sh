#!/usr/bin/env bash
# setup-dev.sh — First-time developer setup (Linux / macOS / Git Bash on Windows)
# Run once after cloning:  bash scripts/setup-dev.sh
set -e

echo "==> Activating git hooks from .githooks/ ..."
git config core.hooksPath .githooks

echo "==> Making hooks executable ..."
chmod +x .githooks/*

echo "==> Installing Python dev dependencies ..."
pip install -e ".[dev]"

echo ""
echo "Done. Git hooks are active."
echo "Run 'pre-commit run --all-files' to verify all checks pass."
