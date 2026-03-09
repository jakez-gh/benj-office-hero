"""Diagnostic: verify database connectivity and list tables.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python tools/check_db.py

Requires DATABASE_URL environment variable (postgresql+asyncpg:// scheme).
"""

from __future__ import annotations

import asyncio
import os
import sys


async def check_db() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable not set.", file=sys.stderr)
        print(
            "  Export it before running:  export DATABASE_URL=postgresql+asyncpg://...",
            file=sys.stderr,
        )
        sys.exit(1)

    # asyncpg uses plain postgresql:// (no dialect suffix)
    asyncpg_url = url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        import asyncpg  # noqa: PLC0415 — optional dependency for this tool

        conn = await asyncpg.connect(asyncpg_url)
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name;"
        )
        print(f"Connected successfully. Tables ({len(tables)}):")
        for t in tables:
            print(f"  - {t['table_name']}")

        if any(t["table_name"] == "users" for t in tables):
            users = await conn.fetch("SELECT id, email FROM users LIMIT 5;")
            print("\nUsers (up to 5):")
            for u in users:
                print(f"  {u['id']}  {u['email']}")

        await conn.close()

    except ImportError:
        print("ERROR: asyncpg not installed. Run: pip install asyncpg", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_db())
