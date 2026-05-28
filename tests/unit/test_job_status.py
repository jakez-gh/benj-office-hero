"""Unit tests for the job status machine (pure, no DB required)."""

from __future__ import annotations

import pytest

from office_hero.core.job_status import (
    ALLOWED_TRANSITIONS,
    JobStatus,
    can_transition,
    is_terminal,
)

ALL_STATUSES = list(JobStatus)


@pytest.mark.parametrize("from_s", ALL_STATUSES)
@pytest.mark.parametrize("to_s", ALL_STATUSES)
def test_can_transition_matrix(from_s: JobStatus, to_s: JobStatus) -> None:
    """Only transitions in ALLOWED_TRANSITIONS return True; all others False."""
    expected = (from_s, to_s) in ALLOWED_TRANSITIONS
    assert (
        can_transition(from_s, to_s) is expected
    ), f"can_transition({from_s!r}, {to_s!r}) expected {expected}"


@pytest.mark.parametrize(
    "status, expected",
    [
        (JobStatus.PENDING, False),
        (JobStatus.SCHEDULED, False),
        (JobStatus.IN_PROGRESS, False),
        (JobStatus.COMPLETE, True),
        (JobStatus.CANCELLED, True),
    ],
)
def test_is_terminal(status: JobStatus, expected: bool) -> None:
    """complete and cancelled are terminal; others are not."""
    assert is_terminal(status) is expected
