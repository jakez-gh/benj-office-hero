# setup-dev.ps1 — First-time developer setup (Windows PowerShell)
# Run once after cloning: .\scripts\setup-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "==> Initializing git repository ..." -ForegroundColor Cyan
git config core.hooksPath .githooks
Write-Host "    ✓ Git hooks path configured to .githooks"

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
