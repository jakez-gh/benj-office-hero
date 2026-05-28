"""OpenRouteService routing adapter.

POSTs to ORS v2 directions API and extracts duration/distance from the first
route summary. Requires ``ORS_API_KEY`` environment variable.

Raises :class:`~office_hero.core.exceptions.RoutingError` on any network or
parse failure so callers can fall back gracefully.
"""

from __future__ import annotations

import os

import httpx

from office_hero.adapters.routing.protocol import RouteResult, RoutingAdapter
from office_hero.core.exceptions import RoutingError

_ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
_TIMEOUT_S = 5.0


class ORSRoutingAdapter(RoutingAdapter):
    """Live ORS routing adapter (requires ORS_API_KEY)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ORS_API_KEY", "")

    async def get_route(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
    ) -> RouteResult | None:
        payload = {
            "coordinates": [[from_lng, from_lat], [to_lng, to_lat]],
            "profile": "driving-car",
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.post(_ORS_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise RoutingError(f"ORS request failed: {exc}") from exc

        try:
            summary = data["routes"][0]["summary"]
            return RouteResult(
                duration_seconds=int(summary["duration"]),
                distance_meters=int(summary["distance"]),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RoutingError(f"ORS response parse failed: {exc}") from exc
