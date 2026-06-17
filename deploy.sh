#!/usr/bin/env bash
# deploy.sh — Deploy Office Hero to Fly.io
#
# Usage:
#   ./deploy.sh              # deploy both API and web (interactive)
#   ./deploy.sh --api-only   # deploy API only
#   ./deploy.sh --web-only   # deploy web only
#   ./deploy.sh --check      # verify prerequisites without deploying
#   ./deploy.sh --non-interactive  # skip prompts (CI mode; requires all secrets set)
#   ./deploy.sh --help       # show this help
#
# What this script does:
#   1. Checks flyctl is installed and you are logged in
#   2. Verifies both Fly.io apps exist (creates them if missing, with confirmation)
#   3. Checks all required secrets are set in Fly.io (prompts for missing ones)
#   4. Deploys API (includes alembic upgrade head via release_command)
#   5. Deploys web frontend
#   6. Hits /health to confirm API is up
#
# Apps deployed:
#   office-hero-api       — FastAPI backend (fly.api.toml)
#   office-hero-admin-web — React frontend (fly.toml)
#
# Required Fly.io secrets for API (fly.api.toml):
#   DATABASE_URL     — Neon PostgreSQL connection string (postgresql://...)
#   JWT_PRIVATE_KEY  — RSA private key (PEM, \n-escaped for single-line storage)
#   JWT_PUBLIC_KEY   — Matching RSA public key (PEM, \n-escaped)
#   ORS_API_KEY      — OpenRouteService API key
#
# Optional secrets:
#   SENTRY_DSN       — Backend Sentry DSN
#
# Optional variables (not secrets) for web:
#   VITE_SENTRY_DSN  — Frontend Sentry DSN (set at build time via fly.toml [build.args])
#
# For GitHub Actions CI/CD:
#   Add FLY_API_TOKEN as a repo secret (from: fly tokens create deploy)
#   The workflow at .github/workflows/deploy.yml handles deploys on push to main.

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
ok()     { echo -e "  ${GREEN}✓${NC} $*"; }
warn()   { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()    { echo -e "  ${RED}✗${NC} $*" >&2; }
hdr()    { echo -e "\n${BOLD}${CYAN}── $* ──${NC}"; }
prompt() { echo -en "${BOLD}  → $*${NC} "; }

# ── Parse arguments ───────────────────────────────────────────────────────────
DEPLOY_API=true
DEPLOY_WEB=true
CHECK_ONLY=false
NON_INTERACTIVE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-only)         DEPLOY_WEB=false ;;
        --web-only)         DEPLOY_API=false ;;
        --check)            CHECK_ONLY=true ;;
        --non-interactive)  NON_INTERACTIVE=true ;;
        --help|-h)
            sed -n '2,38p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) err "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

API_APP="office-hero-api"
WEB_APP="office-hero-admin-web"

# ── Step 1: flyctl ────────────────────────────────────────────────────────────
hdr "Checking flyctl"
if ! command -v flyctl &>/dev/null && ! command -v fly &>/dev/null; then
    err "flyctl not found."
    echo ""
    echo "  Install flyctl:"
    echo "    curl -L https://fly.io/install.sh | sh"
    echo "  Or via Homebrew:"
    echo "    brew install flyctl"
    exit 1
fi

# Use whichever alias is available
FLY=$(command -v flyctl 2>/dev/null || command -v fly)
ok "flyctl: $($FLY version 2>&1 | head -1)"

# ── Step 2: authentication ────────────────────────────────────────────────────
hdr "Fly.io authentication"
if $FLY auth whoami &>/dev/null; then
    WHOAMI=$($FLY auth whoami 2>/dev/null)
    ok "Logged in as: $WHOAMI"
else
    if $NON_INTERACTIVE; then
        err "Not logged in to Fly.io and --non-interactive mode is set."
        err "Set FLY_API_TOKEN environment variable or run: flyctl auth login"
        exit 1
    fi
    warn "Not logged in to Fly.io."
    prompt "Run 'flyctl auth login' now? [y/N] "
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        $FLY auth login
    else
        err "Aborting — please log in first: flyctl auth login"
        exit 1
    fi
fi

$CHECK_ONLY && { hdr "Prerequisites OK (--check mode)"; exit 0; }

# ── Step 3: verify / create apps ─────────────────────────────────────────────
hdr "Fly.io apps"

ensure_app_exists() {
    local app="$1" config="$2"
    if $FLY apps list 2>/dev/null | grep -q "^$app\b"; then
        ok "App exists: $app"
    else
        warn "App '$app' does not exist."
        if $NON_INTERACTIVE; then
            echo -e "  ${DIM}Creating app (--non-interactive)...${NC}"
            $FLY apps create "$app" --org personal
        else
            prompt "Create app '$app' on Fly.io now? [y/N] "
            read -r answer
            if [[ "$answer" =~ ^[Yy]$ ]]; then
                $FLY apps create "$app" --org personal
                ok "Created: $app"
            else
                err "App '$app' required — aborting."
                exit 1
            fi
        fi
    fi
}

$DEPLOY_API && ensure_app_exists "$API_APP"  "fly.api.toml"
$DEPLOY_WEB && ensure_app_exists "$WEB_APP"  "fly.toml"

# ── Step 4: check / set required secrets ─────────────────────────────────────
hdr "Fly.io secrets"

check_and_set_secrets() {
    local app="$1"
    shift
    local required_secrets=("$@")

    local existing_secrets=()
    while IFS= read -r line; do
        existing_secrets+=("$line")
    done < <($FLY secrets list --app "$app" 2>/dev/null | awk 'NR>1 {print $1}')

    local missing=()
    for secret in "${required_secrets[@]}"; do
        if printf '%s\n' "${existing_secrets[@]}" | grep -qx "$secret"; then
            ok "Secret set: $secret ($app)"
        else
            missing+=("$secret")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        warn "Missing secrets for $app: ${missing[*]}"
        if $NON_INTERACTIVE; then
            err "Cannot prompt for secrets in --non-interactive mode."
            err "Set them manually: flyctl secrets set KEY=VALUE --app $app"
            exit 1
        fi
        echo ""
        echo -e "  Enter values for missing secrets (values are not displayed):"
        echo -e "  ${DIM}Leave blank to skip — the deploy will fail if required.${NC}"
        echo ""
        for secret in "${missing[@]}"; do
            prompt "$secret: "
            local val
            read -rs val
            echo ""
            if [[ -n "$val" ]]; then
                $FLY secrets set "${secret}=${val}" --app "$app" --stage
                ok "Staged: $secret"
            else
                warn "Skipped: $secret"
            fi
        done
    fi
}

API_REQUIRED_SECRETS=(DATABASE_URL JWT_PRIVATE_KEY JWT_PUBLIC_KEY ORS_API_KEY)

$DEPLOY_API && check_and_set_secrets "$API_APP" "${API_REQUIRED_SECRETS[@]}"

# ── Step 5: deploy API ────────────────────────────────────────────────────────
if $DEPLOY_API; then
    hdr "Deploying API ($API_APP)"
    echo -e "  ${DIM}This runs database migrations (alembic upgrade head) before starting.${NC}"
    echo ""
    $FLY deploy --config fly.api.toml --remote-only --wait-timeout 300
    ok "API deployed"

    # Quick health check
    echo -e "\n  ${DIM}Running health check...${NC}"
    sleep 5
    HEALTH_URL="https://${API_APP}.fly.dev/health"
    HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_STATUS" == "200" ]]; then
        ok "Health check passed: $HEALTH_URL"
    else
        warn "Health check returned HTTP $HTTP_STATUS — the app may still be starting."
        warn "Check: $HEALTH_URL"
    fi
fi

# ── Step 6: deploy web ────────────────────────────────────────────────────────
if $DEPLOY_WEB; then
    hdr "Deploying web ($WEB_APP)"
    $FLY deploy --config fly.toml --remote-only --wait-timeout 300
    ok "Web deployed"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
hdr "Deployment complete"

$DEPLOY_API && echo -e "  ${GREEN}API:${NC}     https://${API_APP}.fly.dev"
$DEPLOY_API && echo -e "  ${DIM}Docs:    https://${API_APP}.fly.dev/docs${NC}"
$DEPLOY_API && echo -e "  ${DIM}Health:  https://${API_APP}.fly.dev/health${NC}"
$DEPLOY_WEB && echo -e "  ${GREEN}Web:${NC}     https://${WEB_APP}.fly.dev"
echo ""
echo -e "  ${DIM}To tail production logs:${NC}"
$DEPLOY_API && echo -e "  ${DIM}  flyctl logs --app ${API_APP}${NC}"
$DEPLOY_WEB && echo -e "  ${DIM}  flyctl logs --app ${WEB_APP}${NC}"
echo ""
echo -e "  ${DIM}To set up CI/CD (auto-deploy on push to main):${NC}"
echo -e "  ${DIM}  Add FLY_API_TOKEN to GitHub repo secrets${NC}"
echo -e "  ${DIM}  (from: flyctl tokens create deploy)${NC}"
