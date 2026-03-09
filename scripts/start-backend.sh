#!/usr/bin/env bash
# start-backend.sh — Start Office Hero FastAPI development server
#
# Prerequisites:
#   1. Copy .env.example to .env and fill in real values
#   2. Run: pip install -e ".[dev]"
#
# Usage:
#   bash scripts/start-backend.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Load .env if it exists ────────────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
    echo "Loading environment from .env ..."
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

# ── Start server ─────────────────────────────────────────────────────────────
export PYTHONPATH="$PROJECT_ROOT/src"

echo "Starting Office Hero API on http://localhost:8000 ..."
echo "  Docs:   http://localhost:8000/docs"
echo "  Health: http://localhost:8000/health"
echo ""

python -m uvicorn office_hero.main:app --reload --host 127.0.0.1 --port 8000
