import os
import socket
import subprocess
import sys


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return True
        except Exception:
            return False


def start_process(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.Popen:
    """Start a process in the background and return the Popen object."""
    # Use subprocess.Popen so the hook doesn't block
    proc = subprocess.Popen(cmd, env=env or os.environ.copy())
    # record pid if requested
    pidfile = os.environ.get("START_SERVICES_PIDFILE")
    if pidfile:
        try:
            with open(pidfile, "a") as f:
                f.write(str(proc.pid) + "\n")
        except Exception:
            pass
    return proc


def ensure_mock_backend(port: int = 9000) -> subprocess.Popen | None:
    if is_port_open(port):
        print(f"mock backend already running on {port}")
        return None
    print(f"starting mock backend on port {port}")
    return start_process([sys.executable, "tools/mock_backend.py", "--port", str(port)])


def ensure_mcp_server(port: int = 8001) -> subprocess.Popen | None:
    if is_port_open(port):
        print(f"MCP server already listening on {port}")
        return None
    print(f"starting MCP server on port {port}")
    env = os.environ.copy()
    env["MCP_SERVER_PORT"] = str(port)
    # run in same python environment
    return start_process([sys.executable, "-m", "mcp-server.start"], env=env)


def main():
    # make sure mock backend and MCP server are up before push
    # ports can be overridden using environment variables for testing
    backend_port = int(os.environ.get("MOCK_BACKEND_PORT", "9000"))
    mcp_port = int(os.environ.get("MCP_SERVER_PORT", "8001"))
    ensure_mock_backend(backend_port)
    ensure_mcp_server(mcp_port)


if __name__ == "__main__":
    main()
