#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run all local quality gates.

.DESCRIPTION
    Executes the full local quality gate suite in order:
      1. pre-commit (lint, format, security)
      2. pytest with coverage (if tests exist)

    On failure prints a clear error summary.

.EXAMPLE
    .\scripts\qa_gate.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"

    # ── Gate 1: pre-commit ────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "=== GATE 1: pre-commit (lint + format + security) ===" -ForegroundColor Cyan
    python -m pre_commit run --all-files
    $gate1 = $LASTEXITCODE

    # ── Gate 2: pytest ────────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "=== GATE 2: pytest (coverage) ===" -ForegroundColor Cyan
    $testFiles = Get-ChildItem -Path tests -Filter "test_*.py" -Recurse -ErrorAction SilentlyContinue
    if ($testFiles.Count -gt 0) {
        python -m pytest -q --tb=short
        $gate2 = $LASTEXITCODE
    } else {
        Write-Host "No test files found — skipping pytest." -ForegroundColor Yellow
        $gate2 = 0
    }

    # ── Results ───────────────────────────────────────────────────────────────
    Write-Host ""
    $pass1 = $gate1 -eq 0
    $pass2 = $gate2 -eq 0

    Write-Host "Gate results:"
    Write-Host ("  [$(if ($pass1) {'PASS'} else {'FAIL'})] pre-commit") `
        -ForegroundColor $(if ($pass1) { "Green" } else { "Red" })
    Write-Host ("  [$(if ($pass2) {'PASS'} else {'FAIL'})] pytest") `
        -ForegroundColor $(if ($pass2) { "Green" } else { "Red" })

    if (-not ($pass1 -and $pass2)) {
        Write-Host ""
        Write-Host "QUALITY GATE FAILED." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "All gates PASSED." -ForegroundColor Green

} finally {
    Pop-Location
}
