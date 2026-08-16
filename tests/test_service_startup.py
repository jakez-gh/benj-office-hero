import os
import socket
import time

from scripts import start_services


def wait_for_port(port: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except Exception:
                time.sleep(0.1)
    return False


def test_start_services_creates_backends(tmp_path, monkeypatch):
    """Verify that main() launches both services on random ports and records PIDs."""
    pidfile = str(tmp_path / "pids.txt")
    portfile = str(tmp_path / "ports.txt")

    monkeypatch.setenv("START_SERVICES_PIDFILE", pidfile)
    monkeypatch.setenv("START_SERVICES_PORTFILE", portfile)
    # Do NOT set explicit ports — let the module pick free ones
    monkeypatch.delenv("MOCK_BACKEND_PORT", raising=False)
    monkeypatch.delenv("MCP_SERVER_PORT", raising=False)

    start_services.main()

    # Read back the ports that were actually chosen
    port_lines = dict(
        line.split("=") for line in open(portfile).read().strip().splitlines()
    )
    backend_port = int(port_lines["backend"])
    mcp_port = int(port_lines["mcp"])

    assert wait_for_port(backend_port), f"mock backend did not start on port {backend_port}"
    assert wait_for_port(mcp_port), f"MCP server did not start on port {mcp_port}"

    # Tear down: kill spawned processes via the module's own helper
    start_services._kill_old_pids(pidfile)
