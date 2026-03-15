#!/bin/bash
# Integration Testing & Demo Recording Script
# Run complete E2E testing and capture demo video

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo "Office Hero Frontend - E2E Testing Setup"
echo "=========================================="

# 1. Verify dependencies
echo "✓ Checking environment..."
node --version
npm --version
pnpm --version

# 2. Install dependencies (fresh from lock file)
echo "✓ Installing dependencies..."
pnpm install --frozen-lockfile

# 3. Start managed backend+frontend with random conflict-safe ports
echo "✓ Starting managed test servers..."
python3 tools/server_manager.py start

cleanup() {
  python3 tools/server_manager.py stop --quiet || true
}
trap cleanup EXIT

source .runtime/test-ports.env

# 4. Verify randomized server health
echo "✓ Checking backend availability..."
curl -s "http://127.0.0.1:${BACKEND_PORT}/health" > /dev/null
echo "✓ Backend available on ${BACKEND_PORT}"

echo "✓ Checking frontend availability..."
curl -s "http://127.0.0.1:${FRONTEND_PORT}" > /dev/null
echo "✓ Frontend available on ${FRONTEND_PORT}"

# 5. Run E2E tests with video recording
echo ""
echo "=========================================="
echo "Running E2E Tests with Recording"
echo "=========================================="

cd apps/admin-web

# Run tests with video enabled
PLAYWRIGHT_BASE_URL="http://127.0.0.1:${FRONTEND_PORT}" \
SKIP_PLAYWRIGHT_WEBSERVER=1 \
pnpm exec playwright test --project=chromium --record-video=on

# 6. Display results
echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
if [ -d "playwright-report" ]; then
  echo "✓ Test report generated in: playwright-report/"
  echo "✓ Open in browser: npx playwright show-report"
fi

if [ -d "test-results" ]; then
  echo "✓ Video recordings in: test-results/"
fi

echo ""
echo "To view test report:"
echo "  cd apps/admin-web"
echo "  npx playwright show-report"
