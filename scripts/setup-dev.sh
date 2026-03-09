#!/usr/bin/env bash
# setup-dev.sh — First-time developer setup (Linux / macOS / Git Bash on Windows)
# Run once after cloning: bash scripts/setup-dev.sh
set -e

echo "==> Initializing git repository ..."
git config core.hooksPath .githooks
echo "    ✓ Git hooks path configured to .githooks"

echo ""
echo "==> Making hooks executable ..."
chmod +x .githooks/* 2>/dev/null || true
echo "    ✓ Hook permissions fixed"

echo ""
echo "==> Initializing git submodules ..."
git submodule update --init --recursive
echo "    ✓ Submodules initialized"

echo ""
echo "==> Installing Python dev dependencies ..."
pip install -e ".[dev]"
echo "    ✓ Dependencies installed"

echo ""
echo "==> Verifying hook installation ..."
HOOK_PATH=$(git config core.hooksPath)
if [ "$HOOK_PATH" = ".githooks" ]; then
    echo "    ✓ Git hooks path: $HOOK_PATH"
else
    echo "    ✗ Git hooks path not configured: $HOOK_PATH"
    exit 1
fi

echo ""
echo "✅ Setup complete! Git hooks and dependencies are ready."
echo ""
echo "Next steps:"
echo "  • Run 'pre-commit run --all-files' to verify all quality gates pass"
echo "  • Commit and push — hooks will run automatically on commit and push"
echo ""
echo "To reinstall hooks at any time: git config core.hooksPath .githooks"
