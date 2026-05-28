"""RoutingAdapter protocol + result dataclass (ADR 058).

Decouples travel-time estimation from the service layer so concrete
implementations (ORS, stub) can be swapped without touching business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RouteResult:
    """Estimated route between two coordinates."""

    duration_seconds: int
    distance_meters: int


@runtime_checkable
class RoutingAdapter(Protocol):
    """Estimate travel time between two lat/lng points.

    Implementations must be async. On network or parse failure they should
    raise :class:`~office_hero.core.exceptions.RoutingError`. Returning
    ``None`` is reserved for cases where the routing service responds
    successfully but cannot find a route (e.g. unreachable coordinates).
    """

    async def get_route(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
    ) -> RouteResult | None: ...
