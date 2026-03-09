"""User repository for database access."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.roles import Role
from office_hero.models import User


class UserRepository:
    """Async repository for User model CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with SQLAlchemy async session."""
        self.session = session

    async def get_by_email(self, email: str, tenant_id: UUID | None = None) -> User | None:
        """Fetch user by email. If tenant_id is provided, scope to that tenant."""
        stmt = select(User).where(User.email == email)
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch user by ID."""
        return await self.session.get(User, user_id)

    async def create(
        self,
        email: str,
        password_hash: str,
        tenant_id: UUID,
        role: Role,
        permissions: list | None = None,
    ) -> User:
        """Create and return a new user."""
        user = User(
            email=email,
            password_hash=password_hash,
            tenant_id=tenant_id,
            role=role.value,
            permissions=permissions or [],
            active=True,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_role(self, user_id: UUID, role: Role) -> User:
        """Update user's role and return the updated user."""
        user = await self.get_by_id(user_id)
        if user:
            user.role = role.value
            await self.session.flush()
        return user
