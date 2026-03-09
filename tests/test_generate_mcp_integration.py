import json
import sys

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - fastapi may not be installed in CI
    pytest.skip("fastapi not available, skipping integration tests", allow_module_level=True)

from office_hero_mcp.client import client

from tools.generate_mcp_from_openapi import generate


class Tokens(BaseModel):
    access_token: str
    refresh_token: str


def create_auth_app() -> FastAPI:
    app = FastAPI()

    class LoginRequest(BaseModel):
        email: str
        password: str

    @app.post("/auth/login", response_model=Tokens)
    def login(req: LoginRequest):
        # echo back some dummy tokens
        return {"access_token": "x", "refresh_token": "y"}

    class RefreshRequest(BaseModel):
        refresh_token: str

    @app.post("/auth/refresh", response_model=Tokens)
    def refresh(req: RefreshRequest):
        return {"access_token": "x2", "refresh_token": "y2"}

    @app.post("/auth/logout")
    def logout():
        return {"ok": True}

    return app


def test_generate_and_call_against_fastapi(tmp_path):
    # spin up the test FastAPI app and grab spec
    app = create_auth_app()
    client_app = TestClient(app)
    spec = client_app.get("/openapi.json").json()

    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    out_dir = tmp_path / "generated"

    # generate tools from the live spec
    generate(spec_file, out_dir)

    # check that auth tools were created
    names = {p.name for p in out_dir.iterdir()}
    assert {"auth_login.py", "auth_refresh.py", "auth_logout.py"}.issubset(names)

    # import generated module and ensure it calls through to client
    sys_path_before = list(sys.path)
    sys.path.insert(0, str(out_dir))
    try:
        import auth_login

        # patch the client to use HTTP calls against our testserver
        called = []

        def http_post(path, **kwargs):
            called.append((path, kwargs))
            # forward to TestClient
            r = client_app.post(path, json=kwargs.get("json"), params=kwargs.get("params"))
            r.raise_for_status()
            return r.json()

        # simple sync wrapper to match async signature
        async def fake_post(path, **kwargs):
            return http_post(path, **kwargs)

        pytest.monkeypatch.setattr(client, "post", fake_post)

        import asyncio

        inp = auth_login.AuthLoginInput(email="a@example.com", password="pw")
        res = asyncio.run(auth_login.auth_login(inp))
        assert res["access_token"] == "x"
        assert called and called[0][0] == "/auth/login"
    finally:
        sys.path[:] = sys_path_before
