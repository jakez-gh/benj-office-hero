"""HTTP client wrapper for the Office Hero REST API.

The MCP server is a pure HTTP client per ADR 061. Each MCP tool call must
forward the caller's JWT to the REST API so that the same RBAC and tenant
rules apply (ADR 061 lines 80-81). This module exposes:

* `RESTClient` — a thin async wrapper around `httpx.AsyncClient`. Each
  instance carries its own bearer token (or none).
* `get_client(ctx)` — preferred constructor used by tools. It pulls the
  bearer token from the FastMCP request context (the inbound MCP request's
  Authorization header) and falls back to the `OFFICE_HERO_API_TOKEN`
  environment variable when the transport does not expose HTTP headers
  (e.g. stdio transport for local development).
* `client` — a module-level convenience singleton retained for backwards
  compatibility with tests and for the legacy unauthenticated path. New
  code should prefer `get_client(ctx)`.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic_settings import BaseSettings

try:  # pragma: no cover - import guard for environments without mcp installed
    from mcp.server.fastmcp import Context
except ImportError:  # pragma: no cover
    Context = None  # type: ignore[assignment,misc]


class Settings(BaseSettings):
    rest_api_base_url: str = ""


settings = Settings()


class RESTClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = base_url or settings.rest_api_base_url
        self._client = httpx.AsyncClient(base_url=self.base_url)
        self._token = token

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {})
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        response = await self._client.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)


def _extract_token(ctx: Any | None) -> str | None:
    """Pull the bearer token from the FastMCP request context.

    Order of precedence:
    1. ``Authorization: Bearer <token>`` header on the inbound MCP request
       (HTTP transports such as ``streamable-http`` and ``sse``).
    2. ``OFFICE_HERO_API_TOKEN`` environment variable, for stdio transport
       and for development against a fixed service token.

    Returns ``None`` when no token is available. Callers may choose to error
    out before issuing an unauthenticated request; the REST API will reject
    unauthenticated calls regardless.
    """

    if ctx is not None:
        request = getattr(getattr(ctx, "request_context", None), "request", None)
        headers = getattr(request, "headers", None)
        if headers is not None:
            raw = headers.get("authorization") or headers.get("Authorization")
            if raw:
                # accept both "Bearer xxx" and a bare token; strip the scheme
                parts = raw.split(None, 1)
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    return parts[1].strip()
                return raw.strip()

    env_token = os.getenv("OFFICE_HERO_API_TOKEN")
    if env_token:
        return env_token.strip()
    return None


def get_client(ctx: Any | None = None) -> RESTClient:
    """Construct a per-request ``RESTClient`` with the caller's JWT.

    Tools should call this from inside the tool function, passing the
    FastMCP ``Context`` they receive. A new client is constructed on every
    invocation so that tokens never leak across requests.
    """

    return RESTClient(token=_extract_token(ctx))


# Legacy module-level singleton. Retained because the existing test suite
# monkeypatches ``client.get`` / ``client.post`` and several generated tools
# still reference it. New code should prefer ``get_client(ctx)`` so that the
# inbound JWT is forwarded to the REST API.
client = RESTClient()
