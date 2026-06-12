"""Contract status lifecycle — enum, transition matrix, and helpers (Slice 11).

Mirrors :mod:`office_hero.core.job_status`.  All transitions must go through
:meth:`~office_hero.services.contract_service.ContractService._transition`;
direct assignment ``contract.status = ...`` outside the service is a bug.
"""

from __future__ import annotations

from enum import StrEnum


class ContractStatus(StrEnum):
    """Lifecycle states for a recurring service Contract."""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


ALLOWED_TRANSITIONS: frozenset[tuple[ContractStatus, ContractStatus]] = frozenset(
    {
        (ContractStatus.ACTIVE, ContractStatus.PAUSED),
        (ContractStatus.PAUSED, ContractStatus.ACTIVE),
        (ContractStatus.ACTIVE, ContractStatus.ENDED),
        (ContractStatus.PAUSED, ContractStatus.ENDED),
    }
)


def can_transition(current: ContractStatus, target: ContractStatus) -> bool:
    """Return True when ``current -> target`` is in the allow-list."""
    return (current, target) in ALLOWED_TRANSITIONS


def is_terminal(status: ContractStatus) -> bool:
    """Return True for terminal states (no transitions out)."""
    return status is ContractStatus.ENDED
