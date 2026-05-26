import os
import signal
import socket
import time

from scripts import start_services


def get_free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    addr, port = sock.getsockname()
    sock.close()
    return port


def wait_for_port(port: int, timeout: float = 5.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
                return True
            except Exception:
                time.sleep(0.1)
    return False


def kill_pids(pidfile: str):
    try:
        from contextlib import suppress

        with open(pidfile) as f:
            for line in f:
                with suppress(Exception):
                    os.kill(int(line.strip()), signal.SIGTERM)
    except FileNotFoundError:
        pass


def test_start_services_creates_backends(tmp_path, monkeypatch):
    # choose random free ports so we don't collide with anything
    backend_port = get_free_port()
    mcp_port = get_free_port()

    # define pid file path and env overrides
    env = os.environ.copy()
    env["START_SERVICES_PIDFILE"] = str(tmp_path / "pids.txt")
    env["MOCK_BACKEND_PORT"] = str(backend_port)
    env["MCP_SERVER_PORT"] = str(mcp_port)

    # run start_services.main() in-process with modified environment
    monkeypatch.setenv("START_SERVICES_PIDFILE", env["START_SERVICES_PIDFILE"])
    monkeypatch.setenv("MOCK_BACKEND_PORT", env["MOCK_BACKEND_PORT"])
    monkeypatch.setenv("MCP_SERVER_PORT", env["MCP_SERVER_PORT"])
    start_services.main()

    assert wait_for_port(backend_port), "mock backend did not start"
    assert wait_for_port(mcp_port), "MCP server did not start"

    # kill spawned processes
    kill_pids(env["START_SERVICES_PIDFILE"])
