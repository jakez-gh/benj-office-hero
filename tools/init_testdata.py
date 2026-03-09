"""Dev utility: seed a local database with a test tenant and user.

Usage:
    export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb
    export JWT_PRIVATE_KEY="$(cat keys/private.pem)"
    export JWT_PUBLIC_KEY="$(cat keys/public.pem)"
    python tools/init_testdata.py

All configuration comes from environment variables — no hardcoded credentials.
See docs/glossary.md for the tenant/user model and role definitions.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Allow running from project root without pip install -e .
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def init_testdata() -> None:
    """Create a test Tenant and admin User if they do not already exist."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from office_hero.core.config import Settings
    from office_hero.models import Base, Tenant, User
    from office_hero.services.auth_service import AuthService

    settings = Settings()  # reads all values from environment

    engine = create_async_engine(settings.database_url, echo=False)

    # Ensure schema is up to date (idempotent create_all — does not drop)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Schema verified")

    async_session: sessionmaker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ── Tenant ──────────────────────────────────────────────────────────
        existing_tenant = (
            await session.execute(select(Tenant).where(Tenant.name == "Test Company"))
        ).scalar_one_or_none()

        if existing_tenant:
            tenant = existing_tenant
            print(f"✓ Tenant already exists: {tenant.name}  id={tenant.id}")
        else:
            tenant = Tenant(name="Test Company")
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            print(f"✓ Tenant created: {tenant.name}  id={tenant.id}")

        # ── User ─────────────────────────────────────────────────────────────
        existing_user = (
            await session.execute(select(User).where(User.email == "admin@test.local"))
        ).scalar_one_or_none()

        if existing_user:
            print(f"✓ User already exists: {existing_user.email}")
        else:
            auth_service = AuthService(settings)
            password_hash = auth_service.hash_password("password123")

            user = User(
                tenant_id=tenant.id,
                email="admin@test.local",
                password_hash=password_hash,
                role="owner",
                permissions=["*"],
                active=True,
            )
            session.add(user)
            await session.commit()
            print("✓ User created: admin@test.local  role=owner  password=password123")

    await engine.dispose()
    print("✓ Test data ready.")


if __name__ == "__main__":
    asyncio.run(init_testdata())
