# setup-dev.ps1 — First-time developer setup (Windows PowerShell)
# Run once after cloning: .\scripts\setup-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "==> Initializing git repository ..." -ForegroundColor Cyan
git config core.hooksPath .githooks
Write-Host "    ✓ Git hooks path configured to .githooks"

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor Red
}

Write-Header "Office Hero Mobile Development Setup"

# 1. Configure Git hooks
Write-Host ""
Write-Host "1️⃣  Configuring Git hooks..." -ForegroundColor Cyan
git config core.hooksPath .githooks
if ($LASTEXITCODE -eq 0) {
    Write-Success "Git hooks path configured (.githooks)"
} else {
    Write-Error-Custom "Failed to configure git hooks"
    exit 1
}

# 2. Make hooks executable
Write-Host ""
Write-Host "2️⃣  Preparing hook scripts..." -ForegroundColor Cyan
Get-ChildItem ".githooks" -File | ForEach-Object {
    Write-Success "$($_.Name) ready"
}

# 3. Install Node dependencies
Write-Host ""
Write-Host "3️⃣  Installing Node.js dependencies..." -ForegroundColor Cyan
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    pnpm install
    Write-Success "Dependencies installed with pnpm"
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    npm install
    Write-Success "Dependencies installed with npm"
} else {
    Write-Warning "npm/pnpm not found - skipping Node dependency installation"
}

# 4. Backend setup info
Write-Host ""
Write-Host "4️⃣  Backend configuration..." -ForegroundColor Cyan
Write-Host "The backend will start automatically via git hooks when you:" -ForegroundColor Gray
Write-Host "  • Pull changes: post-merge hook auto-starts backend if needed" -ForegroundColor Gray
Write-Host "  • Checkout branches: post-checkout hook verifies environment" -ForegroundColor Gray
Write-Success "Backend auto-startup configured"

# 5. Environment file
Write-Host ""
Write-Host "5️⃣  Environment configuration..." -ForegroundColor Cyan
if (Test-Path "apps/tech-mobile/.env.local") {
    Write-Success ".env.local already configured"
} else {
    Write-Warning ".env.local not found - creating with development defaults"
    $envContent = @"
# Backend API endpoint for development
# This connects to the local backend server (auto-started by git hooks)
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
"@
    Set-Content -Path "apps/tech-mobile/.env.local" -Value $envContent
    Write-Success ".env.local created"
}

# 6. Pre-commit setup
Write-Host ""
Write-Host "6️⃣  Setting up commit hooks..." -ForegroundColor Cyan
if (Get-Command pre-commit -ErrorAction SilentlyContinue) {
    pre-commit install
    Write-Success "pre-commit framework installed"
} else {
    Write-Warning "pre-commit not installed (optional)"
    Write-Host "Install with: pip install pre-commit" -ForegroundColor Gray
}

# Summary
Write-Header "✅ Setup Complete!"
Write-Host ""
Write-Host "Available commands:" -ForegroundColor Cyan
Write-Host "  • pnpm install              - Install all dependencies" -ForegroundColor Gray
Write-Host "  • pnpm --filter tech-mobile start  - Start Expo dev server" -ForegroundColor Gray
Write-Host "  • git pull                  - Backend auto-starts via post-merge hook" -ForegroundColor Gray
Write-Host ""
Write-Host "Git hooks configured:" -ForegroundColor Cyan
Write-Host "  🔧 pre-commit      - Linting + security checks before commits" -ForegroundColor Gray
Write-Host "  🔄 post-merge      - Auto-start backend after pulling changes" -ForegroundColor Gray
Write-Host "  🌿 post-checkout   - Verify environment when switching branches" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  📖 See SETUP.md for detailed rehydration instructions" -ForegroundColor Gray
Write-Host ""
Write-Host "==> Initializing git submodules ..." -ForegroundColor Cyan
git submodule update --init --recursive
Write-Host "    ✓ Submodules initialized"

Write-Host ""
Write-Host "==> Installing Python dev dependencies ..." -ForegroundColor Cyan
pip install -e ".[dev]"
Write-Host "    ✓ Dependencies installed"

Write-Host ""
Write-Host "==> Verifying hook installation ..." -ForegroundColor Cyan
$hookPath = git config core.hooksPath
if ($hookPath -eq ".githooks") {
    Write-Host "    ✓ Git hooks path: $hookPath"
} else {
    Write-Host "    ✗ Git hooks path not configured" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Setup complete! Git hooks and dependencies are ready." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  • Run 'pre-commit run --all-files' to verify all quality gates pass"
Write-Host "  • Commit and push — hooks will run automatically on commit and push"
Write-Host ""
Write-Host "To reinstall hooks at any time: git config core.hooksPath .githooks" -ForegroundColor Gray
