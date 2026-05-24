#!/usr/bin/env bash
# start-backend.sh — Start Office Hero FastAPI development server
#
# Features (Slice 4 — Production Hardening):
#   • Selects a random available port in the ephemeral range (49152–65535)
#   • Kills any previously running instance (reads .backend.pid)
#   • Writes PID + port to .backend.pid for hooks / other scripts
#   • Force-kills stale processes that refuse SIGTERM
#
# Prerequisites:
#   1. Copy .env.example to .env and fill in real values
#   2. Run: poetry install --with dev
#
# Usage:
#   bash scripts/start-backend.sh          # random port
#   BACKEND_PORT=9999 bash scripts/start-backend.sh  # explicit port

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.backend.pid"

# ── Kill any existing backend ─────────────────────────────────────────────────
kill_existing() {
    if [[ -f "$PID_FILE" ]]; then
        local OLD_PID OLD_PORT
        OLD_PID="$(awk 'NR==1' "$PID_FILE")"
        OLD_PORT="$(awk 'NR==2' "$PID_FILE")"

        if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
            echo "⏳ Stopping previous backend (PID $OLD_PID, port $OLD_PORT) …"
            kill "$OLD_PID" 2>/dev/null || true
            # Wait up to 5 s for graceful shutdown
            for _ in $(seq 1 10); do
                kill -0 "$OLD_PID" 2>/dev/null || break
                sleep 0.5
            done
            # Force-kill if still alive
            if kill -0 "$OLD_PID" 2>/dev/null; then
                echo "⚠️  Process $OLD_PID did not exit; sending SIGKILL"
                kill -9 "$OLD_PID" 2>/dev/null || true
            fi
            echo "✅ Previous backend stopped."
        fi
        rm -f "$PID_FILE"
    fi
}

kill_existing

# ── Load .env if it exists ────────────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
    echo "Loading environment from .env …"
    set -o allexport
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +o allexport
else
    echo "Warning: .env not found. Ensure DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY are exported." >&2
    echo "Copy .env.example to .env and fill in real values." >&2
fi

# ── Validate required vars ────────────────────────────────────────────────────
for var in DATABASE_URL JWT_PRIVATE_KEY JWT_PUBLIC_KEY; do
    if [[ -z "${!var}" ]]; then
        echo "Error: Required environment variable '$var' is not set. Aborting." >&2
        exit 1
    fi
done

# ── Select random available port ─────────────────────────────────────────────
pick_random_port() {
    local port
    while true; do
        port=$(( RANDOM % 16383 + 49152 ))   # range 49152–65535
        # Ensure port is not in use
        if ! ss -tlnH "sport = :$port" 2>/dev/null | grep -q .; then
            echo "$port"
            return
        fi
    done
}

BACKEND_PORT="${BACKEND_PORT:-$(pick_random_port)}"

# ── Start server ─────────────────────────────────────────────────────────────

echo ""
echo "🚀 Starting Office Hero API on http://127.0.0.1:${BACKEND_PORT}"
echo "   Docs:   http://127.0.0.1:${BACKEND_PORT}/docs"
echo "   Health: http://127.0.0.1:${BACKEND_PORT}/health"
echo ""

poetry run uvicorn office_hero.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Write PID file so hooks / other scripts can find & kill us
echo "$BACKEND_PID" > "$PID_FILE"
echo "$BACKEND_PORT" >> "$PID_FILE"

echo "📝 Backend PID $BACKEND_PID written to .backend.pid (port $BACKEND_PORT)"

# Wait for process (foreground-like behaviour when called interactively)
wait "$BACKEND_PID" 2>/dev/null || true
