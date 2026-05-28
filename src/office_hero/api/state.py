"""Global app state for engine, auth service, and slice 9/12 services/adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine

from office_hero.services.auth_service import AuthService

if TYPE_CHECKING:
    from office_hero.adapters.geocoding.protocol import GeocodingAdapter
    from office_hero.services.customer_service import CustomerService
    from office_hero.services.location_service import LocationService
    from office_hero.services.vehicle_crew_service import VehicleCrewService
    from office_hero.services.vehicle_service import VehicleService

# Global variables for app lifecycle
_engine: AsyncEngine | None = None
_auth_service: AuthService | None = None
_customer_service: CustomerService | None = None
_location_service: LocationService | None = None
_geocoding_adapter: GeocodingAdapter | None = None
_vehicle_service: VehicleService | None = None
_vehicle_crew_service: VehicleCrewService | None = None


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
            "CustomerService not initialized. " "Ensure app has been created with create_app()."
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
            "LocationService not initialized. " "Ensure app has been created with create_app()."
        )
    return _location_service


def set_geocoding_adapter(adapter: GeocodingAdapter) -> None:
    """Register the active geocoding adapter."""
    global _geocoding_adapter
    _geocoding_adapter = adapter


def get_geocoding_adapter() -> GeocodingAdapter:
    """Retrieve the active geocoding adapter."""
    if _geocoding_adapter is None:
        raise RuntimeError(
            "GeocodingAdapter not initialized. " "Ensure app has been created with create_app()."
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
