#!/usr/bin/env bash
# run.sh — Start the Office Hero development stack
#
# Usage:
#   ./run.sh                # start backend + frontend (dev, hot-reload)
#   ./run.sh --prod         # build frontend if needed, serve production preview
#   ./run.sh --backend      # backend only
#   ./run.sh --frontend     # frontend only
#   ./run.sh --port 9000    # backend on a specific port (default: 8000)
#   ./run.sh --help         # show this help
#
# First run on a fresh clone:
#   1. cp .env.example .env
#   2. Fill in DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY in .env
#   3. ./run.sh
#
# Dependencies are installed automatically when missing.

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✗${NC} $*" >&2; }
hdr()  { echo -e "\n${BOLD}${CYAN}── $* ──${NC}"; }

# ── Parse arguments ───────────────────────────────────────────────────────────
MODE="dev"          # dev | prod
BACKEND=true
FRONTEND=true
BACKEND_PORT=8000

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prod)     MODE="prod"     ;;
        --backend)  FRONTEND=false  ;;
        --frontend) BACKEND=false   ;;
        --port)     BACKEND_PORT="$2"; shift ;;
        --help|-h)
            sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) err "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

FRONTEND_PORT=3000
BACKEND_PID_FILE="$PROJECT_ROOT/.backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/.frontend.pid"

# ── Helper: check command exists ──────────────────────────────────────────────
need() {
    if ! command -v "$1" &>/dev/null; then
        err "'$1' not found. $2"
        exit 1
    fi
}

# ── Step 1: prerequisites ─────────────────────────────────────────────────────
hdr "Checking prerequisites"
need poetry  "Install from https://python-poetry.org/docs/#installation"
need pnpm    "Install via: npm install -g pnpm"
need python3 "Install Python 3.11+ from https://www.python.org"
ok "poetry $(poetry --version 2>&1 | grep -oP '[\d.]+')"
ok "pnpm   $(pnpm --version)"

# ── Step 2: Python dependencies ───────────────────────────────────────────────
hdr "Python dependencies"
VENV_DIR="$PROJECT_ROOT/.venv"
LOCK_FILE="$PROJECT_ROOT/poetry.lock"
VENV_STAMP="$VENV_DIR/.installed_at"

install_python_deps=false
if [[ ! -d "$VENV_DIR" ]]; then
    install_python_deps=true
elif [[ "$LOCK_FILE" -nt "$VENV_STAMP" ]]; then
    install_python_deps=true
fi

if $install_python_deps; then
    echo -e "  ${DIM}Running: poetry install --with dev${NC}"
    poetry install --with dev --no-interaction
    touch "$VENV_STAMP"
    ok "Python dependencies installed"
else
    ok "Python dependencies up to date"
fi

# ── Step 3: Node dependencies ─────────────────────────────────────────────────
hdr "Node dependencies"
NODE_MODULES="$PROJECT_ROOT/node_modules"
PNPM_LOCK="$PROJECT_ROOT/pnpm-lock.yaml"
NODE_STAMP="$NODE_MODULES/.installed_at"

install_node_deps=false
if [[ ! -d "$NODE_MODULES" ]]; then
    install_node_deps=true
elif [[ "$PNPM_LOCK" -nt "$NODE_STAMP" ]]; then
    install_node_deps=true
fi

if $install_node_deps; then
    echo -e "  ${DIM}Running: pnpm install${NC}"
    pnpm install --frozen-lockfile
    touch "$NODE_STAMP"
    ok "Node dependencies installed"
else
    ok "Node dependencies up to date"
fi

# ── Step 4: environment file ──────────────────────────────────────────────────
hdr "Environment"
ENV_FILE="$PROJECT_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
    warn ".env created from .env.example"
    warn "Edit .env and set DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY before the"
    warn "backend will start. Run ./run.sh again when ready."
    if $FRONTEND && ! $BACKEND; then : ; else
        echo ""
        exit 0
    fi
fi

# Load .env
set -o allexport
# shellcheck source=/dev/null
source "$ENV_FILE"
set +o allexport
ok ".env loaded"

# ── Step 5: database migrations ───────────────────────────────────────────────
if $BACKEND && [[ -n "${DATABASE_URL:-}" ]]; then
    hdr "Database migrations"
    echo -e "  ${DIM}Running: alembic upgrade head${NC}"
    if poetry run alembic upgrade head 2>&1 | grep -qE "Running upgrade|Already up to date"; then
        ok "Migrations applied"
    else
        poetry run alembic upgrade head
        ok "Migrations applied"
    fi
fi

# ── Step 6: frontend build (prod mode only) ───────────────────────────────────
frontend_needs_build() {
    local stamp="apps/admin-web/dist/index.html"
    [[ ! -f "$stamp" ]] && return 0
    find apps/admin-web/src apps/admin-web/index.html \
         apps/admin-web/vite.config.ts apps/admin-web/tailwind.config.js \
         apps/admin-web/package.json \
         -newer "$stamp" 2>/dev/null | grep -q .
}

if [[ "$MODE" == "prod" ]] && $FRONTEND; then
    hdr "Frontend build"
    if frontend_needs_build; then
        echo -e "  ${DIM}Running: pnpm --filter admin-web build${NC}"
        pnpm --filter admin-web build
        ok "Frontend built to apps/admin-web/dist/"
    else
        ok "Frontend build is current — skipping"
    fi
fi

# ── Step 7: kill any stale processes ─────────────────────────────────────────
kill_stale() {
    local pidfile="$1" label="$2"
    if [[ -f "$pidfile" ]]; then
        local pid; pid="$(cat "$pidfile")"
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "  ${DIM}Stopping previous $label (PID $pid)${NC}"
            kill "$pid" 2>/dev/null || true
            sleep 0.5
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile"
    fi
}

$BACKEND  && kill_stale "$BACKEND_PID_FILE"  "backend"
$FRONTEND && kill_stale "$FRONTEND_PID_FILE" "frontend"

# ── Step 8: start services ────────────────────────────────────────────────────
hdr "Starting services"

PIDS=()

cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    for pid in "${PIDS[@]:-}"; do
        kill "$pid" 2>/dev/null || true
    done
    rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"
    exit 0
}
trap cleanup INT TERM

if $BACKEND; then
    export OFFICE_HERO_TEST_AUTH="${OFFICE_HERO_TEST_AUTH:-1}"
    export PYTHONPATH="$PROJECT_ROOT/src"
    poetry run uvicorn office_hero.main:app \
        --reload \
        --host 127.0.0.1 \
        --port "$BACKEND_PORT" \
        --log-level info &
    BACKEND_PID=$!
    PIDS+=("$BACKEND_PID")
    echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
    ok "Backend  → http://127.0.0.1:${BACKEND_PORT}  (PID $BACKEND_PID)"
    echo -e "     ${DIM}Docs:   http://127.0.0.1:${BACKEND_PORT}/docs${NC}"
    echo -e "     ${DIM}Health: http://127.0.0.1:${BACKEND_PORT}/health${NC}"
fi

if $FRONTEND; then
    export VITE_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}"
    if [[ "$MODE" == "prod" ]]; then
        pnpm --filter admin-web exec vite preview --port "$FRONTEND_PORT" --host 127.0.0.1 &
    else
        pnpm --filter admin-web exec vite --port "$FRONTEND_PORT" --host 127.0.0.1 &
    fi
    FRONTEND_PID=$!
    PIDS+=("$FRONTEND_PID")
    echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"
    ok "Frontend → http://127.0.0.1:${FRONTEND_PORT}  (PID $FRONTEND_PID)"
fi

echo ""
echo -e "${BOLD}Press Ctrl+C to stop all services.${NC}"

# ── Wait ──────────────────────────────────────────────────────────────────────
wait "${PIDS[@]}"
