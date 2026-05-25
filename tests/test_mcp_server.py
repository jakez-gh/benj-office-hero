import asyncio

import pytest

pytest.importorskip("mcp", reason="mcp package not installed — run from mcp-server/")

from office_hero_mcp.server import load_tools, server  # noqa: E402


def test_server_registers_tools():
    # load both generated and custom tools; this is idempotent
    load_tools()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    # custom tools should be present
    assert "get_health" in names
    assert "get_routing_options" in names
    assert "dispatch_job" in names
