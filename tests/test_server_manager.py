import subprocess
import sys

from tools import server_manager


def test_find_random_free_port_avoids_reserved_values():
    reserved = {21000, 22000, 23000}
    port = server_manager.find_random_free_port(used_ports=reserved)
    assert port not in reserved
    assert server_manager._port_available(port)


def test_terminate_process_group_stops_spawned_process():
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert server_manager._is_pid_alive(proc.pid)
    server_manager._terminate_process_group(proc.pid, grace_seconds=0.2)
    assert not server_manager._is_pid_alive(proc.pid)
