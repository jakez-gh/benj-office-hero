#!/usr/bin/env python
"""Office Hero operator CLI.

Usage:
    hero health              — ping the API /health endpoint
    hero db migrate          — run alembic upgrade head
    hero db rollback         — downgrade one revision
    hero db status           — show current alembic revision
    hero jwt generate        — mint a signed JWT for API testing
    hero run-server          — start uvicorn (dev use)

Reads API_BASE_URL and API_TOKEN from environment (or --url / --token flags).
Reads JWT_PRIVATE_KEY and JWT_ALGORITHM from environment for jwt commands.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta

import click

from tools.client import Client


@click.group()
def cli():
    """Office Hero operator CLI."""
    pass


# ── health ────────────────────────────────────────────────────────────────────


@cli.command()
@click.option(
    "--url", default=None, help="API base URL (default: $API_BASE_URL or http://localhost:8000)"
)
@click.option("--token", default=None, help="Bearer token (default: $API_TOKEN)")
def health(url, token):
    """Call GET /health and print the JSON response."""
    client = Client(base_url=url, token=token)
    try:
        resp = client.get("/health")
    except Exception as exc:
        click.secho(f"health check failed: {exc}", fg="red", err=True)
        sys.exit(1)
    click.echo(json.dumps(resp, indent=2))
    client.close()


# ── db subcommands ────────────────────────────────────────────────────────────


@cli.group()
def db():
    """Database migration commands (wraps Alembic)."""
    pass


@db.command()
def migrate():
    """Run alembic upgrade head — apply all pending migrations."""
    result = subprocess.run(["alembic", "upgrade", "head"], check=False)
    sys.exit(result.returncode)


@db.command()
@click.argument("revision", default="-1")
def rollback(revision):
    """Downgrade by one revision (or to a specific revision)."""
    result = subprocess.run(["alembic", "downgrade", revision], check=False)
    sys.exit(result.returncode)


@db.command()
def status():
    """Show current alembic revision (alembic current)."""
    result = subprocess.run(["alembic", "current"], check=False)
    sys.exit(result.returncode)


@db.command()
def history():
    """Show alembic migration history."""
    result = subprocess.run(["alembic", "history", "--verbose"], check=False)
    sys.exit(result.returncode)


# ── jwt subcommands ───────────────────────────────────────────────────────────


@cli.group()
def jwt():
    """JWT token utilities for testing and operator use."""
    pass


@jwt.command("generate")
@click.option("--tenant-id", required=True, help="Tenant UUID to embed in the token")
@click.option("--user-id", default=None, help="User UUID (random UUID if omitted)")
@click.option("--email", default="admin@hero.local", show_default=True, help="Email claim")
@click.option(
    "--role",
    default="tenant_admin",
    show_default=True,
    type=click.Choice(
        ["operator", "tenant_admin", "dispatcher", "technician", "billing", "read_only"]
    ),
    help="Role claim",
)
@click.option("--expires", default=60, show_default=True, type=int, help="Lifetime in minutes")
def jwt_generate(tenant_id, user_id, email, role, expires):
    """Mint a signed RS256 JWT for API testing.

    Reads JWT_PRIVATE_KEY and JWT_ALGORITHM from environment.
    The generated token can be passed as a Bearer token to any API endpoint.
    """
    try:
        from jose import jwt as jose_jwt
    except ImportError:
        click.secho("python-jose not installed. Run: poetry install", fg="red", err=True)
        sys.exit(1)

    private_key_raw = os.environ.get("JWT_PRIVATE_KEY")
    if not private_key_raw:
        click.secho("JWT_PRIVATE_KEY environment variable is not set.", fg="red", err=True)
        sys.exit(1)

    # Support \n-escaped key (single-line env var form)
    private_key = private_key_raw.replace("\\n", "\n")
    algorithm = os.environ.get("JWT_ALGORITHM", "RS256")
    user_id = user_id or str(uuid.uuid4())

    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "permissions": _permissions_for_role(role),
        "iat": now,
        "exp": now + timedelta(minutes=expires),
    }

    try:
        token = jose_jwt.encode(payload, private_key, algorithm=algorithm)
    except Exception as exc:
        click.secho(f"JWT encoding failed: {exc}", fg="red", err=True)
        sys.exit(1)

    click.echo(token)
    click.secho(
        f"\n# Expires in {expires} min | tenant={tenant_id} | role={role}",
        fg="cyan",
        err=True,
    )
    click.secho(
        "# Usage: curl -H 'Authorization: Bearer <token>' http://localhost:8000/...",
        fg="cyan",
        err=True,
    )


def _permissions_for_role(role: str) -> list[str]:
    """Return the default permission set for a role (mirrors RBAC in core/)."""
    base = {
        "operator": ["*"],
        "tenant_admin": [
            "tenant:read",
            "tenant:write",
            "user:read",
            "user:write",
            "customer:read",
            "customer:write",
            "job:read",
            "job:write",
            "job:dispatch",
            "route:read",
            "route:write",
            "vehicle:read",
            "vehicle:write",
            "contract:read",
            "contract:write",
        ],
        "dispatcher": [
            "customer:read",
            "job:read",
            "job:dispatch",
            "route:read",
            "route:write",
            "vehicle:read",
        ],
        "technician": ["route:read", "job:read", "vehicle:write"],
        "billing": ["customer:read", "job:read", "contract:read"],
        "read_only": ["customer:read", "job:read", "route:read", "vehicle:read"],
    }
    return base.get(role, [])


# ── run-server ────────────────────────────────────────────────────────────────


@cli.command("run-server")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True, type=int)
@click.option("--reload", is_flag=True, help="Enable auto-reload on code changes")
def run_server(host, port, reload):
    """Start the Office Hero API server (dev use; use Fly.io for production)."""
    import uvicorn

    uvicorn.run("office_hero.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
