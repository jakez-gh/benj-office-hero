"""SQLAlchemy ORM models for Office Hero."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# Import all models so they register with Base.metadata
from office_hero.models.contract import Contract  # noqa: F401, E402
from office_hero.models.customer import Customer  # noqa: F401, E402
from office_hero.models.job import Job  # noqa: F401, E402
from office_hero.models.location import Location  # noqa: F401, E402
from office_hero.models.outbox_event import OutboxEvent  # noqa: F401, E402
from office_hero.models.route import Route, RouteStop  # noqa: F401, E402
from office_hero.models.saga_log import SagaLog  # noqa: F401, E402
from office_hero.models.tenant import Tenant  # noqa: F401, E402
from office_hero.models.token import RefreshToken  # noqa: F401, E402
from office_hero.models.user import User  # noqa: F401, E402
from office_hero.models.vehicle import Vehicle  # noqa: F401, E402
from office_hero.models.vehicle_crew import VehicleCrew, VehicleCrewMember  # noqa: F401, E402
from office_hero.models.vehicle_location import VehicleLocation  # noqa: F401, E402
from office_hero.models.jobber_credentials import JobberCredentials  # noqa: F401, E402
