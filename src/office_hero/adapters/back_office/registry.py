"""Back-office adapter registry (Slice 24).

Maps ``tenants.back_office_adapter`` values to adapter factories.  A factory
takes ``(tenant_id, customer_repo, job_repo)`` and returns a
:class:`~office_hero.adapters.back_office.BackOfficeAdapter`.

Slices 25-27 add their adapters here::

    register_adapter("servicetitan", ServiceTitanAdapter.from_tenant)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from office_hero.adapters.back_office import BackOfficeAdapter, NativeAdapter

AdapterFactory = Callable[[UUID, Any, Any], BackOfficeAdapter]


class UnknownBackOfficeAdapterError(Exception):
    """Raised when a tenant references an adapter name nobody registered."""

    def __init__(self, name: str):
        self.name = name
        self.message = f"Unknown back-office adapter: {name!r}"
        super().__init__(self.message)


_REGISTRY: dict[str, AdapterFactory] = {}


def register_adapter(name: str, factory: AdapterFactory) -> None:
    """Register an adapter factory under ``name`` (idempotent overwrite)."""
    _REGISTRY[name] = factory


def get_adapter_factory(name: str) -> AdapterFactory:
    """Resolve a factory or raise :class:`UnknownBackOfficeAdapterError`."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise UnknownBackOfficeAdapterError(name) from exc


def known_adapters() -> list[str]:
    """Names usable in ``tenants.back_office_adapter`` (CHECK constraint mirrors this)."""
    return sorted(_REGISTRY)


register_adapter(
    "native",
    lambda tenant_id, customer_repo, job_repo: NativeAdapter(tenant_id, customer_repo, job_repo),
)
