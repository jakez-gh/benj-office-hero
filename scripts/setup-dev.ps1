# setup-dev.ps1 — First-time developer setup (Windows PowerShell)
# Run once after cloning: .\scripts\setup-dev.ps1

$ErrorActionPreference = "Stop"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
}
function Write-Success {
    param([string]$Text)
    Write-Host "  ✓ $Text" -ForegroundColor Green
}
function Write-Warn {
    param([string]$Text)
    Write-Host "  ⚠️  $Text" -ForegroundColor Yellow
}
function Write-Err {
    param([string]$Text)
    Write-Host "  ❌ $Text" -ForegroundColor Red
}

Write-Header "Office Hero Development Setup"

# 1. Configure Git hooks
Write-Host ""
Write-Host "1️⃣  Configuring Git hooks..." -ForegroundColor Cyan
git config core.hooksPath .githooks
if ($LASTEXITCODE -eq 0) {
    Write-Success "Git hooks path configured (.githooks)"
} else {
    Write-Err "Failed to configure git hooks"
    exit 1
}

# 2. Make hooks executable (no-op on Windows but harmless)
Write-Host ""
Write-Host "2️⃣  Preparing hook scripts..." -ForegroundColor Cyan
Get-ChildItem ".githooks" -File | ForEach-Object {
    Write-Success "$($_.Name) ready"
}

# 3. Initialize submodules
Write-Host ""
Write-Host "3️⃣  Initializing git submodules..." -ForegroundColor Cyan
git submodule update --init --recursive
Write-Success "Submodules initialized"

# 4. Install Python dev dependencies
Write-Host ""
Write-Host "4️⃣  Installing Python dev dependencies..." -ForegroundColor Cyan
pip install -e ".[dev]"
Write-Success "Python dependencies installed"

# 5. Install Node dependencies
Write-Host ""
Write-Host "5️⃣  Installing Node.js dependencies..." -ForegroundColor Cyan
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    pnpm install
    Write-Success "Node dependencies installed with pnpm"
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    npm install
    Write-Success "Node dependencies installed with npm"
} else {
    Write-Warn "npm/pnpm not found — skipping Node dependency installation"
}

# 6. Environment file
Write-Host ""
Write-Host "6️⃣  Environment configuration..." -ForegroundColor Cyan
if (Test-Path "apps/tech-mobile/.env.local") {
    Write-Success ".env.local already configured"
} else {
    Write-Warn ".env.local not found — creating with development defaults"
    New-Item -ItemType Directory -Force -Path "apps/tech-mobile" | Out-Null
    $envContent = @"
# Backend API endpoint for development
# This connects to the local backend server (auto-started by git hooks)
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
"@
    Set-Content -Path "apps/tech-mobile/.env.local" -Value $envContent
    Write-Success ".env.local created"
}

# 7. Pre-commit framework (optional)
Write-Host ""
Write-Host "7️⃣  Setting up pre-commit framework..." -ForegroundColor Cyan
if (Get-Command pre-commit -ErrorAction SilentlyContinue) {
    pre-commit install
    Write-Success "pre-commit framework installed"
} else {
    Write-Warn "pre-commit not installed (optional) — install with: pip install pre-commit"
}

# 8. Verify hook installation
Write-Host ""
Write-Host "8️⃣  Verifying hook installation..." -ForegroundColor Cyan
$hookPath = git config core.hooksPath
if ($hookPath -eq ".githooks") {
    Write-Success "Git hooks path: $hookPath"
} else {
    Write-Err "Git hooks path not configured correctly: '$hookPath'"
    exit 1
}

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Header "✅ Setup Complete!"
Write-Host ""
Write-Host "Git hooks active:" -ForegroundColor Cyan
Write-Host "  🔧 pre-commit      — Linting + security checks before commits" -ForegroundColor Gray
Write-Host "  📝 commit-msg      — Reserved for future commit message validation" -ForegroundColor Gray
Write-Host "  🚀 pre-push        — Tests + bandit + pip-audit before push" -ForegroundColor Gray
Write-Host "  🔄 post-merge      — Auto-start backend after pulling changes" -ForegroundColor Gray
Write-Host "  🌿 post-checkout   — Verify environment when switching branches" -ForegroundColor Gray
Write-Host ""
Write-Host "Common commands:" -ForegroundColor Cyan
Write-Host "  pnpm install                       — Install all dependencies" -ForegroundColor Gray
Write-Host "  pnpm --filter tech-mobile start    — Start Expo dev server" -ForegroundColor Gray
Write-Host "  pre-commit run --all-files         — Run all quality gates now" -ForegroundColor Gray
Write-Host ""
Write-Host "Docs:" -ForegroundColor Cyan
Write-Host "  📖 docs/hooks-rehydration.md       — Detailed rehydration guide" -ForegroundColor Gray
Write-Host ""
Write-Host "To reinstall hooks at any time: git config core.hooksPath .githooks" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:"
Write-Host "  • Run 'pre-commit run --all-files' to verify all quality gates pass"
Write-Host "  • Commit and push — hooks will run automatically on commit and push"
Write-Host ""
Write-Host "To reinstall hooks at any time: git config core.hooksPath .githooks" -ForegroundColor Gray
