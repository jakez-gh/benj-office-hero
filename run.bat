@echo off
REM run.bat — Start the Office Hero development stack (Windows)
REM
REM Usage:
REM   run.bat              — start backend + frontend (dev, hot-reload)
REM   run.bat --prod       — build frontend if needed, serve production preview
REM   run.bat --backend    — backend only
REM   run.bat --frontend   — frontend only
REM   run.bat --port 9000  — backend on a specific port (default: 8000)
REM   run.bat --help       — show this help
REM
REM First run on a fresh clone:
REM   1. copy .env.example .env
REM   2. Edit .env and set DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY
REM   3. run.bat
REM
REM NOTE: This script opens two separate console windows for backend and
REM frontend. Close both windows (or this window) to stop all services.

setlocal enabledelayedexpansion

REM ── Handle --help ─────────────────────────────────────────────────────────────
if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help
goto :parse_args

:show_help
echo Office Hero — development runner
echo.
echo Usage:
echo   run.bat                  Start backend + frontend ^(dev mode^)
echo   run.bat --prod           Build frontend ^(if needed^) + production preview
echo   run.bat --backend        Backend only
echo   run.bat --frontend       Frontend only
echo   run.bat --port 9000      Backend on a specific port ^(default: 8000^)
echo   run.bat --help           This help text
echo.
echo Prerequisites:
echo   - Python 3.11+  https://python.org
echo   - Poetry        https://python-poetry.org/docs/#installation
echo   - Node.js 18+   https://nodejs.org
echo   - pnpm          npm install -g pnpm
exit /b 0

REM ── Parse arguments ───────────────────────────────────────────────────────────
:parse_args
set MODE=dev
set DO_BACKEND=1
set DO_FRONTEND=1
set BACKEND_PORT=8000

:arg_loop
if "%~1"=="" goto :args_done
if "%~1"=="--prod"     set MODE=prod
if "%~1"=="--backend"  set DO_FRONTEND=0
if "%~1"=="--frontend" set DO_BACKEND=0
if "%~1"=="--port" (
    set BACKEND_PORT=%~2
    shift
)
shift
goto :arg_loop
:args_done

REM ── Project root ─────────────────────────────────────────────────────────────
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo ── Checking prerequisites ──
where poetry >nul 2>&1 || (
    echo   [MISSING] poetry not found.
    echo   Install from: https://python-poetry.org/docs/#installation
    exit /b 1
)
where pnpm >nul 2>&1 || (
    echo   [MISSING] pnpm not found.
    echo   Install via: npm install -g pnpm
    exit /b 1
)
for /f "tokens=*" %%v in ('poetry --version 2^>nul') do echo   OK  %%v
for /f "tokens=*" %%v in ('pnpm --version 2^>nul') do echo   OK  pnpm %%v

REM ── Python dependencies ───────────────────────────────────────────────────────
echo.
echo ── Python dependencies ──
set VENV_DIR=%SCRIPT_DIR%.venv
set VENV_STAMP=%VENV_DIR%\.installed_at
set INSTALL_PYTHON=0

if not exist "%VENV_DIR%" set INSTALL_PYTHON=1

if %INSTALL_PYTHON%==0 (
    if not exist "%VENV_STAMP%" set INSTALL_PYTHON=1
)
if %INSTALL_PYTHON%==0 (
    for %%A in ("%SCRIPT_DIR%poetry.lock") do set LOCK_MOD=%%~tA
    for %%A in ("%VENV_STAMP%") do set STAMP_MOD=%%~tA
    if "!LOCK_MOD!" gtr "!STAMP_MOD!" set INSTALL_PYTHON=1
)

if %INSTALL_PYTHON%==1 (
    echo   Running: poetry install --with dev
    call poetry install --with dev --no-interaction
    if errorlevel 1 (
        echo   [ERROR] poetry install failed
        exit /b 1
    )
    type nul > "%VENV_STAMP%"
    echo   OK  Python dependencies installed
) else (
    echo   OK  Python dependencies up to date
)

REM ── Node dependencies ─────────────────────────────────────────────────────────
echo.
echo ── Node dependencies ──
set NODE_MODULES=%SCRIPT_DIR%node_modules
set NODE_STAMP=%NODE_MODULES%\.installed_at
set INSTALL_NODE=0

if not exist "%NODE_MODULES%" set INSTALL_NODE=1

if %INSTALL_NODE%==0 (
    if not exist "%NODE_STAMP%" set INSTALL_NODE=1
)
if %INSTALL_NODE%==0 (
    for %%A in ("%SCRIPT_DIR%pnpm-lock.yaml") do set LOCK_MOD=%%~tA
    for %%A in ("%NODE_STAMP%") do set STAMP_MOD=%%~tA
    if "!LOCK_MOD!" gtr "!STAMP_MOD!" set INSTALL_NODE=1
)

if %INSTALL_NODE%==1 (
    echo   Running: pnpm install
    call pnpm install --frozen-lockfile
    if errorlevel 1 (
        echo   [ERROR] pnpm install failed
        exit /b 1
    )
    type nul > "%NODE_STAMP%"
    echo   OK  Node dependencies installed
) else (
    echo   OK  Node dependencies up to date
)

REM ── Environment file ──────────────────────────────────────────────────────────
echo.
echo ── Environment ──
if not exist "%SCRIPT_DIR%.env" (
    copy "%SCRIPT_DIR%.env.example" "%SCRIPT_DIR%.env" >nul
    echo   WARN  .env created from .env.example
    echo   WARN  Edit .env and set DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY
    echo   WARN  Re-run run.bat when ready.
    if %DO_BACKEND%==1 (
        echo.
        exit /b 0
    )
)

REM Load .env into environment
for /f "usebackq tokens=1,* delims==" %%a in ("%SCRIPT_DIR%.env") do (
    set LINE=%%a
    if not "!LINE:~0,1!"=="#" (
        if not "%%a"=="" (
            set "%%a=%%b"
        )
    )
)
echo   OK  .env loaded

REM ── Database migrations ───────────────────────────────────────────────────────
if %DO_BACKEND%==1 (
    if not "%DATABASE_URL%"=="" (
        echo.
        echo ── Database migrations ──
        echo   Running: alembic upgrade head
        call poetry run alembic upgrade head
        if errorlevel 1 (
            echo   [ERROR] migrations failed
            exit /b 1
        )
        echo   OK  Migrations applied
    )
)

REM ── Frontend build (prod mode only) ──────────────────────────────────────────
if "%MODE%"=="prod" (
    if %DO_FRONTEND%==1 (
        echo.
        echo ── Frontend build ──
        if not exist "%SCRIPT_DIR%apps\admin-web\dist\index.html" (
            set BUILD_NEEDED=1
        ) else (
            set BUILD_NEEDED=0
        )
        if !BUILD_NEEDED!==1 (
            echo   Running: pnpm --filter admin-web build
            call pnpm --filter admin-web build
            if errorlevel 1 (
                echo   [ERROR] frontend build failed
                exit /b 1
            )
            echo   OK  Frontend built to apps/admin-web/dist/
        ) else (
            echo   OK  Frontend build is current — skipping
        )
    )
)

REM ── Start services ────────────────────────────────────────────────────────────
echo.
echo ── Starting services ──

set VITE_API_BASE_URL=http://127.0.0.1:%BACKEND_PORT%
if not defined OFFICE_HERO_TEST_AUTH set OFFICE_HERO_TEST_AUTH=1

if %DO_BACKEND%==1 (
    set PYTHONPATH=%SCRIPT_DIR%src
    echo   OK  Backend  -^> http://127.0.0.1:%BACKEND_PORT%
    echo       Docs:    http://127.0.0.1:%BACKEND_PORT%/docs
    echo       Health:  http://127.0.0.1:%BACKEND_PORT%/health
    start "Office Hero — Backend" cmd /k "cd /d %SCRIPT_DIR% && set OFFICE_HERO_TEST_AUTH=%OFFICE_HERO_TEST_AUTH% && set PYTHONPATH=%PYTHONPATH% && poetry run uvicorn office_hero.main:app --reload --host 127.0.0.1 --port %BACKEND_PORT% --log-level info"
    timeout /t 2 /nobreak >nul
)

if %DO_FRONTEND%==1 (
    echo   OK  Frontend -^> http://127.0.0.1:3000
    if "%MODE%"=="prod" (
        start "Office Hero — Frontend" cmd /k "cd /d %SCRIPT_DIR% && set VITE_API_BASE_URL=%VITE_API_BASE_URL% && pnpm --filter admin-web exec vite preview --port 3000 --host 127.0.0.1"
    ) else (
        start "Office Hero — Frontend" cmd /k "cd /d %SCRIPT_DIR% && set VITE_API_BASE_URL=%VITE_API_BASE_URL% && pnpm --filter admin-web exec vite --port 3000 --host 127.0.0.1"
    )
)

echo.
echo Services started in separate windows.
echo Close those windows or press Ctrl+C here to stop.
pause
