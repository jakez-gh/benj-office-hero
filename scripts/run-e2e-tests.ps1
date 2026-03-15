# Integration Testing & Demo Recording Script (Windows)
# Run complete E2E testing and capture demo video

$ErrorActionPreference = "Stop"
$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RootDir

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

# 3. Start managed backend+frontend with random ports
Write-Host "`n✓ Starting managed test servers..." -ForegroundColor Green
python tools/server_manager.py start

try {
  $ports = @{}
  Get-Content ".runtime/test-ports.env" | ForEach-Object {
    if ($_ -match "^\s*([A-Z_]+)=(.+)$") {
      $ports[$Matches[1]] = $Matches[2]
    }
  }

  $backendPort = $ports["BACKEND_PORT"]
  $frontendPort = $ports["FRONTEND_PORT"]

  if (-not $backendPort -or -not $frontendPort) {
    throw "Managed ports file missing BACKEND_PORT/FRONTEND_PORT"
  }

  # 4. Verify randomized server health
  Write-Host "`n✓ Checking backend availability..." -ForegroundColor Green
  $null = Invoke-WebRequest -Uri "http://127.0.0.1:$backendPort/health" -ErrorAction Stop
  Write-Host "✓ Backend available on $backendPort" -ForegroundColor Green

  Write-Host "`n✓ Checking frontend availability..." -ForegroundColor Green
  $null = Invoke-WebRequest -Uri "http://127.0.0.1:$frontendPort" -ErrorAction Stop
  Write-Host "✓ Frontend available on $frontendPort" -ForegroundColor Green

# 5. Run E2E tests with video recording
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Running E2E Tests with Recording" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

  cd apps/admin-web

  # Run tests with video enabled
  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:$frontendPort"
  $env:SKIP_PLAYWRIGHT_WEBSERVER = "1"
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
}
finally {
  Set-Location $RootDir
  python tools/server_manager.py stop --quiet
}
