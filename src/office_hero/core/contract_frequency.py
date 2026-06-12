"""Contract recurrence frequencies and calendar-safe date arithmetic (Slice 11).

``advance_date`` is a pure function so the generation logic in
:class:`~office_hero.services.contract_service.ContractService` stays trivially
testable.  Month-based frequencies clamp the day-of-month to the target month's
length (Jan 31 + monthly -> Feb 28/29), matching how FSM products like PestPac
schedule recurring service.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from enum import StrEnum


class ContractFrequency(StrEnum):
    """Supported recurrence cadences for Contracts."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"


_WEEK_DELTAS: dict[ContractFrequency, int] = {
    ContractFrequency.WEEKLY: 7,
    ContractFrequency.BIWEEKLY: 14,
}

_MONTH_DELTAS: dict[ContractFrequency, int] = {
    ContractFrequency.MONTHLY: 1,
    ContractFrequency.QUARTERLY: 3,
    ContractFrequency.SEMIANNUAL: 6,
    ContractFrequency.ANNUAL: 12,
}


def _add_months(d: date, months: int) -> date:
    """Add ``months`` to ``d``, clamping the day to the target month length."""
    total = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def advance_date(d: date, frequency: ContractFrequency) -> date:
    """Return the next occurrence of ``d`` advanced by one ``frequency`` period."""
    if frequency in _WEEK_DELTAS:
        return d + timedelta(days=_WEEK_DELTAS[frequency])
    return _add_months(d, _MONTH_DELTAS[frequency])
