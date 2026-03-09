"""Rate limit manager with 1-second TTL cache and DB-backed limits."""

from __future__ import annotations

import time
from typing import Any

from office_hero.core.logging import get_logger

log = get_logger(__name__)

# Hard-coded fallback defaults (requests per minute)
_DEFAULTS: dict[str, int] = {
    "auth": 10,
    "write": 60,
    "read": 300,
    "global": 1000,
}

_CACHE_TTL_SECONDS = 1.0


class RateLimitManager:
    """Manages rate limit lookups with per-instance TTL cache backed by the DB.

    Cache is instance-level (self._cache) to ensure test isolation and allow
    independent instances in multi-process deployments.
    """

    def __init__(self, session_factory=None):
        """Initialize with optional async session factory.

        If session_factory is None, only default fallback limits are used.
        """
        self._session_factory = session_factory
        # Instance-level TTL cache: {scope_key: (value, expiry_timestamp)}
        self._cache: dict[str, tuple[Any, float]] = {}

    def _cache_get(self, key: str) -> Any | None:
        """Return cached value if still within TTL, else None."""
        entry = self._cache.get(key)
        if entry and time.monotonic() < entry[1]:
            return entry[0]
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        """Store value in instance TTL cache."""
        self._cache[key] = (value, time.monotonic() + _CACHE_TTL_SECONDS)

    def get_limit(self, scope: str) -> int:
        """Return requests-per-minute limit for the given scope.

        Checks cache first, then falls back to hard-coded defaults.
        DB-backed lookup is wired in Slice 5+ when session_factory is provided.
        """
        scope = scope.lower()
        cache_key = f"limit:{scope}"

        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Fallback to defaults (DB lookup would go here with session_factory)
        limit = _DEFAULTS.get(scope, _DEFAULTS["global"])
        self._cache_set(cache_key, limit)
        log.debug("rate_limit.fetched", scope=scope, limit=limit, source="default")
        return limit

    def is_banned(self, scope_key: str) -> bool:
        """Check if a scope key is in the ban list.

        Returns False by default; DB lookup wired in Slice 5+ with session_factory.
        """
        cache_key = f"ban:{scope_key}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Default: not banned (DB-backed check wired later)
        self._cache_set(cache_key, False)
        return False

    def slowapi_limit_string(self, scope: str) -> str:
        """Return slowapi-formatted limit string (e.g. '10/minute')."""
        limit = self.get_limit(scope)
        return f"{limit}/minute"
