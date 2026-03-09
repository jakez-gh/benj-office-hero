#!/usr/bin/env pwsh
# start-backend.ps1 — Start Office Hero FastAPI development server
#
# Prerequisites:
#   1. Copy .env.example to .env and fill in real values (DATABASE_URL, JWT keys)
#   2. Run: pip install -e ".[dev]"
#
# Usage:
#   .\scripts\start-backend.ps1

$ErrorActionPreference = "Stop"

# ── Load .env if it exists ────────────────────────────────────────────────────
$EnvFile = Join-Path $PSScriptRoot ".." ".env"
if (Test-Path $EnvFile) {
    Write-Host "Loading environment from .env ..." -ForegroundColor DarkGray
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*([A-Z_][A-Z0-9_]*)=(.+)$" -and $_ -notmatch "^\s*#") {
            [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"').Trim("'"))
        }
    }
} else {
    Write-Warning ".env not found. Ensure DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY are exported."
    Write-Warning "Copy .env.example to .env and fill in real values."
}

# ── Validate required vars are set ───────────────────────────────────────────
foreach ($var in @("DATABASE_URL", "JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY")) {
    if (-not [System.Environment]::GetEnvironmentVariable($var)) {
        Write-Error "Required environment variable '$var' is not set. Aborting."
        exit 1
    }
}

# ── Start server ─────────────────────────────────────────────────────────────
Write-Host "Starting Office Hero API on http://localhost:8000 ..." -ForegroundColor Cyan
Write-Host "  Docs: http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host "  Health: http://localhost:8000/health" -ForegroundColor DarkGray
Write-Host ""

$env:PYTHONPATH = Join-Path $PSScriptRoot ".." "src"
python -m uvicorn office_hero.main:app --reload --host 127.0.0.1 --port 8000
