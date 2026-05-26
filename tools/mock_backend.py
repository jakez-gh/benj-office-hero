"""Simple mock backend server for MCP testing.

This uses FastAPI and replicates the auth endpoints used by our generator
integration tests.  The script can be invoked directly or imported by other
code.  It is intentionally small and self-contained so that Slice 23 can be
tested without needing the full backend-core checkout.

Usage:
    python tools/mock_backend.py [--host 127.0.0.1] [--port 8000]

A Git hook could also call this script to ensure some server is running while
quality checks execute.
"""

import argparse

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError as err:  # pragma: no cover
    raise RuntimeError("fastapi must be installed to run the mock backend") from err


def create_app() -> FastAPI:
    app = FastAPI()

    class LoginRequest(BaseModel):
        email: str
        password: str

    class Tokens(BaseModel):
        access_token: str
        refresh_token: str

    @app.post("/auth/login", response_model=Tokens)
    def login(req: LoginRequest):
        # dummy implementation returns static tokens
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    import uvicorn

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)
