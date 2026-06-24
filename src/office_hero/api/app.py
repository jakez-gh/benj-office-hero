"""Office Hero FastAPI application factory (SOLID: SRP, DIP).

The app is constructed via ``create_app`` so saga / outbox dependencies can be
injected at startup (tests pass mocks; production wires the real repositories).
A module-level ``app`` instance is created at import time using the in-memory
mock repositories so legacy tests that do ``from office_hero.api.app import app``
continue to work.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from office_hero.adapters.geocoding.stub import StubGeocodingAdapter
from office_hero.api.exception_handlers import register_exception_handlers
from office_hero.api.limiter import limiter
from office_hero.api.middleware.auth import JWTAuthMiddleware
from office_hero.api.middleware.logging import LoggingMiddleware
from office_hero.api.middleware.security_headers import SecurityHeadersMiddleware
from office_hero.api.middleware.test_auth import TestAuthMiddleware, test_auth_enabled
from office_hero.api.routes import auth, health
from office_hero.api.routes.admin import audit_router, create_admin_router, rate_limits_router
from office_hero.api.routes.integrations import create_integrations_router
from office_hero.api.routes.contracts import create_contract_router
from office_hero.api.routes.customers import create_customer_router
from office_hero.api.routes.dispatch import create_dispatch_router
from office_hero.api.routes.jobs import create_job_router
from office_hero.api.routes.locations import create_location_router
from office_hero.api.routes.routes import create_routes_router
from office_hero.api.routes.sagas import create_saga_router
from office_hero.api.routes.schedule_options import create_schedule_options_router
from office_hero.api.routes.tech import create_tech_router
from office_hero.api.routes.vehicle_crews import create_vehicle_crew_router
from office_hero.api.routes.vehicle_location import create_vehicle_location_router
from office_hero.api.routes.vehicles import create_vehicle_router
from office_hero.api.state import (
    get_route_repository,
    get_route_stop_repository,
    set_auth_service,
    set_contract_service,
    set_customer_service,
    set_dispatch_service,
    set_dynamic_dispatch_service,
    set_engine,
    set_geocoding_adapter,
    set_job_dispatch_service,
    set_job_service,
    set_location_service,
    set_route_repository,
    set_route_stop_repository,
    set_schedule_suggestion_service,
    set_vehicle_crew_service,
    set_vehicle_service,
)
from office_hero.core.logging import get_logger
from office_hero.repositories.contract_repository import InMemoryContractRepository
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
from office_hero.repositories.route_repository import InMemoryRouteRepository
from office_hero.repositories.route_stop_repository import InMemoryRouteStopRepository
from office_hero.repositories.vehicle_crew_repository import InMemoryVehicleCrewRepository
from office_hero.repositories.vehicle_location_repository import InMemoryVehicleLocationRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.back_office_sync_service import BackOfficeSyncService
from office_hero.services.contract_service import ContractService
from office_hero.services.custom_field_templates import (
    registry as _template_registry_module,
)  # noqa: F401
from office_hero.services.customer_service import CustomerService
from office_hero.services.dispatch_service import DispatchService
from office_hero.services.dynamic_dispatch_service import DynamicDispatchService
from office_hero.services.job_dispatch_service import JobDispatchService
from office_hero.services.job_service import JobService
from office_hero.services.location_service import LocationService
from office_hero.services.saga_service import SagaService
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService
from office_hero.services.vehicle_crew_service import VehicleCrewService
from office_hero.services.vehicle_location_service import VehicleLocationService
from office_hero.services.vehicle_service import VehicleService

log = get_logger(__name__)


def _register_back_office_adapters() -> None:
    """Conditionally register concrete back-office adapters present in env.

    Non-fatal when credentials are absent — those adapters simply won't be
    available and tenants configured for them fall back to 'native'.  This
    keeps the in-memory / test environment booting without any credentials.
    """
    from office_hero.adapters.back_office.registry import register_adapter  # noqa: PLC0415

    if all(
        os.environ.get(k)
        for k in (
            "SERVICETITAN_CLIENT_ID",
            "SERVICETITAN_CLIENT_SECRET",
            "SERVICETITAN_APP_KEY",
            "SERVICETITAN_TENANT_ID",
        )
    ):
        from office_hero.adapters.back_office.servicetitan import ServiceTitanAdapter  # noqa: PLC0415

        register_adapter("servicetitan", ServiceTitanAdapter.from_tenant)
        log.info("back_office.registered", adapter="servicetitan")

    if all(os.environ.get(k) for k in ("JOBBER_CLIENT_ID", "JOBBER_CLIENT_SECRET")):
        from office_hero.adapters.back_office.jobber import JobberAdapter  # noqa: PLC0415

        register_adapter("jobber", JobberAdapter.from_tenant)
        log.info("back_office.registered", adapter="jobber")

    # PestPac HTTP call layer is blocked on sandbox access (see RES-026 Q1).
    # Register once the NotImplementedError stubs are completed.
    if all(os.environ.get(k) for k in ("PESTPAC_API_KEY", "PESTPAC_COMPANY_KEY")):
        from office_hero.adapters.back_office.pestpac import PestPacAdapter  # noqa: PLC0415

        register_adapter("pestpac", PestPacAdapter.from_tenant)
        log.info("back_office.registered", adapter="pestpac")


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
            _register_back_office_adapters()
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
    contract_service: ContractService | None = None,
    vehicle_service: VehicleService | None = None,
    vehicle_crew_service: VehicleCrewService | None = None,
    schedule_suggestion_service: ScheduleSuggestionService | None = None,
    job_dispatch_service: JobDispatchService | None = None,
    vehicle_location_service: VehicleLocationService | None = None,
    dispatch_service: DispatchService | None = None,
    dynamic_dispatch_service: DynamicDispatchService | None = None,
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
    # Sentry error tracking — opt-in via SENTRY_DSN env var (not set = disabled).
    _sentry_dsn = os.environ.get("SENTRY_DSN")
    if _sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            sentry_sdk.init(
                dsn=_sentry_dsn,
                integrations=[StarletteIntegration(), FastApiIntegration()],
                traces_sample_rate=0.1,
                send_default_pii=False,
                environment=os.environ.get("APP_ENV", "production"),
            )
            log.info("sentry.initialized", dsn_set=True)
        except ImportError:
            log.warning("sentry.skipped", reason="sentry-sdk not installed")

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

    # Slice-11 default: in-memory contract repository sharing the job/customer/
    # location repos above so generated jobs land in the same store the /jobs
    # routes read from. The outbox wires the back-office sync seam (slice 24).
    if contract_service is None:
        contract_service = ContractService(
            repo=InMemoryContractRepository(),
            customer_repo=cust_repo,
            location_repo=loc_repo,
            job_repo=_default_job_repo or InMemoryJobRepository(),
            audit=audit,
            template_registry=_template_registry_module,
            outbox=outbox_repo,
        )
    set_contract_service(contract_service)

    # Slice-24: back-office sync service draining the outbox through the
    # tenant's adapter (native by default — see adapters/back_office/registry).
    back_office_sync_service = BackOfficeSyncService(
        outbox=outbox_repo,
        customer_repo=cust_repo,
        job_repo=_default_job_repo or InMemoryJobRepository(),
    )

    # Slice-12 defaults: in-memory vehicle repos
    _default_v_repo: InMemoryVehicleRepository | None = None
    vc_repo: InMemoryVehicleCrewRepository | None = None
    if vehicle_service is None or vehicle_crew_service is None:
        v_audit = InMemoryAuditService()
        _default_v_repo = InMemoryVehicleRepository()
        vc_repo = InMemoryVehicleCrewRepository()
        _default_v_repo._crew_repo = vc_repo  # cross-reference for list_active_for_date

        class _DevTrustUserRepo:
            """Dev default: accept any crew-member id as an active Technician.

            In the in-memory configuration identity comes from auth headers and
            there is no users store to validate against — a None-returning repo
            would make POST /vehicle-crews unusable (every member rejected as
            not_in_tenant). Production wiring injects the SQL-backed user
            repository, which keeps the strict active/role validation.
            """

            async def get_by_id(self, user_id, tenant_id):
                from types import SimpleNamespace

                return SimpleNamespace(
                    id=user_id, tenant_id=tenant_id, role="technician", active=True
                )

        if vehicle_service is None:
            vehicle_service = VehicleService(repo=_default_v_repo, audit=v_audit, crew_repo=vc_repo)
        if vehicle_crew_service is None:
            vehicle_crew_service = VehicleCrewService(
                crew_repo=vc_repo,
                vehicle_repo=_default_v_repo,
                user_repo=_DevTrustUserRepo(),
                audit=v_audit,
            )

    set_vehicle_service(vehicle_service)
    set_vehicle_crew_service(vehicle_crew_service)

    # Slice-15: shared location repo (created before slice-13 so routing can use live positions).
    # NOTE: the default VehicleLocationService uses _default_v_repo (set when vehicle_service
    # is None). If you inject vehicle_service without also injecting vehicle_location_service,
    # the two services will have disconnected vehicle repos and location writes will 404.
    # Always inject vehicle_location_service when injecting vehicle_service in tests.
    _default_location_repo: InMemoryVehicleLocationRepository | None = None
    if vehicle_location_service is None:
        _default_location_repo = InMemoryVehicleLocationRepository()
        vehicle_location_service = VehicleLocationService(
            location_repo=_default_location_repo,
            vehicle_repo=_default_v_repo or InMemoryVehicleRepository(),
        )

    # Slice-13: schedule suggestion service (uses live GPS positions when available)
    if schedule_suggestion_service is None:
        from office_hero.adapters.routing.stub import StubRoutingAdapter

        schedule_suggestion_service = ScheduleSuggestionService(
            job_repo=_default_job_repo or InMemoryJobRepository(),
            vehicle_repo=_default_v_repo or InMemoryVehicleRepository(),
            routing_adapter=StubRoutingAdapter(),
            vehicle_location_repo=_default_location_repo,
        )
    set_schedule_suggestion_service(schedule_suggestion_service)

    # Slice-14: shared route repositories — both the job dispatch service
    # (suggested-slot booking) and the dispatch service (manual commit /
    # resequence) must write the same Route/RouteStop store or the Routes
    # view would only see half the dispatches.
    _route_repo = None
    _route_stop_repo = None
    if dispatch_service is None:
        _route_repo = InMemoryRouteRepository()
        _route_stop_repo = InMemoryRouteStopRepository()
        set_route_repository(_route_repo)
        set_route_stop_repository(_route_stop_repo)
    else:
        # Injected dispatch service: reuse the route repos the caller
        # registered (tests call set_route_repository before create_app) so
        # a default JobDispatchService writes the same store.
        try:
            _route_repo = get_route_repository()
            _route_stop_repo = get_route_stop_repository()
        except RuntimeError:
            pass

    # Slice-14: job dispatch service
    if job_dispatch_service is None:
        job_dispatch_service = JobDispatchService(
            job_repo=_default_job_repo or InMemoryJobRepository(),
            vehicle_repo=_default_v_repo or InMemoryVehicleRepository(),
            route_repo=_route_repo,
            stop_repo=_route_stop_repo,
            crew_repo=vc_repo or InMemoryVehicleCrewRepository(),
        )
    set_job_dispatch_service(job_dispatch_service)

    # Slice-14 (dispatch route management): dispatch service
    if dispatch_service is None:
        dispatch_service = DispatchService(
            route_repo=_route_repo,
            stop_repo=_route_stop_repo,
            job_repo=_default_job_repo or InMemoryJobRepository(),
            vehicle_repo=_default_v_repo or InMemoryVehicleRepository(),
            vehicle_crew_repo=vc_repo or InMemoryVehicleCrewRepository(),
            schedule_service=schedule_suggestion_service,
            audit=audit,
        )
    set_dispatch_service(dispatch_service)

    # Slice-16: dynamic dispatch (day-of re-routing) — shares the same route/stop/
    # job/vehicle/crew repos and schedule service as the Slice-14 dispatch services.
    # Injectable so tests can wire it onto their shared repos (the default below
    # only matches the other services when create_app builds all of them itself).
    if dynamic_dispatch_service is None:
        dynamic_dispatch_service = DynamicDispatchService(
            route_repo=_route_repo or InMemoryRouteRepository(),
            stop_repo=_route_stop_repo or InMemoryRouteStopRepository(),
            job_repo=_default_job_repo or InMemoryJobRepository(),
            vehicle_repo=_default_v_repo or InMemoryVehicleRepository(),
            vehicle_crew_repo=vc_repo or InMemoryVehicleCrewRepository(),
            schedule_service=schedule_suggestion_service,
            audit=audit,
        )
    set_dynamic_dispatch_service(dynamic_dispatch_service)

    application = FastAPI(
        title="Office Hero",
        description="Back-office management API for office services",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- Middleware (added first = innermost) ---
    # JWT auth: validates Bearer tokens; passes through when no token present.
    application.add_middleware(JWTAuthMiddleware)
    # Test auth (X-Test-* header bypass) is opt-in via OFFICE_HERO_TEST_AUTH=1.
    # NEVER enable in production — it bypasses JWT auth entirely.
    if test_auth_enabled():
        application.add_middleware(TestAuthMiddleware)
        # CORS for local dev/demo: allows the Vite dev server (localhost:3000) to
        # call the backend directly without proxy. Only active with test auth.
        _cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
        application.add_middleware(
            CORSMiddleware,
            allow_origins=_cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(LoggingMiddleware)

    # --- Exception handlers ---
    register_exception_handlers(application)

    # --- slowapi rate limiter state ---
    application.state.limiter = limiter

    # --- Routers ---
    application.include_router(health.router, tags=["health"])
    application.include_router(auth.router, tags=["auth"])

    saga_router = create_saga_router(saga_service=saga_service)
    application.include_router(saga_router, prefix="/sagas", tags=["sagas"])

    admin_router = create_admin_router(
        saga_service=saga_service,
        outbox_repo=outbox_repo,
        sync_service_provider=lambda: back_office_sync_service,
    )
    application.include_router(admin_router, prefix="/admin", tags=["admin"])
    application.include_router(audit_router, prefix="/admin", tags=["admin"])
    application.include_router(rate_limits_router, prefix="/admin", tags=["admin"])
    application.include_router(
        create_integrations_router(), prefix="/admin", tags=["admin", "integrations"]
    )

    customer_router = create_customer_router(
        service_provider=lambda: customer_service,
        location_service_provider=lambda: location_service,
    )
    application.include_router(customer_router, prefix="/customers", tags=["customers"])

    location_router = create_location_router(service_provider=lambda: location_service)
    application.include_router(location_router, tags=["locations"])

    job_router = create_job_router(service_provider=lambda: job_service)
    application.include_router(job_router, prefix="/jobs", tags=["jobs"])

    contract_router = create_contract_router(service_provider=lambda: contract_service)
    application.include_router(contract_router, prefix="/contracts", tags=["contracts"])

    # Tech router must be registered before the vehicles router so that
    # /vehicles/my-crew-today is matched before /{vehicle_id} catches it.
    tech_router = create_tech_router(
        crew_service_provider=lambda: vehicle_crew_service,
    )
    application.include_router(tech_router, tags=["tech"])

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

    vehicle_location_router = create_vehicle_location_router(
        service_provider=lambda: vehicle_location_service,
    )
    application.include_router(vehicle_location_router, tags=["vehicle-location"])

    # repo_provider reads module state so injected dispatch services (whose
    # repos were registered via set_route_repository) resolve correctly.
    routes_router = create_routes_router(
        service_provider=lambda: dispatch_service,
        repo_provider=get_route_repository,
    )
    application.include_router(routes_router, tags=["routes"])

    return application


# Module-level instance used by TestClient and uvicorn. Uses in-memory mocks
# so the import succeeds without a live database; production callers should
# build their own app via ``create_app(saga_service=..., outbox_repo=...)``.
app = create_app()
