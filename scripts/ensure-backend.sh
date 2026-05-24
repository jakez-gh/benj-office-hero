#!/usr/bin/env bash
# ensure-backend.sh — Ensure the backend is running before tests
#
# Called by Makefile test target or CI scripts. If the backend is
# already running (via .backend.pid), this is a no-op. Otherwise it
# starts a fresh instance on a random port.
#
# Usage:
#   bash scripts/ensure-backend.sh        # start if not running
#   bash scripts/ensure-backend.sh --kill  # stop any running instance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.backend.pid"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

read_pid() {
    if [[ -f "$PID_FILE" ]]; then
        EXISTING_PID="$(awk 'NR==1' "$PID_FILE")"
        EXISTING_PORT="$(awk 'NR==2' "$PID_FILE")"
    else
        EXISTING_PID=""
        EXISTING_PORT=""
    fi
}

if [[ "${1:-}" == "--kill" ]]; then
    read_pid
    if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
        kill "$EXISTING_PID" 2>/dev/null || true
        sleep 1
        kill -0 "$EXISTING_PID" 2>/dev/null && kill -9 "$EXISTING_PID" 2>/dev/null || true
        echo -e "${GREEN}Backend stopped (PID $EXISTING_PID)${NC}"
    fi
    rm -f "$PID_FILE"
    exit 0
fi

read_pid
if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    echo -e "${GREEN}Backend already running (PID $EXISTING_PID, port $EXISTING_PORT)${NC}"
    exit 0
fi

echo -e "${YELLOW}Starting backend for test run...${NC}"
bash "$PROJECT_ROOT/scripts/start-backend.sh" &
disown

for _ in $(seq 1 15); do
    if [[ -f "$PID_FILE" ]]; then
        read_pid
        if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
            echo -e "${GREEN}Backend started (PID $EXISTING_PID, port $EXISTING_PORT)${NC}"
            exit 0
        fi
    fi
    sleep 1
done

echo "Backend may not have started; tests will use mocks." >&2
exit 0
