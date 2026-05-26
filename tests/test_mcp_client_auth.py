"""Tests for the JWT passthrough behaviour of office_hero_mcp.client.

ADR 061 (lines 80-81) requires the MCP server to forward the caller's JWT
to the REST API on every tool call. ``get_client`` is the per-request
factory that enforces this. These tests exercise the precedence:
    1. Authorization header on the inbound MCP request.
    2. ``OFFICE_HERO_API_TOKEN`` environment variable (stdio transport).
    3. No token (caller will get 401 from REST API).
"""

import pytest

pytest.importorskip("mcp", reason="mcp package not installed — run from mcp-server/")

from types import SimpleNamespace  # noqa: E402

from office_hero_mcp.client import RESTClient, _extract_token, get_client  # noqa: E402


def _make_ctx(headers: dict[str, str] | None) -> SimpleNamespace:
    """Build a Context-like object with a Starlette-style request.headers mapping."""
    request = SimpleNamespace(headers=headers) if headers is not None else None
    request_context = SimpleNamespace(request=request)
    return SimpleNamespace(request_context=request_context)


def test_extract_token_prefers_bearer_header(monkeypatch):
    monkeypatch.delenv("OFFICE_HERO_API_TOKEN", raising=False)
    ctx = _make_ctx({"authorization": "Bearer header-token"})
    assert _extract_token(ctx) == "header-token"


def test_extract_token_accepts_capitalised_header(monkeypatch):
    monkeypatch.delenv("OFFICE_HERO_API_TOKEN", raising=False)
    ctx = _make_ctx({"Authorization": "Bearer header-token"})
    assert _extract_token(ctx) == "header-token"


def test_extract_token_accepts_bare_token(monkeypatch):
    monkeypatch.delenv("OFFICE_HERO_API_TOKEN", raising=False)
    ctx = _make_ctx({"authorization": "raw-token"})
    assert _extract_token(ctx) == "raw-token"


def test_extract_token_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("OFFICE_HERO_API_TOKEN", "env-token")
    ctx = _make_ctx(None)
    assert _extract_token(ctx) == "env-token"


def test_extract_token_returns_none_without_anything(monkeypatch):
    monkeypatch.delenv("OFFICE_HERO_API_TOKEN", raising=False)
    assert _extract_token(None) is None
    assert _extract_token(_make_ctx(None)) is None


def test_get_client_returns_per_request_client(monkeypatch):
    monkeypatch.delenv("OFFICE_HERO_API_TOKEN", raising=False)
    ctx_a = _make_ctx({"authorization": "Bearer token-a"})
    ctx_b = _make_ctx({"authorization": "Bearer token-b"})

    a = get_client(ctx_a)
    b = get_client(ctx_b)

    assert isinstance(a, RESTClient)
    assert isinstance(b, RESTClient)
    assert a is not b
    assert a._token == "token-a"
    assert b._token == "token-b"


def test_rest_client_forwards_token_as_bearer():
    """RESTClient.request must set Authorization: Bearer <token> on outgoing calls."""
    import asyncio

    rc = RESTClient(token="my-jwt")
    captured: dict[str, dict] = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class _Async:
        async def request(self, method, path, headers=None, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["headers"] = headers or {}
            return _Resp()

    rc._client = _Async()  # type: ignore[assignment]
    asyncio.run(rc.get("/whoami"))

    assert captured["headers"].get("Authorization") == "Bearer my-jwt"
    assert captured["method"] == "GET"
    assert captured["path"] == "/whoami"
