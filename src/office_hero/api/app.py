"""Office Hero FastAPI application factory (SOLID: SRP, DIP).

The app is constructed via ``create_app`` so saga / outbox dependencies can be
injected at startup (tests pass mocks; production wires the real repositories).
A module-level ``app`` instance is created at import time using the in-memory
mock repositories so legacy tests that do ``from office_hero.api.app import app``
continue to work.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from office_hero.adapters.geocoding.stub import StubGeocodingAdapter
from office_hero.api.exception_handlers import register_exception_handlers
from office_hero.api.limiter import limiter
from office_hero.api.middleware.logging import LoggingMiddleware
from office_hero.api.middleware.security_headers import SecurityHeadersMiddleware
from office_hero.api.routes import health
from office_hero.api.routes.admin import audit_router, create_admin_router
from office_hero.api.routes.customers import create_customer_router
from office_hero.api.routes.dispatch import create_dispatch_router
from office_hero.api.routes.jobs import create_job_router
from office_hero.api.routes.tech import create_tech_router
from office_hero.api.routes.locations import create_location_router
from office_hero.api.routes.sagas import create_saga_router
from office_hero.api.routes.schedule_options import create_schedule_options_router
from office_hero.api.routes.vehicle_crews import create_vehicle_crew_router
from office_hero.api.routes.vehicles import create_vehicle_router
from office_hero.api.state import (
    set_auth_service,
    set_customer_service,
    set_engine,
    set_geocoding_adapter,
    set_job_dispatch_service,
    set_job_service,
    set_location_service,
    set_schedule_suggestion_service,
    set_vehicle_crew_service,
    set_vehicle_service,
)
from office_hero.core.logging import get_logger
from office_hero.repositories.customer_repository import (
    InMemoryCustomerRepository,
)
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.location_repository import (
    InMemoryLocationRepository,
)
from office_hero.repositories.mocks import (
    InMemoryAuditService,
    MockOutboxRepository,
    MockSagaRepository,
)
from office_hero.repositories.protocols import OutboxRepository
from office_hero.repositories.vehicle_crew_repository import InMemoryVehicleCrewRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.custom_field_templates import (
    registry as _template_registry_module,
)  # noqa: F401
from office_hero.services.customer_service import CustomerService
from office_hero.services.job_dispatch_service import JobDispatchService
from office_hero.services.job_service import JobService
from office_hero.services.location_service import LocationService
from office_hero.services.saga_service import SagaService
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService
from office_hero.services.vehicle_crew_service import VehicleCrewService
from office_hero.services.vehicle_service import VehicleService

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: bring up shared resources, then dispose them.

    Startup:
        * Build the async SQLAlchemy engine from ``DATABASE_URL`` (if set) and
          register it in module-level state so request handlers can resolve it
          via ``office_hero.api.state.get_engine``.
        * Build the ``AuthService`` from environment-derived ``Settings`` (if
          ``JWT_PRIVATE_KEY``/``JWT_PUBLIC_KEY`` are present) and register it
          in module-level state.

    Shutdown:
        * Dispose the engine pool so connections are released cleanly.

    Missing config is treated as non-fatal at startup — individual routes
    will surface a ``RuntimeError`` if they try to use an uninitialized
    dependency. This keeps the test environment (which never has Postgres
    available) working while still wiring real lifecycle in production.
    """
    engine = None
    try:
        try:
            from office_hero.core.config import get_settings
            from office_hero.db.engine import create_engine
            from office_hero.services.auth_service import AuthService

            settings = get_settings()
            engine = create_engine(settings.database_url)
            set_engine(engine)
            set_auth_service(AuthService(settings))
            log.info("app.lifespan.startup", db="ready", auth="ready")
        except Exception as exc:  # noqa: BLE001 - intentional broad catch
            log.warning("app.lifespan.startup_skipped", error=str(exc))

        yield
    finally:
        if engine is not None:
            try:
                await engine.dispose()
                log.info("app.lifespan.shutdown", db="disposed")
            except Exception as exc:  # noqa: BLE001 - intentional broad catch
                log.warning("app.lifespan.shutdown_failed", error=str(exc))


def create_app(
    *,
    saga_service: SagaService | None = None,
    outbox_repo: OutboxRepository | None = None,
    customer_service: CustomerService | None = None,
    location_service: LocationService | None = None,
    job_service: JobService | None = None,
    vehicle_service: VehicleService | None = None,
    vehicle_crew_service: VehicleCrewService | None = None,
    schedule_suggestion_service: ScheduleSuggestionService | None = None,
    job_dispatch_service: JobDispatchService | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Wires middleware (order matters - outermost first), exception handlers,
    the slowapi rate limiter, and all route routers.

    Args:
        saga_service: Saga orchestrator. Defaults to an in-memory mock-backed
            instance so the module-level ``app`` boots without a database.
        outbox_repo: Outbox repository for dead-letter routes. Defaults to an
            in-memory mock.
        customer_service: Slice-9 CustomerService. Defaults to an in-memory
            implementation so tests can construct ``create_app()`` without
            wiring a DB session.
        location_service: Slice-9 LocationService (same defaulting behaviour).
        job_service: Slice-10 JobService. Defaults to an in-memory
            implementation so tests boot without a database.
        vehicle_service: Slice-12 VehicleService. Defaults to in-memory.
        vehicle_crew_service: Slice-12 VehicleCrewService. Defaults to in-memory.

    The factory invokes router factories once at startup, not per-request.
    """
    if saga_service is None:
        saga_service = SagaService(saga_repo=MockSagaRepository())
    if outbox_repo is None:
        outbox_repo = MockOutboxRepository()

    # Slice-9/10 defaults: in-memory repositories + the stub geocoder. These let
    # the module-level ``app`` boot without a database and keep API tests off
    # the live Nominatim service.
    audit = InMemoryAuditService()
    cust_repo = InMemoryCustomerRepository()
    loc_repo = InMemoryLocationRepository()
    geocoder = StubGeocodingAdapter()

    if customer_service is None:
        customer_service = CustomerService(repo=cust_repo, audit=audit)
    if location_service is None:
        location_service = LocationService(
            repo=loc_repo,
            customer_repo=cust_repo,
            audit=audit,
            geocoder=geocoder,
        )
    _default_job_repo: InMemoryJobRepository | None = None
    if job_service is None:
        _default_job_repo = InMemoryJobRepository()
        job_service = JobService(
            repo=_default_job_repo,
            customer_repo=cust_repo,
            location_repo=loc_repo,
            audit=audit,
            template_registry=_template_registry_module,
        )
    set_geocoding_adapter(geocoder)
    set_customer_service(customer_service)
    set_location_service(location_service)
    set_job_service(job_service)

    # Slice-12 defaults: in-memory vehicle repos
    _default_v_repo: InMemoryVehicleRepository | None = None
    if vehicle_service is None or vehicle_crew_service is None:
        v_audit = InMemoryAuditService()
        _default_v_repo = InMemoryVehicleRepository()
        vc_repo = InMemoryVehicleCrewRepository()
        _default_v_repo._crew_repo = vc_repo  # cross-reference for list_active_for_date

        class _NoopUserRepo:
            async def get_by_id(self, user_id, tenant_id):
                return None

        if vehicle_service is None:
            vehicle_service = VehicleService(repo=_default_v_repo, audit=v_audit, crew_repo=vc_repo)
        if vehicle_crew_service is None:
            vehicle_crew_service = VehicleCrewService(
                crew_repo=vc_repo,
                vehicle_repo=_default_v_repo,
                user_repo=_NoopUserRepo(),
                audit=v_audit,
            )

    set_vehicle_service(vehicle_service)
    set_vehicle_crew_service(vehicle_crew_service)

    # Slice-13: schedule suggestion service
    if schedule_suggestion_service is None:
        from office_hero.adapters.routing.stub import StubRoutingAdapter

        schedule_suggestion_service = ScheduleSuggestionService(
            job_repo=_default_job_repo or InMemoryJobRepository(),
            vehicle_repo=_default_v_repo or InMemoryVehicleRepository(),
            routing_adapter=StubRoutingAdapter(),
        )
    set_schedule_suggestion_service(schedule_suggestion_service)

    # Slice-14: job dispatch service
    if job_dispatch_service is None:
        job_dispatch_service = JobDispatchService(
            job_repo=_default_job_repo or InMemoryJobRepository(),
            vehicle_repo=_default_v_repo or InMemoryVehicleRepository(),
        )
    set_job_dispatch_service(job_dispatch_service)

    application = FastAPI(
        title="Office Hero",
        description="Back-office management API for office services",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- Middleware (outermost -> innermost) ---
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(LoggingMiddleware)

    # --- Exception handlers ---
    register_exception_handlers(application)

    # --- slowapi rate limiter state ---
    application.state.limiter = limiter

    # --- Routers ---
    application.include_router(health.router, tags=["health"])

    saga_router = create_saga_router(saga_service=saga_service)
    application.include_router(saga_router, prefix="/sagas", tags=["sagas"])

    admin_router = create_admin_router(
        saga_service=saga_service,
        outbox_repo=outbox_repo,
    )
    application.include_router(admin_router, prefix="/admin", tags=["admin"])
    application.include_router(audit_router, prefix="/admin", tags=["admin"])

    customer_router = create_customer_router(
        service_provider=lambda: customer_service,
        location_service_provider=lambda: location_service,
    )
    application.include_router(customer_router, prefix="/customers", tags=["customers"])

    location_router = create_location_router(service_provider=lambda: location_service)
    application.include_router(location_router, tags=["locations"])

    job_router = create_job_router(service_provider=lambda: job_service)
    application.include_router(job_router, prefix="/jobs", tags=["jobs"])

    vehicle_router = create_vehicle_router(service_provider=lambda: vehicle_service)
    application.include_router(vehicle_router, prefix="/vehicles", tags=["vehicles"])

    crew_router = create_vehicle_crew_router(
        service_provider=lambda: vehicle_crew_service,
        vehicle_service_provider=lambda: vehicle_service,
    )
    application.include_router(crew_router, tags=["crews"])

    schedule_options_router = create_schedule_options_router(
        service_provider=lambda: schedule_suggestion_service,
    )
    application.include_router(schedule_options_router, tags=["schedule-options"])

    dispatch_router = create_dispatch_router(
        service_provider=lambda: job_dispatch_service,
    )
    application.include_router(dispatch_router, tags=["dispatch"])

    tech_router = create_tech_router(
        crew_service_provider=lambda: vehicle_crew_service,
    )
    application.include_router(tech_router, tags=["tech"])

    return application


# Module-level instance used by TestClient and uvicorn. Uses in-memory mocks
# so the import succeeds without a live database; production callers should
# build their own app via ``create_app(saga_service=..., outbox_repo=...)``.
app = create_app()
