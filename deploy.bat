@echo off
REM deploy.bat — Deploy Office Hero to Fly.io (Windows)
REM
REM Usage:
REM   deploy.bat              — deploy both API and web (interactive)
REM   deploy.bat --api-only   — deploy API only
REM   deploy.bat --web-only   — deploy web only
REM   deploy.bat --check      — verify prerequisites without deploying
REM   deploy.bat --non-interactive  — skip prompts (CI mode)
REM   deploy.bat --help       — show this help
REM
REM What this script does:
REM   1. Checks flyctl is installed and you are logged in
REM   2. Verifies both Fly.io apps exist
REM   3. Checks all required secrets are set (prompts for missing ones)
REM   4. Deploys API (migrations run automatically via release_command)
REM   5. Deploys web frontend
REM   6. Hits /health to confirm API is up
REM
REM Apps deployed:
REM   office-hero-api       (fly.api.toml)
REM   office-hero-admin-web (fly.toml)
REM
REM Required secrets for API:
REM   DATABASE_URL     Neon PostgreSQL connection string
REM   JWT_PRIVATE_KEY  RSA private key (PEM, \n-escaped)
REM   JWT_PUBLIC_KEY   Matching RSA public key (PEM, \n-escaped)
REM   ORS_API_KEY      OpenRouteService API key
REM
REM Optional: SENTRY_DSN (backend), VITE_SENTRY_DSN (frontend)
REM
REM For CI/CD: set FLY_API_TOKEN as a GitHub repo secret.
REM See .github/workflows/deploy.yml

setlocal enabledelayedexpansion

REM ── Handle --help ─────────────────────────────────────────────────────────────
if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help
goto :parse_args

:show_help
echo Office Hero — Fly.io deployment script
echo.
echo Usage:
echo   deploy.bat                   Deploy both API and web
echo   deploy.bat --api-only        Deploy API only
echo   deploy.bat --web-only        Deploy web only
echo   deploy.bat --check           Check prerequisites only
echo   deploy.bat --non-interactive Skip all prompts ^(CI mode^)
echo   deploy.bat --help            This help text
echo.
echo Prerequisites:
echo   flyctl    https://fly.io/install.sh
echo   fly auth login (then re-run this script)
echo.
echo Required Fly.io secrets (set once):
echo   DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, ORS_API_KEY
echo.
echo CI/CD: Add FLY_API_TOKEN to GitHub repo secrets.
echo See .github/workflows/deploy.yml for automated deploys.
exit /b 0

REM ── Parse arguments ───────────────────────────────────────────────────────────
:parse_args
set DEPLOY_API=1
set DEPLOY_WEB=1
set CHECK_ONLY=0
set NON_INTERACTIVE=0

:arg_loop
if "%~1"=="" goto :args_done
if "%~1"=="--api-only"        set DEPLOY_WEB=0
if "%~1"=="--web-only"        set DEPLOY_API=0
if "%~1"=="--check"           set CHECK_ONLY=1
if "%~1"=="--non-interactive" set NON_INTERACTIVE=1
shift
goto :arg_loop
:args_done

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"
set API_APP=office-hero-api
set WEB_APP=office-hero-admin-web

REM ── Step 1: flyctl ────────────────────────────────────────────────────────────
echo.
echo ── Checking flyctl ──
where flyctl >nul 2>&1
if errorlevel 1 (
    where fly >nul 2>&1
    if errorlevel 1 (
        echo   [MISSING] flyctl not found.
        echo.
        echo   Install flyctl:
        echo     PowerShell: iwr https://fly.io/install.ps1 -useb ^| iex
        echo     Chocolatey: choco install flyctl
        echo     Scoop:      scoop install flyctl
        exit /b 1
    )
    set FLY=fly
) else (
    set FLY=flyctl
)

for /f "tokens=*" %%v in ('!FLY! version 2^>nul') do (
    echo   OK  %%v
    goto :fly_version_done
)
:fly_version_done

REM ── Step 2: authentication ────────────────────────────────────────────────────
echo.
echo ── Fly.io authentication ──
!FLY! auth whoami >nul 2>&1
if errorlevel 1 (
    if %NON_INTERACTIVE%==1 (
        echo   [ERROR] Not logged in to Fly.io and --non-interactive mode is set.
        echo   Set FLY_API_TOKEN environment variable or run: flyctl auth login
        exit /b 1
    )
    echo   [WARN] Not logged in to Fly.io.
    set /p DOLOGIN=   Run 'flyctl auth login' now? [y/N]:
    if /i "!DOLOGIN!"=="y" (
        !FLY! auth login
    ) else (
        echo   Aborting. Please log in first: flyctl auth login
        exit /b 1
    )
) else (
    for /f "tokens=*" %%w in ('!FLY! auth whoami 2^>nul') do echo   OK  Logged in as: %%w
)

if %CHECK_ONLY%==1 (
    echo.
    echo ── Prerequisites OK ^(--check mode^) ──
    exit /b 0
)

REM ── Step 3: verify apps ───────────────────────────────────────────────────────
echo.
echo ── Fly.io apps ──

if %DEPLOY_API%==1 (
    !FLY! apps list 2>nul | findstr /i "%API_APP%" >nul
    if errorlevel 1 (
        echo   [WARN] App '%API_APP%' does not exist.
        if %NON_INTERACTIVE%==1 (
            echo   Creating app...
            !FLY! apps create %API_APP% --org personal
        ) else (
            set /p CREATEAPI=   Create app '%API_APP%' on Fly.io now? [y/N]:
            if /i "!CREATEAPI!"=="y" (
                !FLY! apps create %API_APP% --org personal
                echo   OK  Created: %API_APP%
            ) else (
                echo   Aborting — app required.
                exit /b 1
            )
        )
    ) else (
        echo   OK  App exists: %API_APP%
    )
)

if %DEPLOY_WEB%==1 (
    !FLY! apps list 2>nul | findstr /i "%WEB_APP%" >nul
    if errorlevel 1 (
        echo   [WARN] App '%WEB_APP%' does not exist.
        if %NON_INTERACTIVE%==1 (
            echo   Creating app...
            !FLY! apps create %WEB_APP% --org personal
        ) else (
            set /p CREATEWEB=   Create app '%WEB_APP%' on Fly.io now? [y/N]:
            if /i "!CREATEWEB!"=="y" (
                !FLY! apps create %WEB_APP% --org personal
                echo   OK  Created: %WEB_APP%
            ) else (
                echo   Aborting — app required.
                exit /b 1
            )
        )
    ) else (
        echo   OK  App exists: %WEB_APP%
    )
)

REM ── Step 4: check required secrets ───────────────────────────────────────────
echo.
echo ── Fly.io secrets (%API_APP%) ──

if %DEPLOY_API%==1 (
    for %%S in (DATABASE_URL JWT_PRIVATE_KEY JWT_PUBLIC_KEY ORS_API_KEY) do (
        !FLY! secrets list --app %API_APP% 2>nul | findstr /i "%%S" >nul
        if errorlevel 1 (
            echo   [MISSING] %%S
            if %NON_INTERACTIVE%==1 (
                echo   [ERROR] Cannot prompt in --non-interactive mode.
                echo   Set missing secrets: flyctl secrets set KEY=VALUE --app %API_APP%
                exit /b 1
            )
            echo   Enter value for %%S ^(input not shown^):
            set /p SECVAL=   %%S=
            if not "!SECVAL!"=="" (
                !FLY! secrets set "%%S=!SECVAL!" --app %API_APP% --stage
                echo   OK  Staged: %%S
            ) else (
                echo   [SKIP] %%S not set — deploy may fail.
            )
        ) else (
            echo   OK  Secret set: %%S
        )
    )
)

REM ── Step 5: deploy API ────────────────────────────────────────────────────────
if %DEPLOY_API%==1 (
    echo.
    echo ── Deploying API ^(%API_APP%^) ──
    echo   Note: database migrations run automatically before startup.
    echo.
    !FLY! deploy --config fly.api.toml --remote-only --wait-timeout 300
    if errorlevel 1 (
        echo   [ERROR] API deploy failed.
        echo   Tail logs: flyctl logs --app %API_APP%
        exit /b 1
    )
    echo   OK  API deployed

    echo.
    echo   Running health check...
    timeout /t 5 /nobreak >nul
    curl -sf -o nul -w "  Health check: HTTP %%{http_code}" "https://%API_APP%.fly.dev/health" 2>nul
    if errorlevel 1 (
        echo   [WARN] Health check failed — app may still be starting.
        echo   Check: https://%API_APP%.fly.dev/health
    ) else (
        echo.
        echo   OK  https://%API_APP%.fly.dev/health
    )
)

REM ── Step 6: deploy web ────────────────────────────────────────────────────────
if %DEPLOY_WEB%==1 (
    echo.
    echo ── Deploying web ^(%WEB_APP%^) ──
    !FLY! deploy --config fly.toml --remote-only --wait-timeout 300
    if errorlevel 1 (
        echo   [ERROR] Web deploy failed.
        echo   Tail logs: flyctl logs --app %WEB_APP%
        exit /b 1
    )
    echo   OK  Web deployed
)

REM ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ── Deployment complete ──
echo.
if %DEPLOY_API%==1 (
    echo   API:    https://%API_APP%.fly.dev
    echo   Docs:   https://%API_APP%.fly.dev/docs
    echo   Health: https://%API_APP%.fly.dev/health
)
if %DEPLOY_WEB%==1 (
    echo   Web:    https://%WEB_APP%.fly.dev
)
echo.
echo   To tail production logs:
if %DEPLOY_API%==1 echo     flyctl logs --app %API_APP%
if %DEPLOY_WEB%==1 echo     flyctl logs --app %WEB_APP%
echo.
echo   CI/CD: add FLY_API_TOKEN to GitHub repo secrets.
echo   See .github/workflows/deploy.yml for automated deploys on push to main.
