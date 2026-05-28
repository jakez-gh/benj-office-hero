"""Stub routing adapter — deterministic ~15-minute estimate for any pair.

Used in unit/API tests and as the default when ``ORS_API_KEY`` is not set.
"""

from __future__ import annotations

from office_hero.adapters.routing.protocol import RouteResult, RoutingAdapter

_STUB_DURATION_S = 900
_STUB_DISTANCE_M = 12_000


class StubRoutingAdapter(RoutingAdapter):
    """Returns a fixed ~15-minute / 12 km estimate for any coordinate pair."""

    async def get_route(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
    ) -> RouteResult:
        return RouteResult(
            duration_seconds=_STUB_DURATION_S,
            distance_meters=_STUB_DISTANCE_M,
        )
