import sys

sys.path.insert(0, "src")

import asyncio
import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:pass@localhost:5432/test"

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from office_hero.core.config import Settings
from office_hero.models import Base, Tenant, User
from office_hero.services.auth_service import AuthService


async def init_db():
    """Initialize database with test data."""

    # Settings for auth service
    settings = Settings(
        database_url="postgresql+asyncpg://postgres:pass@localhost:5432/test",
        jwt_private_key="private",
        jwt_public_key="public",
        jwt_algorithm="RS256",
    )

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database schema created")

    # Create session factory
    async_session_local = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create test data
    async with async_session_local() as session:
        # Check for existing test tenant
        from sqlalchemy import select

        existing_tenant = (
            await session.execute(select(Tenant).filter_by(name="Test Company"))
        ).scalar_one_or_none()

        if existing_tenant:
            tenant = existing_tenant
            print(f"✓ Test tenant already exists: {tenant.name}")
        else:
            tenant = Tenant(name="Test Company")
            session.add(tenant)
            await session.commit()
            print(f"✓ Test tenant created: {tenant.name}")

        # Check for existing test user
        existing_user = (
            await session.execute(select(User).filter_by(email="test@example.com"))
        ).scalar_one_or_none()

        if existing_user:
            print("✓ Test user already exists: test@example.com")
        else:
            # Create user
            auth_service = AuthService(settings)
            password_hash = auth_service.hash_password("password123")

            user = User(
                tenant_id=tenant.id,
                email="test@example.com",
                password_hash=password_hash,
                role="admin",
                permissions=["*"],
                active=True,
            )
            session.add(user)
            await session.commit()
            print("✓ Test user created: test@example.com / password123")

    await engine.dispose()
    print("✓ Database ready for integration testing")


if __name__ == "__main__":
    asyncio.run(init_db())
