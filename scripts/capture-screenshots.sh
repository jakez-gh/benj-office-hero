#!/usr/bin/env bash
# capture-screenshots.sh — regenerate admin-web UI screenshots into docs/.
#
# Part of the git-hook build pipeline (.githooks/pre-push): when a push touches
# the UI, screenshots are regenerated so docs/screenshots/admin-web/ always
# matches the rendered app. If anything changed, the fresh PNGs are staged and
# the push is aborted so they ride the next commit.
#
# Standalone use:    bash scripts/capture-screenshots.sh
# Skip in a hook:    OFFICE_HERO_SKIP_SCREENSHOTS=1 git push
#
# Prerequisites: pnpm install; npx playwright install chromium (one-time —
# scripts/setup-dev.ps1 step 9 handles it).

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

OUT_DIR="docs/screenshots/admin-web"

echo "📸 Capturing admin-web screenshots (Playwright/chromium)…"
(
    cd apps/admin-web
    # playwright.config.ts webServer boots vite and waits for :3000, reusing
    # a dev server that is already running.
    SCREENSHOT_DIR=screenshots npx playwright test src/e2e/screenshots.spec.ts \
        --project=chromium --reporter=line
)

mkdir -p "$OUT_DIR"
# Mirror (rsync is not guaranteed in git-bash on Windows).
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
cp -r apps/admin-web/screenshots/. "$OUT_DIR/"

if [ -n "$(git status --porcelain "$OUT_DIR")" ]; then
    git add "$OUT_DIR"
    echo ""
    echo "🖼  Screenshots changed — refreshed PNGs are staged."
    echo "   Commit them (e.g. git commit -m 'docs(screenshots): refresh admin-web screenshots')"
    echo "   and push again."
    exit 1
fi

echo "✅ Screenshots are up to date."
