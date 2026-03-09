"""Idempotency service: ensures saga steps can be safely retried."""

from __future__ import annotations

from typing import Any
from uuid import UUID


class IdempotencyService:
    """Manages idempotency keys and caches step results.

    When a saga step is retried with the same idempotency key, this service
    returns the cached result instead of re-executing the step. This ensures
    that retries don't cause duplicate operations on external systems.
    """

    def __init__(self):
        # Map: idem_key -> (step_name, result)
        self.cache: dict[UUID, tuple[str, Any]] = {}

    def store_result(self, idem_key: UUID, step_name: str, result: Any) -> None:
        """Cache the result of a step execution.

        Args:
            idem_key: The idempotency key for this step
            step_name: The name of the step (for logging/validation)
            result: The result returned by the step
        """
        self.cache[idem_key] = (step_name, result)

    def get_cached_result(self, idem_key: UUID, step_name: str) -> Any | None:
        """Retrieve a cached result if available.

        Returns the cached result if:
        1. The idem_key exists in the cache
        2. The step_name matches (validation against misuse)

        Otherwise returns None.
        """
        if idem_key not in self.cache:
            return None

        cached_step_name, cached_result = self.cache[idem_key]
        if cached_step_name != step_name:
            raise ValueError(
                f"Idempotency key {idem_key} was used for step "
                f"'{cached_step_name}' but is now being used for "
                f"'{step_name}'. Idempotency keys must not be reused "
                f"across different steps."
            )
        return cached_result

    def clear_cache(self) -> None:
        """Clear all cached results (useful for testing)."""
        self.cache.clear()

    def clear_key(self, idem_key: UUID) -> None:
        """Clear a specific cached result."""
        self.cache.pop(idem_key, None)
