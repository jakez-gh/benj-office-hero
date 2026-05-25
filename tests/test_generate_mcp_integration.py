import json
import sys

import pytest

pytest.importorskip("mcp", reason="mcp package not installed — run from mcp-server/")

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - fastapi may not be installed in CI
    pytest.skip("fastapi not available, skipping integration tests", allow_module_level=True)

from tools.generate_mcp_from_openapi import generate  # noqa: E402


class Tokens(BaseModel):
    access_token: str
    refresh_token: str


def create_auth_app() -> FastAPI:
    app = FastAPI()

    class LoginRequest(BaseModel):
        email: str
        password: str

    @app.post("/auth/login", response_model=Tokens, operation_id="auth_login")
    def login(req: LoginRequest):
        # echo back some dummy tokens
        return {"access_token": "x", "refresh_token": "y"}

    class RefreshRequest(BaseModel):
        refresh_token: str

    @app.post("/auth/refresh", response_model=Tokens, operation_id="auth_refresh")
    def refresh(req: RefreshRequest):
        return {"access_token": "x2", "refresh_token": "y2"}

    @app.post("/auth/logout", operation_id="auth_logout")
    def logout():
        return {"ok": True}

    return app


def test_generate_and_call_against_fastapi(tmp_path, monkeypatch):
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

        # patch the per-request client factory inside the generated module
        # so the tool actually calls the FastAPI TestClient instead of
        # opening a real httpx connection.
        called: list[tuple[str, dict]] = []

        class _Bridge:
            async def post(self, path, **kwargs):
                called.append((path, kwargs))
                r = client_app.post(path, json=kwargs.get("json"), params=kwargs.get("params"))
                r.raise_for_status()
                return r.json()

            async def get(self, path, **kwargs):
                called.append((path, kwargs))
                r = client_app.get(path, params=kwargs.get("params"))
                r.raise_for_status()
                return r.json()

        bridge = _Bridge()
        monkeypatch.setattr(auth_login, "get_client", lambda ctx=None: bridge)

        import asyncio

        inp = auth_login.AuthLoginInput(email="a@example.com", password="pw")
        res = asyncio.run(auth_login.auth_login(inp, ctx=None))
        assert res["access_token"] == "x"
        assert called and called[0][0] == "/auth/login"
    finally:
        sys.path[:] = sys_path_before
