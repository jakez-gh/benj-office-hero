#!/usr/bin/env python
import os
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


if __name__ == "__main__":
    cli()
