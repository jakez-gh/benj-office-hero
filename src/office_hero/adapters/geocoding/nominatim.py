"""NominatimGeocodingAdapter — production-default address-to-coordinate resolver.

This adapter calls the public Nominatim service operated by OpenStreetMap
(https://nominatim.org/release-docs/develop/api/Search/). Nominatim's usage
policy mandates:

  * a real, identifying ``User-Agent`` header (anonymous traffic is throttled
    aggressively);
  * a sustained request rate not exceeding **1 request per second** per source
    IP/identity.

The adapter enforces both: the ``User-Agent`` is required at construction
time (via ``Settings.nominatim_user_agent``), and an ``asyncio.Semaphore(1)``
combined with a minimum-interval sleeper ensures we never exceed 1 req/sec.

SSRF defence: the configured ``base_url`` is validated against
``settings.geocoding_allowlist`` at construction time so an operator cannot
point the geocoder at an internal IP through configuration.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from urllib.parse import urlparse

import httpx

from office_hero.adapters.geocoding.protocol import (
    AddressInput,
    Coordinates,
    GeocodingAdapter,
)
from office_hero.core.exceptions import GeocodingError
from office_hero.core.logging import get_logger

log = get_logger(__name__)


class NominatimGeocodingAdapter(GeocodingAdapter):
    """Production Nominatim adapter (1 req/sec, ToS-compliant)."""

    SOURCE: str = "nominatim"
    MIN_INTERVAL_S: float = 1.0  # Nominatim ToS hard ceiling.

    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        timeout: float = 5.0,
        allowlist: Iterable[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        """Construct an adapter and validate the base_url against the allowlist.

        Args:
            base_url: Nominatim root URL, e.g. ``"https://nominatim.openstreetmap.org"``.
            user_agent: Identifying User-Agent header (Nominatim ToS).
            timeout: Per-request timeout in seconds.
            allowlist: Iterable of allowed hostnames. ``None`` disables the check
                (useful only for tests that build the adapter against a mock host).
            client: Optional pre-built ``httpx.AsyncClient`` (mainly for tests).

        Raises:
            GeocodingError: If ``base_url``'s host is not in ``allowlist``.
        """
        if not user_agent:
            raise GeocodingError("Nominatim requires a non-empty user_agent (ToS)")

        if allowlist is not None:
            host = urlparse(base_url).hostname or ""
            if host not in set(allowlist):
                raise GeocodingError(
                    f"Refusing to geocode against host '{host}': not in allowlist"
                )

        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None

        # Rate-limit gate: one request at a time AND >=1s gap between dispatches.
        self._semaphore = asyncio.Semaphore(1)
        self._last_dispatch_monotonic: float = 0.0

    async def geocode(self, address: AddressInput) -> Coordinates | None:
        """Resolve an :class:`AddressInput` via Nominatim ``/search``.

        Returns the first matching candidate's ``lat``/``lng`` or ``None`` when
        Nominatim reports no results.

        Raises:
            GeocodingError: On HTTP error, timeout, or response parse failure.
        """
        query = ", ".join(
            part
            for part in (
                address.street,
                address.city,
                address.state,
                address.postal_code,
                address.country,
            )
            if part
        )

        params = {"format": "jsonv2", "q": query, "limit": "1"}
        headers = {"User-Agent": self._user_agent}
        url = f"{self._base_url}/search"

        async with self._semaphore:
            # Sleep until at least MIN_INTERVAL_S has elapsed since the last call.
            now = time.monotonic()
            wait = self.MIN_INTERVAL_S - (now - self._last_dispatch_monotonic)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_dispatch_monotonic = time.monotonic()

            try:
                client = self._client or httpx.AsyncClient(timeout=self._timeout)
                try:
                    resp = await client.get(url, params=params, headers=headers)
                finally:
                    if self._owns_client and self._client is None:
                        await client.aclose()
            except httpx.TimeoutException as exc:
                log.warning(
                    "geocoding.nominatim.timeout",
                    error=str(exc),
                    query=query,
                )
                raise GeocodingError(f"Nominatim timed out: {exc}") from exc
            except httpx.HTTPError as exc:
                log.warning(
                    "geocoding.nominatim.http_error",
                    error=str(exc),
                    query=query,
                )
                raise GeocodingError(f"Nominatim HTTP error: {exc}") from exc

        if resp.status_code >= 400:
            log.warning(
                "geocoding.nominatim.bad_status",
                status_code=resp.status_code,
                query=query,
            )
            raise GeocodingError(f"Nominatim returned HTTP {resp.status_code}")

        try:
            payload = resp.json()
        except ValueError as exc:
            log.warning("geocoding.nominatim.bad_json", query=query)
            raise GeocodingError(f"Nominatim returned non-JSON body: {exc}") from exc

        if not payload:
            log.info("geocoding.nominatim.miss", query=query)
            return None

        try:
            first = payload[0]
            lat = float(first["lat"])
            lng = float(first["lon"])
            display_name = str(first.get("display_name", query))
        except (KeyError, ValueError, TypeError) as exc:
            raise GeocodingError(f"Nominatim payload missing lat/lon: {exc}") from exc

        return Coordinates(
            lat=lat,
            lng=lng,
            formatted_address=display_name,
            source=self.SOURCE,
        )
