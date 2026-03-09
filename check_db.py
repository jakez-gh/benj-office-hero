import asyncio
import sys

import asyncpg


async def check_db():
    try:
        conn = await asyncpg.connect("postgresql://postgres:pass@localhost:5432/test")
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        )
        print("Tables:", [t["table_name"] for t in tables])

        # Check users table
        if any(t["table_name"] == "users" for t in tables):
            users = await conn.fetch("SELECT id, email FROM users LIMIT 5;")
            print("Existing users:", users)
        else:
            print("No users table found")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


asyncio.run(check_db())
