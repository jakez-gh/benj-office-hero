"""Global app state for engine, auth service, and slice 9/10/12 services/adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine

from office_hero.services.auth_service import AuthService

if TYPE_CHECKING:
    from office_hero.adapters.geocoding.protocol import GeocodingAdapter
    from office_hero.repositories.route_repository import RouteRepositoryProtocol
    from office_hero.repositories.route_stop_repository import RouteStopRepositoryProtocol
    from office_hero.repositories.vehicle_location_repository import (
        VehicleLocationRepositoryProtocol,
    )
    from office_hero.services.customer_service import CustomerService
    from office_hero.services.dispatch_service import DispatchService
    from office_hero.services.job_dispatch_service import JobDispatchService
    from office_hero.services.job_service import JobService
    from office_hero.services.location_service import LocationService
    from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService
    from office_hero.services.vehicle_crew_service import VehicleCrewService
    from office_hero.services.vehicle_location_service import VehicleLocationService
    from office_hero.services.vehicle_service import VehicleService

# Global variables for app lifecycle
_engine: AsyncEngine | None = None
_auth_service: AuthService | None = None
_customer_service: CustomerService | None = None
_location_service: LocationService | None = None
_job_service: JobService | None = None
_geocoding_adapter: GeocodingAdapter | None = None
_vehicle_service: VehicleService | None = None
_vehicle_crew_service: VehicleCrewService | None = None
_schedule_suggestion_service: ScheduleSuggestionService | None = None
_job_dispatch_service: JobDispatchService | None = None
_route_repository: RouteRepositoryProtocol | None = None
_route_stop_repository: RouteStopRepositoryProtocol | None = None
_dispatch_service: DispatchService | None = None
_vehicle_location_repository: VehicleLocationRepositoryProtocol | None = None
_vehicle_location_service: VehicleLocationService | None = None


def get_engine() -> AsyncEngine:
    """Get the global engine instance."""
    global _engine
    if _engine is None:
        raise RuntimeError("Engine not initialized. Ensure app has been created with create_app()")
    return _engine


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        raise RuntimeError(
            "AuthService not initialized. Ensure app has been created with create_app()"
        )
    return _auth_service


def set_engine(engine: AsyncEngine) -> None:
    """Set the global engine instance."""
    global _engine
    _engine = engine


def set_auth_service(auth_service: AuthService) -> None:
    """Set the global auth service instance."""
    global _auth_service
    _auth_service = auth_service


# --- Slice 9: Customer / Location services and the geocoding adapter ---


def set_customer_service(service: CustomerService) -> None:
    """Register the customer service used by the route factory."""
    global _customer_service
    _customer_service = service


def get_customer_service() -> CustomerService:
    """Retrieve the registered customer service."""
    if _customer_service is None:
        raise RuntimeError(
            "CustomerService not initialized. Ensure app has been created with create_app()."
        )
    return _customer_service


def set_location_service(service: LocationService) -> None:
    """Register the location service used by the route factory."""
    global _location_service
    _location_service = service


def get_location_service() -> LocationService:
    """Retrieve the registered location service."""
    if _location_service is None:
        raise RuntimeError(
            "LocationService not initialized. Ensure app has been created with create_app()."
        )
    return _location_service


# --- Slice 10: Job service ---


def set_job_service(service: JobService) -> None:
    """Register the job service used by the route factory."""
    global _job_service
    _job_service = service


def get_job_service() -> JobService:
    """Retrieve the registered job service."""
    if _job_service is None:
        raise RuntimeError(
            "JobService not initialized. Ensure app has been created with create_app()."
        )
    return _job_service


def set_geocoding_adapter(adapter: GeocodingAdapter) -> None:
    """Register the active geocoding adapter."""
    global _geocoding_adapter
    _geocoding_adapter = adapter


def get_geocoding_adapter() -> GeocodingAdapter:
    """Retrieve the active geocoding adapter."""
    if _geocoding_adapter is None:
        raise RuntimeError(
            "GeocodingAdapter not initialized. Ensure app has been created with create_app()."
        )
    return _geocoding_adapter


# --- Slice 12: Vehicle / VehicleCrew services ---


def set_vehicle_service(service: VehicleService) -> None:
    """Register the vehicle service used by the route factory."""
    global _vehicle_service
    _vehicle_service = service


def get_vehicle_service() -> VehicleService:
    """Retrieve the registered vehicle service."""
    if _vehicle_service is None:
        raise RuntimeError(
            "VehicleService not initialized. Ensure app has been created with create_app()."
        )
    return _vehicle_service


def set_vehicle_crew_service(service: VehicleCrewService) -> None:
    """Register the vehicle crew service used by the route factory."""
    global _vehicle_crew_service
    _vehicle_crew_service = service


def get_vehicle_crew_service() -> VehicleCrewService:
    """Retrieve the registered vehicle crew service."""
    if _vehicle_crew_service is None:
        raise RuntimeError(
            "VehicleCrewService not initialized. Ensure app has been created with create_app()."
        )
    return _vehicle_crew_service


# --- Slice 13: Schedule suggestion service ---


def set_schedule_suggestion_service(service: ScheduleSuggestionService) -> None:
    """Register the schedule suggestion service."""
    global _schedule_suggestion_service
    _schedule_suggestion_service = service


def get_schedule_suggestion_service() -> ScheduleSuggestionService:
    """Retrieve the registered schedule suggestion service."""
    if _schedule_suggestion_service is None:
        raise RuntimeError(
            "ScheduleSuggestionService not initialized. "
            "Ensure app has been created with create_app()."
        )
    return _schedule_suggestion_service


# --- Slice 14: Job dispatch service ---


def set_job_dispatch_service(service: JobDispatchService) -> None:
    """Register the job dispatch service."""
    global _job_dispatch_service
    _job_dispatch_service = service


def get_job_dispatch_service() -> JobDispatchService:
    """Retrieve the registered job dispatch service."""
    if _job_dispatch_service is None:
        raise RuntimeError(
            "JobDispatchService not initialized. " "Ensure app has been created with create_app()."
        )
    return _job_dispatch_service


# --- Slice 14: Route management service and repositories ---


def set_route_repository(repo: RouteRepositoryProtocol) -> None:
    """Register the route repository."""
    global _route_repository
    _route_repository = repo


def get_route_repository() -> RouteRepositoryProtocol:
    """Retrieve the registered route repository."""
    if _route_repository is None:
        raise RuntimeError(
            "RouteRepository not initialized. Ensure app has been created with create_app()."
        )
    return _route_repository


def set_route_stop_repository(repo: RouteStopRepositoryProtocol) -> None:
    """Register the route stop repository."""
    global _route_stop_repository
    _route_stop_repository = repo


def get_route_stop_repository() -> RouteStopRepositoryProtocol:
    """Retrieve the registered route stop repository."""
    if _route_stop_repository is None:
        raise RuntimeError(
            "RouteStopRepository not initialized. Ensure app has been created with create_app()."
        )
    return _route_stop_repository


def set_dispatch_service(service: DispatchService) -> None:
    """Register the dispatch service."""
    global _dispatch_service
    _dispatch_service = service


def get_dispatch_service() -> DispatchService:
    """Retrieve the registered dispatch service."""
    if _dispatch_service is None:
        raise RuntimeError(
            "DispatchService not initialized. Ensure app has been created with create_app()."
        )
    return _dispatch_service


# --- Slice 15: Vehicle location tracking ---


def set_vehicle_location_repository(repo: VehicleLocationRepositoryProtocol) -> None:
    """Register the vehicle location repository."""
    global _vehicle_location_repository
    _vehicle_location_repository = repo


def get_vehicle_location_repository() -> VehicleLocationRepositoryProtocol:
    """Retrieve the registered vehicle location repository."""
    if _vehicle_location_repository is None:
        raise RuntimeError(
            "VehicleLocationRepository not initialized. Ensure app has been created with create_app()."
        )
    return _vehicle_location_repository


def set_vehicle_location_service(service: VehicleLocationService) -> None:
    """Register the vehicle location service."""
    global _vehicle_location_service
    _vehicle_location_service = service


def get_vehicle_location_service() -> VehicleLocationService:
    """Retrieve the registered vehicle location service."""
    if _vehicle_location_service is None:
        raise RuntimeError(
            "VehicleLocationService not initialized. Ensure app has been created with create_app()."
        )
    return _vehicle_location_service
