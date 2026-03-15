"""Manage local backend/frontend test servers for hook-driven automation.

This module provides deterministic process management around two goals:
1) Always launch test servers on random, conflict-resistant ports.
2) Replace stale prior deployments by terminating old process groups first,
   then force-killing them if graceful shutdown fails.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
STATE_FILE = RUNTIME_DIR / "test-servers.json"
PORTS_FILE = RUNTIME_DIR / "test-ports.env"

HOST = "127.0.0.1"
PORT_MIN = 20000
PORT_MAX = 60999


@dataclass(slots=True)
class ManagedProcess:
    """Represents one server process managed by this tool."""

    name: str
    pid: int
    port: int
    command: list[str]


def _runtime_mkdir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _load_dotenv(dotenv_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not dotenv_path.exists():
        return values

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
    return True


def find_random_free_port(
    used_ports: set[int] | None = None,
    min_port: int = PORT_MIN,
    max_port: int = PORT_MAX,
    attempts: int = 256,
) -> int:
    """Find a free TCP port within a high, low-collision range."""
    reserved = used_ports or set()
    rng = random.SystemRandom()

    for _ in range(attempts):
        candidate = rng.randint(min_port, max_port)
        if candidate in reserved:
            continue
        if _port_available(candidate):
            return candidate

    raise RuntimeError("Unable to find a free random port after multiple attempts")


def _is_pid_alive(pid: int) -> bool:
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            # /proc/<pid>/stat field 3 is process state; Z means zombie.
            state = stat_path.read_text(encoding="utf-8").split()[2]
            if state == "Z":
                return False
        except (OSError, IndexError):
            pass

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_exit(pid: int, timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with contextlib.suppress(ChildProcessError, OSError):
            os.waitpid(pid, os.WNOHANG)

        if not _is_pid_alive(pid):
            return True
        time.sleep(0.2)
    return not _is_pid_alive(pid)


def _terminate_process_group(pid: int, grace_seconds: float = 8.0) -> None:
    if not _is_pid_alive(pid):
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    if _wait_for_exit(pid, grace_seconds):
        return

    # Graceful shutdown failed — force kill.
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return

    _wait_for_exit(pid, 2.0)


def _save_state(processes: list[ManagedProcess]) -> None:
    _runtime_mkdir()
    payload = {
        "updated_at": int(time.time()),
        "processes": [asdict(proc) for proc in processes],
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_state() -> list[ManagedProcess]:
    if not STATE_FILE.exists():
        return []

    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    output: list[ManagedProcess] = []
    for row in data.get("processes", []):
        output.append(
            ManagedProcess(
                name=str(row["name"]),
                pid=int(row["pid"]),
                port=int(row["port"]),
                command=[str(part) for part in row.get("command", [])],
            )
        )
    return output


def _clear_state_files() -> None:
    for file_path in (STATE_FILE, PORTS_FILE):
        if file_path.exists():
            file_path.unlink()


def stop_existing_servers(quiet: bool = False) -> None:
    """Stop any existing managed servers from previous runs."""
    state = _load_state()
    if not state:
        _clear_state_files()
        return

    for proc in state:
        if not quiet:
            print(f"Stopping {proc.name} pid={proc.pid} port={proc.port} ...")
        _terminate_process_group(proc.pid)

    _clear_state_files()


def _http_ready(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except urllib.error.HTTPError as exc:
        # Server responded, even if degraded (e.g. /health 503 while deps are down).
        return exc.code >= 100
    except (urllib.error.URLError, TimeoutError):
        return False


def _wait_http(url: str, timeout_seconds: float, label: str) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _http_ready(url):
            return
        time.sleep(0.4)
    raise TimeoutError(f"Timed out waiting for {label}: {url}")


def _backend_command(port: int) -> list[str]:
    cmd_from_env = os.environ.get("TEST_BACKEND_CMD")
    if cmd_from_env:
        return [part.replace("{port}", str(port)) for part in shlex.split(cmd_from_env)]

    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        python_bin = str(venv_python)
    else:
        poetry = shutil.which("poetry")
        if poetry:
            return [
                poetry,
                "run",
                "python",
                "-m",
                "uvicorn",
                "office_hero.main:app",
                "--host",
                HOST,
                "--port",
                str(port),
            ]
        python_bin = str(Path(sys.executable))

    return [
        python_bin,
        "-m",
        "uvicorn",
        "office_hero.main:app",
        "--host",
        HOST,
        "--port",
        str(port),
    ]


def _frontend_command(port: int) -> list[str]:
    cmd_from_env = os.environ.get("TEST_FRONTEND_CMD")
    if cmd_from_env:
        return [part.replace("{port}", str(port)) for part in shlex.split(cmd_from_env)]

    return [
        "pnpm",
        "--filter",
        "admin-web",
        "exec",
        "vite",
        "--host",
        HOST,
        "--port",
        str(port),
        "--strictPort",
    ]


def _spawn_process(name: str, command: list[str], env: dict[str, str]) -> subprocess.Popen[bytes]:
    _runtime_mkdir()
    log_file = RUNTIME_DIR / f"{name}.log"
    log_handle = log_file.open("w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
        )
    finally:
        log_handle.close()
    return proc


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(_load_dotenv(PROJECT_ROOT / ".env"))
    env.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:pass@127.0.0.1:55432/test")
    env.setdefault("JWT_PRIVATE_KEY", "dev-secret")
    env.setdefault("JWT_PUBLIC_KEY", "dev-secret")
    env.setdefault("JWT_ALGORITHM", "HS256")
    env.setdefault("PYTHONPATH", str(PROJECT_ROOT / "src"))
    return env


def start_servers(quiet: bool = False) -> tuple[int, int]:
    """Start backend and frontend servers on random ports.

    Any prior managed deployment is terminated first. If graceful shutdown does
    not complete in time, processes are force-killed.
    """

    stop_existing_servers(quiet=quiet)
    used: set[int] = set()
    backend_port = find_random_free_port(used)
    used.add(backend_port)
    frontend_port = find_random_free_port(used)

    backend_env = _base_env()
    frontend_env = dict(os.environ)
    frontend_env["VITE_API_BASE_URL"] = f"http://{HOST}:{backend_port}"

    backend_cmd = _backend_command(backend_port)
    frontend_cmd = _frontend_command(frontend_port)

    if not quiet:
        print(f"Starting backend on {HOST}:{backend_port} ...")
    backend_proc = _spawn_process("backend", backend_cmd, backend_env)

    try:
        _wait_http(f"http://{HOST}:{backend_port}/health", timeout_seconds=40.0, label="backend")
    except Exception:
        _terminate_process_group(backend_proc.pid)
        raise

    if not quiet:
        print(f"Starting frontend on {HOST}:{frontend_port} ...")
    frontend_proc = _spawn_process("frontend", frontend_cmd, frontend_env)

    try:
        _wait_http(f"http://{HOST}:{frontend_port}", timeout_seconds=50.0, label="frontend")
    except Exception:
        _terminate_process_group(frontend_proc.pid)
        _terminate_process_group(backend_proc.pid)
        raise

    managed = [
        ManagedProcess(
            name="backend", pid=backend_proc.pid, port=backend_port, command=backend_cmd
        ),
        ManagedProcess(
            name="frontend",
            pid=frontend_proc.pid,
            port=frontend_port,
            command=frontend_cmd,
        ),
    ]
    _save_state(managed)
    _runtime_mkdir()
    PORTS_FILE.write_text(
        "\n".join(
            [
                f"BACKEND_PORT={backend_port}",
                f"FRONTEND_PORT={frontend_port}",
                f"VITE_API_BASE_URL=http://{HOST}:{backend_port}",
                f"PLAYWRIGHT_BASE_URL=http://{HOST}:{frontend_port}",
                "SKIP_PLAYWRIGHT_WEBSERVER=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    if not quiet:
        print(f"Managed test servers ready: backend={backend_port}, frontend={frontend_port}")
    return backend_port, frontend_port


def _status() -> int:
    state = _load_state()
    if not state:
        print("No managed test servers are currently recorded.")
        return 0

    for proc in state:
        alive = _is_pid_alive(proc.pid)
        print(f"{proc.name}: pid={proc.pid} port={proc.port} alive={alive}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage local hook-driven test servers")
    parser.add_argument("command", choices=["start", "stop", "status"])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.command == "start":
            start_servers(quiet=args.quiet)
            return 0
        if args.command == "stop":
            stop_existing_servers(quiet=args.quiet)
            return 0
        return _status()
    except Exception as exc:  # pragma: no cover - guarded by CLI contract
        print(f"server-manager error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
