"""ORSGeocodingAdapter — OpenRouteService geocoder (stubbed, future slice).

Wiring exists so the factory ``settings.geocoding_adapter = "ors"`` switch can
be exercised by tests, but the actual HTTP integration lands when an
OpenRouteService API key is provisioned (tracked in a follow-up slice).
"""

from __future__ import annotations

from office_hero.adapters.geocoding.protocol import (
    AddressInput,
    Coordinates,
    GeocodingAdapter,
)


class ORSGeocodingAdapter(GeocodingAdapter):
    """Skeleton ORS adapter — raises until the integration is provisioned."""

    SOURCE: str = "ors"

    def __init__(self, *args, **kwargs) -> None:
        """Accept any kwargs the factory may pass; integration is deferred."""
        # Intentional no-op: this class exists as a placeholder so the
        # ``GEOCODING_ADAPTER`` config switch is testable today.
        return None

    async def geocode(self, address: AddressInput) -> Coordinates | None:
        """Not implemented — ORS integration is deferred to a follow-up slice."""
        raise NotImplementedError(
            "ORSGeocodingAdapter is enabled in a follow-up slice when the ORS "
            "API key is provisioned."
        )
