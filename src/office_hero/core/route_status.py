"""Route and RouteStop status enums and transition matrices (Slice 14)."""

from __future__ import annotations

from enum import StrEnum


class RouteStatus(StrEnum):
    DRAFT = "draft"
    COMMITTED = "committed"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class RouteStopStatus(StrEnum):
    PENDING = "pending"
    ARRIVED = "arrived"
    COMPLETE = "complete"
    SKIPPED = "skipped"


# Allowed route transitions: from → {allowed_to}
_ROUTE_TRANSITIONS: dict[RouteStatus, frozenset[RouteStatus]] = {
    RouteStatus.DRAFT: frozenset({RouteStatus.COMMITTED, RouteStatus.CANCELLED}),
    RouteStatus.COMMITTED: frozenset({RouteStatus.IN_PROGRESS, RouteStatus.CANCELLED}),
    RouteStatus.IN_PROGRESS: frozenset({RouteStatus.COMPLETE, RouteStatus.CANCELLED}),
    RouteStatus.COMPLETE: frozenset(),
    RouteStatus.CANCELLED: frozenset(),
}

# Allowed stop transitions: from → {allowed_to}
_STOP_TRANSITIONS: dict[RouteStopStatus, frozenset[RouteStopStatus]] = {
    RouteStopStatus.PENDING: frozenset(
        {RouteStopStatus.ARRIVED, RouteStopStatus.COMPLETE, RouteStopStatus.SKIPPED}
    ),
    RouteStopStatus.ARRIVED: frozenset({RouteStopStatus.COMPLETE, RouteStopStatus.SKIPPED}),
    RouteStopStatus.COMPLETE: frozenset(),
    RouteStopStatus.SKIPPED: frozenset(),
}


def can_route_transition(from_status: RouteStatus, to_status: RouteStatus) -> bool:
    return to_status in _ROUTE_TRANSITIONS.get(from_status, frozenset())


def can_stop_transition(from_status: RouteStopStatus, to_status: RouteStopStatus) -> bool:
    return to_status in _STOP_TRANSITIONS.get(from_status, frozenset())


def is_terminal_route(status: RouteStatus) -> bool:
    return status in (RouteStatus.COMPLETE, RouteStatus.CANCELLED)


def is_terminal_stop(status: RouteStopStatus) -> bool:
    return status in (RouteStopStatus.COMPLETE, RouteStopStatus.SKIPPED)
