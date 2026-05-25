import asyncio

import pytest

pytest.importorskip("mcp", reason="mcp package not installed — run from mcp-server/")

from office_hero_mcp.tools.custom import health, routing  # noqa: E402


class _FakeClient:
    """Records calls and returns canned responses for tool tests."""

    def __init__(self, get_response=None, post_response=None):
        self._get_response = get_response
        self._post_response = post_response
        self.get_calls: list[tuple[str, dict]] = []
        self.post_calls: list[tuple[str, dict]] = []

    async def get(self, path, **kwargs):
        self.get_calls.append((path, kwargs))
        return self._get_response

    async def post(self, path, **kwargs):
        self.post_calls.append((path, kwargs))
        return self._post_response


def test_get_health_calls_client(monkeypatch):
    fake = _FakeClient(get_response={"status": "ok"})
    # patch the get_client factory inside the health module so the tool
    # obtains our fake instead of constructing a real httpx-backed client.
    monkeypatch.setattr(health, "get_client", lambda ctx=None: fake)
    inp = health.GetHealthInput()
    result = asyncio.run(health.get_health(inp, ctx=None))
    assert fake.get_calls and fake.get_calls[0][0] == "/health"
    assert result == {"status": "ok"}


def test_get_routing_options_and_dispatch(monkeypatch):
    fake = _FakeClient(post_response={"options": [1, 2, 3]})
    monkeypatch.setattr(routing, "get_client", lambda ctx=None: fake)

    inp = routing.RoutingOptionsInput(job_id=42)
    result = asyncio.run(routing.get_routing_options(inp, ctx=None))
    assert fake.post_calls and fake.post_calls[0][0] == "/jobs/42/routing-options"
    assert result == {"options": [1, 2, 3]}

    fake.post_calls.clear()
    dispatch_inp = routing.DispatchJobInput(job_id=42, option_id="optX")
    dispatch_res = asyncio.run(routing.dispatch_job(dispatch_inp, ctx=None))
    assert fake.post_calls[0][0] == "/jobs/42/dispatch"
    assert fake.post_calls[0][1]["json"] == {"option_id": "optX"}
    assert dispatch_res == {"options": [1, 2, 3]}
