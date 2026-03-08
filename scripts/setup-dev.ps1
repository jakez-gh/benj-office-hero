# setup-dev.ps1 — First-time developer setup (Windows PowerShell)
# Run once after cloning:  .\scripts\setup-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "==> Activating git hooks from .githooks/ ..." -ForegroundColor Cyan
git config core.hooksPath .githooks

Write-Host "==> Installing Python dev dependencies ..." -ForegroundColor Cyan
pip install -e ".[dev]"

Write-Host ""
Write-Host "Done. Git hooks are active." -ForegroundColor Green
Write-Host "Run 'pre-commit run --all-files' to verify all checks pass."
