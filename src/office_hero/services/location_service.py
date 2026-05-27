"""LocationService — orchestrates location CRUD, geocoding, and audit emission."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from office_hero.adapters.geocoding.protocol import AddressInput, GeocodingAdapter
from office_hero.core.exceptions import (
    CustomerNotFoundError,
    GeocodingError,
    LocationNotFoundError,
)
from office_hero.core.logging import get_logger
from office_hero.models.location import Location
from office_hero.repositories.customer_repository import (
    CustomerRepositoryProtocol,
)
from office_hero.repositories.location_repository import (
    LocationRepositoryProtocol,
)
from office_hero.services.customer_service import AuditPublisher

log = get_logger(__name__)


# Address fields that, when changed, should trigger automatic re-geocoding.
_GEOCODE_RELEVANT_FIELDS = frozenset(
    {"street", "street2", "city", "state", "postal_code", "country"}
)


def _location_summary(loc: Location) -> dict[str, Any]:
    """Audit-safe projection of a Location."""
    return {
        "location_id": str(loc.id),
        "customer_id": str(loc.customer_id),
        "label": loc.label,
        "city": loc.city,
        "state": loc.state,
        "country": loc.country,
        "geocode_status": loc.geocode_status,
        "geocode_source": loc.geocode_source,
    }


class LocationService:
    """Business orchestration for the :class:`Location` aggregate."""

    def __init__(
        self,
        repo: LocationRepositoryProtocol,
        customer_repo: CustomerRepositoryProtocol,
        audit: AuditPublisher,
        geocoder: GeocodingAdapter,
    ):
        """Inject deps (DI)."""
        self.repo = repo
        self.customer_repo = customer_repo
        self.audit = audit
        self.geocoder = geocoder

    async def _verify_customer(self, tenant_id: UUID, customer_id: UUID) -> None:
        """Raise :class:`CustomerNotFoundError` if customer is missing or cross-tenant."""
        cust = await self.customer_repo.get_by_id(customer_id, tenant_id)
        if cust is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found in tenant scope")

    async def create(
        self,
        tenant_id: UUID,
        user_id: UUID,
        customer_id: UUID,
        address_fields: dict[str, Any],
        label: str | None,
        *,
        geocode: bool = True,
    ) -> Location:
        """Insert a location, attempt geocoding, emit ``location.created``."""
        await self._verify_customer(tenant_id, customer_id)

        loc = await self.repo.create(
            tenant_id,
            customer_id,
            street=address_fields["street"],
            street2=address_fields.get("street2"),
            city=address_fields["city"],
            state=address_fields["state"],
            postal_code=address_fields["postal_code"],
            country=address_fields.get("country", "US"),
            label=label,
        )

        if geocode:
            loc = await self._geocode_and_persist(tenant_id, loc)

        await self.audit.log_event(
            event_type="location.created",
            details=_location_summary(loc),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return loc

    async def _geocode_and_persist(self, tenant_id: UUID, loc: Location) -> Location:
        """Try geocoding ``loc``; persist coords on success, mark failed otherwise."""
        address = AddressInput(
            street=loc.street,
            city=loc.city,
            state=loc.state,
            postal_code=loc.postal_code,
            country=loc.country,
        )
        try:
            coords = await self.geocoder.geocode(address)
        except GeocodingError as exc:
            log.warning(
                "location.geocode.error",
                location_id=str(loc.id),
                error=str(exc),
            )
            return await self.repo.mark_geocode_failed(loc.id, tenant_id, str(exc))

        if coords is None:
            log.info("location.geocode.miss", location_id=str(loc.id))
            return await self.repo.mark_geocode_failed(loc.id, tenant_id, "no result")

        return await self.repo.set_coordinates(
            loc.id, tenant_id, coords.lat, coords.lng, coords.source
        )

    async def get(self, tenant_id: UUID, location_id: UUID) -> Location:
        """Fetch or raise :class:`LocationNotFoundError`."""
        loc = await self.repo.get_by_id(location_id, tenant_id)
        if loc is None:
            raise LocationNotFoundError(f"Location {location_id} not found")
        return loc

    async def list_for_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        *,
        archived: bool = False,
    ) -> list[Location]:
        """List a customer's locations."""
        await self._verify_customer(tenant_id, customer_id)
        return await self.repo.list_for_customer(customer_id, tenant_id, archived=archived)

    async def update(
        self,
        tenant_id: UUID,
        user_id: UUID,
        location_id: UUID,
        patch: dict[str, Any],
        *,
        regeocode: bool | Literal["auto"] = "auto",
    ) -> Location:
        """Apply a partial update; optionally re-geocode and emit ``location.updated``."""
        existing = await self.get(tenant_id, location_id)

        changed_fields = {k for k, v in patch.items() if getattr(existing, k, None) != v}

        before: dict[str, Any] = {k: getattr(existing, k, None) for k in changed_fields}
        after: dict[str, Any] = {k: patch[k] for k in changed_fields}

        updated = await self.repo.update(location_id, tenant_id, **patch)

        # Decide whether to re-geocode.
        should_regeo = False
        if regeocode is True:
            should_regeo = True
        elif regeocode == "auto":
            should_regeo = bool(changed_fields & _GEOCODE_RELEVANT_FIELDS)
        elif regeocode is False:
            should_regeo = False

        if should_regeo:
            updated = await self._geocode_and_persist(tenant_id, updated)

        await self.audit.log_event(
            event_type="location.updated",
            details={
                "location_id": str(updated.id),
                "before": before,
                "after": after,
                "regeocoded": should_regeo,
                "geocode_status": updated.geocode_status,
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    async def manual_set_coordinates(
        self,
        tenant_id: UUID,
        user_id: UUID,
        location_id: UUID,
        lat: float,
        lng: float,
    ) -> Location:
        """Operator override of geocoded coordinates."""
        # Existence check (raises if missing/cross-tenant).
        await self.get(tenant_id, location_id)
        updated = await self.repo.update(
            location_id,
            tenant_id,
            lat=lat,
            lng=lng,
            geocode_source="manual",
            geocode_status="manual",
        )
        await self.audit.log_event(
            event_type="location.coordinates_set_manual",
            details={
                "location_id": str(updated.id),
                "lat": float(lat),
                "lng": float(lng),
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    async def regeocode(self, tenant_id: UUID, user_id: UUID, location_id: UUID) -> Location:
        """Force a re-geocode of an existing location."""
        existing = await self.get(tenant_id, location_id)
        updated = await self._geocode_and_persist(tenant_id, existing)
        await self.audit.log_event(
            event_type="location.regeocoded",
            details=_location_summary(updated),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    async def archive(self, tenant_id: UUID, user_id: UUID, location_id: UUID) -> Location:
        """Soft-delete a location; emit ``location.archived``."""
        await self.get(tenant_id, location_id)
        archived = await self.repo.archive(location_id, tenant_id)
        await self.audit.log_event(
            event_type="location.archived",
            details=_location_summary(archived),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return archived
