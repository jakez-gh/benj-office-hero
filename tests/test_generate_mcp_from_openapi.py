import json
import sys
from typing import Any

import pytest
from office_hero_mcp.client import client
from pydantic import ValidationError

from tools import generate_mcp_from_openapi as gen


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
    assert "client.post" in login_content
    assert "/auth/login" in login_content

    # dynamic import and invocation
    sys.path.insert(0, str(out_dir))
    try:
        import auth_login

        # usage of Pydantic models
        login_in = auth_login.AuthLoginInput(email="a", password="b")
        assert login_in.email == "a"

        # monkeypatch client methods
        called = []

        async def fake_post(path, **kwargs):
            called.append((path, kwargs))
            return {"ok": True}

        # use fixture passed into outer test
        monkeypatch.setattr(client, "post", fake_post)

        # actually call the async function by running loop
        import asyncio

        out = asyncio.run(auth_login.auth_login(login_in))
        assert out == {"ok": True}
        assert called[0][0] == "/auth/login"
        assert "json" in called[0][1]

        # invalid input should raise ValidationError
        with pytest.raises(ValidationError):
            auth_login.AuthLoginInput()  # missing fields -> error
    finally:
        sys.path.pop(0)


def test_generator_handles_missing_spec():
    with pytest.raises(SystemExit):
        gen.main(["prog"])
