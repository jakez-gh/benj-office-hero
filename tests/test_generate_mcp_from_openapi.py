import json
import sys
from typing import Any

import pytest

pytest.importorskip("mcp", reason="mcp package not installed — run from mcp-server/")

from pydantic import ValidationError  # noqa: E402

from tools import generate_mcp_from_openapi as gen  # noqa: E402


def make_auth_spec() -> dict[str, Any]:
    # minimal spec with the three auth endpoints
    return {
        "openapi": "3.0.0",
        "paths": {
            "/auth/login": {
                "post": {
                    "operationId": "auth_login",
                    "description": "Obtain JWT tokens",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                    },
                                    "required": ["email", "password"],
                                }
                            }
                        }
                    },
                }
            },
            "/auth/refresh": {
                "post": {
                    "operationId": "auth_refresh",
                    "description": "Refresh access token",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"refresh_token": {"type": "string"}},
                                }
                            }
                        }
                    },
                }
            },
            "/auth/logout": {
                "post": {
                    "operationId": "auth_logout",
                    "description": "Revoke tokens",
                }
            },
        },
    }


class _FakeClient:
    """Records calls and returns canned responses."""

    def __init__(self, response):
        self._response = response
        self.calls: list[tuple[str, dict]] = []

    async def post(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return self._response

    async def get(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return self._response


def test_generate_auth_tools(tmp_path, monkeypatch):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(make_auth_spec()))

    out_dir = tmp_path / "generated"
    gen.generate(spec_path, out_dir)

    # files created
    files = {p.name for p in out_dir.iterdir()}
    assert files == {"auth_login.py", "auth_refresh.py", "auth_logout.py"}

    # inspect login file content
    login_content = (out_dir / "auth_login.py").read_text()
    assert "async def auth_login" in login_content
    # generated tools must use the per-request client factory (ADR 061)
    assert "get_client(ctx).post" in login_content
    assert "/auth/login" in login_content
    # tools must accept Context so JWT passthrough works
    assert "ctx: Context" in login_content

    # dynamic import and invocation
    sys.path.insert(0, str(out_dir))
    try:
        import auth_login

        # usage of Pydantic models
        login_in = auth_login.AuthLoginInput(email="a", password="b")
        assert login_in.email == "a"

        # patch the get_client factory inside the generated module so the
        # tool uses our fake instead of opening a real httpx connection.
        fake = _FakeClient({"ok": True})
        monkeypatch.setattr(auth_login, "get_client", lambda ctx=None: fake)

        # actually call the async function by running loop
        import asyncio

        out = asyncio.run(auth_login.auth_login(login_in, ctx=None))
        assert out == {"ok": True}
        assert fake.calls[0][0] == "/auth/login"
        assert "json" in fake.calls[0][1]

        # invalid input should raise ValidationError
        with pytest.raises(ValidationError):
            auth_login.AuthLoginInput()  # missing fields -> error
    finally:
        sys.path.pop(0)


def test_generator_handles_missing_spec():
    with pytest.raises(SystemExit):
        gen.main(["prog"])
