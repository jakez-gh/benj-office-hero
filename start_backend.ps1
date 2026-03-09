#!/usr/bin/env pwsh
# Start Office Hero FastAPI backend server

Write-Host "🚀 Starting Office Hero Backend Server..." -ForegroundColor Cyan

# Set environment variables from .env
$env:DATABASE_URL = "postgresql+asyncpg://postgres:pass@localhost:5432/test"
$env:JWT_PRIVATE_KEY = "private"
$env:JWT_PUBLIC_KEY = "public"
$env:JWT_ALGORITHM = "RS256"
$env:PYTHONPATH = "$PSScriptRoot\src"

# Change to backend directory
Set-Location $PSScriptRoot

# Start uvicorn
Write-Host "Starting FastAPI on 0.0.0.0:8000" -ForegroundColor Green
python -m uvicorn office_hero.main:app --reload --host 0.0.0.0 --port 8000
