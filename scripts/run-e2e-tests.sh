#!/bin/bash
# Integration Testing & Demo Recording Script
# Run complete E2E testing and capture demo video

set -e

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

# 3. Verify backend is running
echo "✓ Checking backend availability..."
if ! curl -s http://localhost:8000/health > /dev/null; then
  echo "✗ Backend not running on http://localhost:8000"
  echo "  Please start backend: cd ../office-hero-backend-core && python -m uvicorn src.office_hero.main:app --host 0.0.0.0 --port 8000"
  exit 1
fi
echo "✓ Backend health: $(curl -s http://localhost:8000/health)"

# 4. Verify frontend dev server is running
echo "✓ Checking frontend dev server..."
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
  echo "  Starting frontend dev server..."
  pnpm dev &
  sleep 3
fi
echo "✓ Frontend accessible at http://localhost:3000"

# 5. Run E2E tests with video recording
echo ""
echo "=========================================="
echo "Running E2E Tests with Recording"
echo "=========================================="

cd apps/admin-web

# Run tests with video enabled
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
