# Integration Testing & Demo Recording Script (Windows)
# Run complete E2E testing and capture demo video

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Office Hero Frontend - E2E Testing Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Verify dependencies
Write-Host "`n✓ Checking environment..." -ForegroundColor Green
node --version
npm --version
pnpm --version

# 2. Install dependencies (fresh from lock file)
Write-Host "`n✓ Installing dependencies..." -ForegroundColor Green
pnpm install --frozen-lockfile

# 3. Verify backend is running
Write-Host "`n✓ Checking backend availability..." -ForegroundColor Green
try {
  $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -ErrorAction Stop
  Write-Host "✓ Backend health: $($response.Content)" -ForegroundColor Green
} catch {
  Write-Host "✗ Backend not running on http://localhost:8000" -ForegroundColor Red
  Write-Host "  Please start backend: cd ..\office-hero-backend-core" -ForegroundColor Yellow
  Write-Host "  Then: powershell -Command `"`$env:DATABASE_URL='postgresql+asyncpg://postgres:pass@localhost:5432/test'; python -m uvicorn src.office_hero.main:app --host 0.0.0.0 --port 8000`"" -ForegroundColor Yellow
  exit 1
}

# 4. Verify frontend dev server is running
Write-Host "`n✓ Checking frontend dev server..." -ForegroundColor Green
try {
  $null = Invoke-WebRequest -Uri "http://localhost:3000" -ErrorAction Stop
  Write-Host "✓ Frontend accessible at http://localhost:3000" -ForegroundColor Green
} catch {
  Write-Host "  Starting frontend dev server..." -ForegroundColor Yellow
  Push-Location apps/admin-web
  Start-Process -NoNewWindow pnpm -ArgumentList "dev"
  Pop-Location
  Start-Sleep -Seconds 3
}

# 5. Run E2E tests with video recording
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Running E2E Tests with Recording" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

cd apps/admin-web

# Run tests with video enabled
pnpm exec playwright test --project=chromium --record-video=on

# 6. Display results
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (Test-Path "playwright-report") {
  Write-Host "✓ Test report generated in: playwright-report/" -ForegroundColor Green
  Write-Host "✓ Open in browser: npx playwright show-report" -ForegroundColor Green
}

if (Test-Path "test-results") {
  Write-Host "✓ Video recordings in: test-results/" -ForegroundColor Green
  Get-ChildItem test-results -Filter "*.webm" | ForEach-Object {
    Write-Host "  - Recording: $($_.Name)" -ForegroundColor Green
  }
}

Write-Host ""
Write-Host "To view test report:" -ForegroundColor Yellow
Write-Host "  cd apps/admin-web" -ForegroundColor Yellow
Write-Host "  npx playwright show-report" -ForegroundColor Yellow
