"""Unit tests for contract recurrence date arithmetic (Slice 11)."""

from __future__ import annotations

from datetime import date

import pytest

from office_hero.core.contract_frequency import ContractFrequency, advance_date
from office_hero.core.contract_status import ContractStatus, can_transition, is_terminal


class TestAdvanceDate:
    """advance_date is the single source of recurrence truth — test the matrix."""

    @pytest.mark.parametrize(
        ("start", "frequency", "expected"),
        [
            (date(2026, 6, 1), ContractFrequency.WEEKLY, date(2026, 6, 8)),
            (date(2026, 6, 1), ContractFrequency.BIWEEKLY, date(2026, 6, 15)),
            (date(2026, 6, 1), ContractFrequency.MONTHLY, date(2026, 7, 1)),
            (date(2026, 6, 1), ContractFrequency.QUARTERLY, date(2026, 9, 1)),
            (date(2026, 6, 1), ContractFrequency.SEMIANNUAL, date(2026, 12, 1)),
            (date(2026, 6, 1), ContractFrequency.ANNUAL, date(2027, 6, 1)),
        ],
    )
    def test_simple_cadences(self, start, frequency, expected):
        assert advance_date(start, frequency) == expected

    def test_weekly_crosses_month_boundary(self):
        assert advance_date(date(2026, 6, 29), ContractFrequency.WEEKLY) == date(2026, 7, 6)

    def test_monthly_clamps_to_short_month(self):
        """Jan 31 + monthly -> Feb 28 in a non-leap year."""
        assert advance_date(date(2026, 1, 31), ContractFrequency.MONTHLY) == date(2026, 2, 28)

    def test_monthly_clamps_to_leap_february(self):
        """Jan 31 + monthly -> Feb 29 in a leap year."""
        assert advance_date(date(2028, 1, 31), ContractFrequency.MONTHLY) == date(2028, 2, 29)

    def test_quarterly_crosses_year_boundary(self):
        assert advance_date(date(2026, 11, 15), ContractFrequency.QUARTERLY) == date(2027, 2, 15)

    def test_annual_from_leap_day_clamps(self):
        """Feb 29 + annual -> Feb 28 the following (non-leap) year."""
        assert advance_date(date(2028, 2, 29), ContractFrequency.ANNUAL) == date(2029, 2, 28)

    def test_semiannual_from_month_end(self):
        """Aug 31 + semiannual -> Feb 28 (clamped)."""
        assert advance_date(date(2026, 8, 31), ContractFrequency.SEMIANNUAL) == date(2027, 2, 28)


class TestContractStatusMachine:
    """The 3x3 transition grid — only the documented edges are allowed."""

    ALLOWED = {
        (ContractStatus.ACTIVE, ContractStatus.PAUSED),
        (ContractStatus.PAUSED, ContractStatus.ACTIVE),
        (ContractStatus.ACTIVE, ContractStatus.ENDED),
        (ContractStatus.PAUSED, ContractStatus.ENDED),
    }

    @pytest.mark.parametrize("current", list(ContractStatus))
    @pytest.mark.parametrize("target", list(ContractStatus))
    def test_transition_matrix(self, current, target):
        assert can_transition(current, target) is ((current, target) in self.ALLOWED)

    def test_is_terminal(self):
        assert is_terminal(ContractStatus.ENDED)
        assert not is_terminal(ContractStatus.ACTIVE)
        assert not is_terminal(ContractStatus.PAUSED)
