"""GeocodingAdapter protocol + the input/output dataclasses (ADR 058).

The protocol decouples address-to-coordinates resolution from the rest of the
application so we can swap concrete implementations (Nominatim, ORS, an
in-memory stub for tests) without rippling changes through the service or
repository layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AddressInput:
    """Address fields used to query the geocoder.

    Kept intentionally minimal — only the structured pieces a typical geocoder
    accepts. Free-form address fields (e.g. ``street2``) are deliberately
    excluded because they confuse most geocoders and rarely affect the result.
    """

    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"


@dataclass(frozen=True)
class Coordinates:
    """Resolved coordinates returned by a geocoding adapter."""

    lat: float
    lng: float
    formatted_address: str
    source: str


@runtime_checkable
class GeocodingAdapter(Protocol):
    """Resolve an :class:`AddressInput` to :class:`Coordinates` (or ``None``).

    Implementations must be async; the production default (Nominatim) is
    network-bound. Implementations should raise
    :class:`office_hero.core.exceptions.GeocodingError` for hard failures
    (network, timeout, parse) and return ``None`` when the geocoder responds
    successfully but returns no candidate.
    """

    async def geocode(self, address: AddressInput) -> Coordinates | None:
        """Resolve an address to coordinates, or ``None`` if not resolvable."""
        ...
