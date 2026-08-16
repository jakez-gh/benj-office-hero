#!/usr/bin/env bash
# manage-backend.sh — zero-downtime local backend manager
#
# Commands:
#   deploy   Pick a random free port, start a new server, verify health,
#            kill the previous instance. If the new server fails to start,
#            kill it and keep the old one alive (or exit non-zero).
#   stop     Kill the currently-running server (reads .backend-port / .backend-pid)
#   status   Print whether the server is running and on what port
#
# State files (git-ignored):
#   .backend-port  — port the current server is listening on
#   .backend-pid   — PID of the current server process
#
# Usage (from repo root):
#   bash scripts/manage-backend.sh deploy
#   bash scripts/manage-backend.sh stop
#   bash scripts/manage-backend.sh status

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; NC=''
fi

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PORT_FILE="$PROJECT_ROOT/.backend-port"
PID_FILE="$PROJECT_ROOT/.backend-pid"

# ── Config ────────────────────────────────────────────────────────────────────
PORT_RANGE_MIN=40000   # high ephemeral range — unlikely to conflict with dev tooling
PORT_RANGE_MAX=49999
HEALTH_TIMEOUT=30      # seconds to wait for new server to become healthy
KILL_TIMEOUT=10        # seconds to wait for old server to die gracefully

# ── Helpers ───────────────────────────────────────────────────────────────────

pick_free_port() {
  local port
  local attempts=0
  while (( attempts < 50 )); do
    port=$(( RANDOM % (PORT_RANGE_MAX - PORT_RANGE_MIN + 1) + PORT_RANGE_MIN ))
    # Check if port is free: ss/netstat/lsof
    if ! ss -tuln 2>/dev/null | grep -q ":${port} " && \
       ! lsof -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | grep -q .; then
      echo "$port"
      return 0
    fi
    (( attempts++ ))
  done
  echo "ERROR: could not find a free port after 50 attempts" >&2
  exit 1
}

server_healthy() {
  local port="$1"
  curl -sf "http://127.0.0.1:${port}/health" >/dev/null 2>&1
}

wait_for_health() {
  local port="$1"
  local deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
  while (( $(date +%s) < deadline )); do
    if server_healthy "$port"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

kill_process() {
  # Kill by PID, escalating to SIGKILL if needed
  local pid="$1"
  local label="${2:-process}"
  if ! kill -0 "$pid" 2>/dev/null; then
    return 0  # already dead
  fi
  echo -e "${YELLOW}  Sending SIGTERM to ${label} (PID ${pid})…${NC}"
  kill -TERM "$pid" 2>/dev/null || true
  local deadline=$(( $(date +%s) + KILL_TIMEOUT ))
  while (( $(date +%s) < deadline )); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo -e "${GREEN}  ${label} stopped.${NC}"
      return 0
    fi
    sleep 1
  done
  echo -e "${RED}  ${label} did not stop; sending SIGKILL…${NC}"
  kill -KILL "$pid" 2>/dev/null || true
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    echo -e "${RED}  ERROR: could not kill ${label} (PID ${pid})${NC}" >&2
    return 1
  fi
  echo -e "${GREEN}  ${label} forcefully killed.${NC}"
}

read_current_state() {
  OLD_PORT=""
  OLD_PID=""
  if [[ -f "$PORT_FILE" ]]; then
    OLD_PORT="$(<"$PORT_FILE")"
  fi
  if [[ -f "$PID_FILE" ]]; then
    OLD_PID="$(<"$PID_FILE")"
    # Validate PID is still alive
    if ! kill -0 "$OLD_PID" 2>/dev/null; then
      OLD_PID=""
    fi
  fi
}

# ── Load .env ─────────────────────────────────────────────────────────────────
load_env() {
  local env_file="$PROJECT_ROOT/.env"
  if [[ -f "$env_file" ]]; then
    set -o allexport
    # shellcheck source=/dev/null
    source "$env_file"
    set +o allexport
  fi
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_deploy() {
  load_env
  read_current_state

  # Validate required env before starting anything
  for var in DATABASE_URL JWT_PRIVATE_KEY JWT_PUBLIC_KEY; do
    if [[ -z "${!var:-}" ]]; then
      echo -e "${RED}ERROR: Required env var '$var' is not set.${NC}" >&2
      echo "Copy .env.example → .env and fill in the values." >&2
      exit 1
    fi
  done

  local new_port
  new_port="$(pick_free_port)"
  echo -e "${YELLOW}🚀 Starting new backend on port ${new_port}…${NC}"

  export PYTHONPATH="$PROJECT_ROOT/src"
  python -m uvicorn office_hero.main:app \
    --host 127.0.0.1 \
    --port "$new_port" \
    --reload \
    >"$PROJECT_ROOT/.backend-stdout.log" 2>"$PROJECT_ROOT/.backend-stderr.log" &
  local new_pid=$!

  echo -e "   PID ${new_pid}, waiting for health check (up to ${HEALTH_TIMEOUT}s)…"

  if wait_for_health "$new_port"; then
    echo -e "${GREEN}✅ New backend healthy on http://127.0.0.1:${new_port}${NC}"
    echo -e "   Docs:   http://127.0.0.1:${new_port}/docs"

    # Tear down old instance (if any)
    if [[ -n "$OLD_PID" ]]; then
      echo -e "${YELLOW}  Stopping old backend (PID ${OLD_PID}, port ${OLD_PORT})…${NC}"
      kill_process "$OLD_PID" "old backend"
    fi

    # Persist new state
    echo "$new_port" > "$PORT_FILE"
    echo "$new_pid"  > "$PID_FILE"

    # Export so callers can pick up the port
    export OFFICE_HERO_API_URL="http://127.0.0.1:${new_port}"
    echo -e "${GREEN}✅ Backend running: OFFICE_HERO_API_URL=${OFFICE_HERO_API_URL}${NC}"
  else
    echo -e "${RED}❌ New backend failed to become healthy within ${HEALTH_TIMEOUT}s${NC}" >&2
    echo "   See $PROJECT_ROOT/.backend-stderr.log for details."
    echo -e "${RED}   Killing new backend (PID ${new_pid})…${NC}"
    kill_process "$new_pid" "new backend (failed)" || true
    if [[ -n "$OLD_PID" ]]; then
      echo -e "${YELLOW}  Old backend (PID ${OLD_PID}, port ${OLD_PORT}) remains running.${NC}"
    fi
    exit 1
  fi
}

cmd_stop() {
  read_current_state
  if [[ -z "$OLD_PID" ]]; then
    echo -e "${YELLOW}No running backend found (PID file empty or stale).${NC}"
    exit 0
  fi
  echo -e "${YELLOW}Stopping backend (PID ${OLD_PID}, port ${OLD_PORT})…${NC}"
  kill_process "$OLD_PID" "backend"
  rm -f "$PORT_FILE" "$PID_FILE"
  echo -e "${GREEN}✅ Backend stopped.${NC}"
}

cmd_status() {
  read_current_state
  if [[ -n "$OLD_PID" ]] && [[ -n "$OLD_PORT" ]]; then
    if server_healthy "$OLD_PORT"; then
      echo -e "${GREEN}✅ Backend running: http://127.0.0.1:${OLD_PORT} (PID ${OLD_PID})${NC}"
    else
      echo -e "${YELLOW}⚠️  Backend process alive (PID ${OLD_PID}) but /health not responding on port ${OLD_PORT}${NC}"
    fi
  else
    echo -e "${RED}❌ Backend not running${NC}"
    exit 1
  fi
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
CMD="${1:-deploy}"
case "$CMD" in
  deploy)  cmd_deploy ;;
  stop)    cmd_stop ;;
  status)  cmd_status ;;
  *)
    echo "Usage: $0 {deploy|stop|status}" >&2
    exit 1
    ;;
esac
