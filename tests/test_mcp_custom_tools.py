import asyncio

import pytest

pytest.importorskip("mcp", reason="mcp package not installed — run from mcp-server/")

from office_hero_mcp.client import client
from office_hero_mcp.tools.custom import health, routing


def test_get_health_calls_client(monkeypatch):
    called = {}

    async def fake_get(path, **kwargs):
        called["path"] = path
        return {"status": "ok"}

    monkeypatch.setattr(client, "get", fake_get)
    inp = health.GetHealthInput()
    result = asyncio.run(health.get_health(inp))
    assert called["path"] == "/health"
    assert result == {"status": "ok"}


def test_get_routing_options_and_dispatch(monkeypatch):
    post_calls = []

    async def fake_post(path, **kwargs):
        post_calls.append((path, kwargs))
        # return a dummy structure
        return {"options": [1, 2, 3]}

    monkeypatch.setattr(client, "post", fake_post)

    inp = routing.RoutingOptionsInput(job_id=42)
    result = asyncio.run(routing.get_routing_options(inp))
    assert post_calls and post_calls[0][0] == "/jobs/42/routing-options"
    assert result == {"options": [1, 2, 3]}

    post_calls.clear()
    dispatch_inp = routing.DispatchJobInput(job_id=42, option_id="optX")
    dispatch_res = asyncio.run(routing.dispatch_job(dispatch_inp))
    assert post_calls[0][0] == "/jobs/42/dispatch"
    assert post_calls[0][1]["json"] == {"option_id": "optX"}
    assert dispatch_res == {"options": [1, 2, 3]}
