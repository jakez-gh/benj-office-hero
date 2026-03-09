#!/usr/bin/env python
import subprocess
import sys

import click

from tools.client import Client


@click.group()
def cli():
    """Office Hero operator CLI."""
    pass


@cli.command()
@click.option("--url", default=None, help="API base URL")
@click.option("--token", default=None, help="Bearer token")
def health(url, token):
    """Call GET /health and print the JSON response."""
    client = Client(base_url=url, token=token)
    try:
        resp = client.get("/health")
    except Exception as e:
        click.echo(f"health check failed: {e}")
        sys.exit(1)
    click.echo(resp)
    client.close()


@cli.command()
def migrate():
    """Run alembic upgrade head."""
    result = subprocess.run(["alembic", "upgrade", "head"], check=False)
    sys.exit(result.returncode)


@cli.command()
@click.option("--host", default="127.0.0.1", help="API server host")
@click.option("--port", default=8000, type=int, help="API server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload on code changes")
def run_server(host, port, reload):
    """Start the Office Hero API server."""
    import uvicorn

    uvicorn.run(
        "office_hero.api:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    cli()
