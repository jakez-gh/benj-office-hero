"""Start mock-backend and MCP server for pre-push / CI testing.

Ports are chosen randomly via OS ephemeral allocation so they never
conflict with other services.  If a previous instance left a pidfile,
the old processes are killed before new ones start.

Environment overrides (mostly for deterministic test usage):
    MOCK_BACKEND_PORT   – force a specific backend port
    MCP_SERVER_PORT     – force a specific MCP server port
    START_SERVICES_PIDFILE – path to write spawned PIDs
    START_SERVICES_PORTFILE – path to write "backend=PORT\nmcp=PORT" for consumers
"""

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_free_port() -> int:
    """Ask the OS for a random, unused ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return True
        except Exception:
            return False


def _kill_old_pids(pidfile: str) -> None:
    """Send SIGTERM then SIGKILL to every PID recorded in *pidfile*."""
    path = Path(pidfile)
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        pid = int(line.strip()) if line.strip().isdigit() else None
        if pid is None:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            # give it a moment to shut down
            time.sleep(0.3)
            os.kill(pid, signal.SIGKILL)  # force if still alive
        except ProcessLookupError:
            pass  # already dead
        except PermissionError:
            pass  # not ours
    path.unlink(missing_ok=True)


def _record_pid(pid: int) -> None:
    pidfile = os.environ.get("START_SERVICES_PIDFILE")
    if pidfile:
        with open(pidfile, "a") as f:
            f.write(f"{pid}\n")


def start_process(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.Popen:
    """Start a process in the background and return the Popen object."""
    proc = subprocess.Popen(cmd, env=env or os.environ.copy())
    _record_pid(proc.pid)
    return proc


def _write_portfile(backend_port: int, mcp_port: int) -> None:
    portfile = os.environ.get(
        "START_SERVICES_PORTFILE",
        str(_PROJECT_ROOT / ".service-ports"),
    )
    Path(portfile).write_text(f"backend={backend_port}\nmcp={mcp_port}\n")


# ---------------------------------------------------------------------------
# Service launchers
# ---------------------------------------------------------------------------

def ensure_mock_backend(port: int | None = None) -> tuple[subprocess.Popen | None, int]:
    if port is None:
        port = int(os.environ.get("MOCK_BACKEND_PORT", "0")) or get_free_port()
    if is_port_open(port):
        print(f"mock backend already running on {port}")
        return None, port
    print(f"starting mock backend on port {port}")
    proc = start_process(
        [sys.executable, str(_PROJECT_ROOT / "tools" / "mock_backend.py"), "--port", str(port)],
    )
    return proc, port


def ensure_mcp_server(port: int | None = None) -> tuple[subprocess.Popen | None, int]:
    if port is None:
        port = int(os.environ.get("MCP_SERVER_PORT", "0")) or get_free_port()
    if is_port_open(port):
        print(f"MCP server already listening on {port}")
        return None, port
    print(f"starting MCP server on port {port}")
    env = os.environ.copy()
    env["MCP_SERVER_PORT"] = str(port)
    # Launch via the start.py entry-point (mcp-server has a hyphen so
    # ``python -m mcp-server.start`` is invalid).
    proc = start_process(
        [sys.executable, str(_PROJECT_ROOT / "mcp-server" / "start.py")],
        env=env,
    )
    return proc, port


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Ensure mock backend and MCP server are running.

    If a previous pidfile exists its processes are killed first so that
    a fresh deployment always wins.
    """
    pidfile = os.environ.get("START_SERVICES_PIDFILE", str(_PROJECT_ROOT / ".service-pids"))
    os.environ.setdefault("START_SERVICES_PIDFILE", pidfile)

    # Kill any previously-launched instances
    _kill_old_pids(pidfile)

    _, backend_port = ensure_mock_backend()
    _, mcp_port = ensure_mcp_server()

    _write_portfile(backend_port, mcp_port)
    print(f"services ready — backend={backend_port}  mcp={mcp_port}")


if __name__ == "__main__":
    main()
