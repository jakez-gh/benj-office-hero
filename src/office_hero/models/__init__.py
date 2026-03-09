"""SQLAlchemy ORM models for Office Hero."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# Import all models so they register with Base.metadata
from office_hero.models.tenant import Tenant  # noqa: F401, E402
from office_hero.models.token import RefreshToken  # noqa: F401, E402
from office_hero.models.user import User  # noqa: F401, E402
