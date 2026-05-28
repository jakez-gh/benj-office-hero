"""Job status lifecycle — enum, transition matrix, and helpers.

Centralising all transition logic here ensures that every other layer
(service, API, tests) reasons about the same allowed-transition set.
Callers must never bypass ``can_transition()``; any direct
``job.status = ...`` outside :class:`~office_hero.services.job_service.JobService`
must be rejected in code review.
"""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """Valid status values for a :class:`~office_hero.models.job.Job`."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


# Explicit allow-list of (from, to) pairs.  Any pair absent from this set is
# illegal and must raise InvalidJobTransitionError.
ALLOWED_TRANSITIONS: frozenset[tuple[JobStatus, JobStatus]] = frozenset(
    {
        (JobStatus.PENDING, JobStatus.SCHEDULED),
        (JobStatus.PENDING, JobStatus.CANCELLED),
        (JobStatus.SCHEDULED, JobStatus.IN_PROGRESS),
        (JobStatus.SCHEDULED, JobStatus.CANCELLED),
        (JobStatus.IN_PROGRESS, JobStatus.COMPLETE),
        (JobStatus.IN_PROGRESS, JobStatus.CANCELLED),
    }
)

_TERMINAL_STATUSES: frozenset[JobStatus] = frozenset({JobStatus.COMPLETE, JobStatus.CANCELLED})


def can_transition(current: JobStatus, target: JobStatus) -> bool:
    """Return *True* if transitioning from *current* to *target* is allowed."""
    return (current, target) in ALLOWED_TRANSITIONS


def is_terminal(status: JobStatus) -> bool:
    """Return *True* if *status* is a terminal state (no transitions out)."""
    return status in _TERMINAL_STATUSES
