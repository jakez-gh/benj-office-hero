"""Unit tests for :class:`ContractService` (TDD-first, no DB required).

Status transitions, cross-tenant defence, immutable-field protection, and the
due-job generation pass (catch-up, idempotency, end_date auto-end) are all
exercised here using in-memory repositories.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from office_hero.core.exceptions import (
    ContractNotFoundError,
    CustomerNotFoundError,
    InvalidContractTransitionError,
    LocationNotFoundError,
)
from office_hero.repositories.contract_repository import InMemoryContractRepository
from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.location_repository import InMemoryLocationRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.contract_service import ContractService
from office_hero.services.custom_field_templates import registry as template_registry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_A = uuid4()
TENANT_B = uuid4()
USER_A = uuid4()


@pytest.fixture()
def audit() -> InMemoryAuditService:
    return InMemoryAuditService()


@pytest.fixture()
def cust_repo() -> InMemoryCustomerRepository:
    return InMemoryCustomerRepository()


@pytest.fixture()
def loc_repo() -> InMemoryLocationRepository:
    return InMemoryLocationRepository()


@pytest.fixture()
def job_repo() -> InMemoryJobRepository:
    return InMemoryJobRepository()


@pytest.fixture()
def contract_repo() -> InMemoryContractRepository:
    return InMemoryContractRepository()


@pytest.fixture()
def svc(contract_repo, cust_repo, loc_repo, job_repo, audit) -> ContractService:
    return ContractService(
        repo=contract_repo,
        customer_repo=cust_repo,
        location_repo=loc_repo,
        job_repo=job_repo,
        audit=audit,
        template_registry=template_registry,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_customer_and_location(cust_repo, loc_repo, *, tenant_id=TENANT_A):
    """Create a customer + one location; return (customer, location)."""
    cust = await cust_repo.create(tenant_id, name="Acme Pest Control")
    loc = await loc_repo.create(
        tenant_id,
        customer_id=cust.id,
        street="1 Main St",
        city="Austin",
        state="TX",
        postal_code="78701",
    )
    return cust, loc


async def _create_contract(svc, cust, loc, **overrides):
    """Create a quarterly contract starting 2026-06-01 unless overridden."""
    kwargs = {
        "customer_id": cust.id,
        "location_id": loc.id,
        "title": "Quarterly pest plan",
        "frequency": "quarterly",
        "start_date": date(2026, 6, 1),
        "industry": "pest_control",
    }
    kwargs.update(overrides)
    return await svc.create(TENANT_A, USER_A, **kwargs)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_contract_sets_next_due_to_start_date_and_audits(
    svc, cust_repo, loc_repo, audit
):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc)

    assert contract.status == "active"
    assert contract.next_due == date(2026, 6, 1)
    assert contract.industry == "pest_control"
    assert any(e.event_type == "contract.created" for e in audit.events)


async def test_create_contract_unknown_customer_raises_not_found(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    with pytest.raises(CustomerNotFoundError):
        await _create_contract(svc, cust, loc, customer_id=uuid4())


async def test_create_contract_cross_tenant_customer_raises_not_found(svc, cust_repo, loc_repo):
    """A customer that exists in tenant B is invisible to tenant A (defence-in-depth)."""
    cust_b, loc_b = await _seed_customer_and_location(cust_repo, loc_repo, tenant_id=TENANT_B)
    with pytest.raises(CustomerNotFoundError):
        await _create_contract(svc, cust_b, loc_b)


async def test_create_contract_location_of_other_customer_raises(svc, cust_repo, loc_repo):
    cust, _ = await _seed_customer_and_location(cust_repo, loc_repo)
    other_cust, other_loc = await _seed_customer_and_location(cust_repo, loc_repo)
    with pytest.raises(LocationNotFoundError):
        await _create_contract(svc, cust, other_loc)


async def test_create_contract_unknown_frequency_raises_value_error(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    with pytest.raises(ValueError):
        await _create_contract(svc, cust, loc, frequency="fortnightly")


async def test_create_contract_end_before_start_raises_value_error(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    with pytest.raises(ValueError):
        await _create_contract(svc, cust, loc, end_date=date(2026, 5, 1))


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_contract_immutable_fields_rejected(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc)
    for field in ("status", "tenant_id", "customer_id", "industry", "frequency"):
        with pytest.raises(ValueError):
            await svc.update(TENANT_A, USER_A, contract.id, {field: "x"})


async def test_update_contract_next_due_is_patchable(svc, cust_repo, loc_repo):
    """Skipping a visit by pushing next_due forward is a legitimate workflow."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc)
    updated = await svc.update(TENANT_A, USER_A, contract.id, {"next_due": date(2026, 9, 1)})
    assert updated.next_due == date(2026, 9, 1)


async def test_update_contract_null_on_non_nullable_field_rejected(svc, cust_repo, loc_repo):
    """Explicit nulls on NOT NULL columns must 422, not 500 / poison state."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc)
    for field in ("next_due", "title", "priority", "estimated_duration_min", "custom_fields"):
        with pytest.raises(ValueError):
            await svc.update(TENANT_A, USER_A, contract.id, {field: None})


async def test_update_contract_can_clear_end_date(svc, cust_repo, loc_repo):
    """end_date is legitimately clearable — the agreement becomes open-ended."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc, end_date=date(2027, 6, 1))
    updated = await svc.update(TENANT_A, USER_A, contract.id, {"end_date": None})
    assert updated.end_date is None


async def test_update_contract_cross_tenant_raises_not_found(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc)
    with pytest.raises(ContractNotFoundError):
        await svc.update(TENANT_B, USER_A, contract.id, {"title": "stolen"})


# ---------------------------------------------------------------------------
# pause / resume / end transitions
# ---------------------------------------------------------------------------


async def test_pause_then_resume_round_trip(svc, cust_repo, loc_repo, audit):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc, start_date=date(2099, 1, 1))

    paused = await svc.pause(TENANT_A, USER_A, contract.id)
    assert paused.status == "paused"
    assert paused.paused_at is not None

    resumed = await svc.resume(TENANT_A, USER_A, contract.id)
    assert resumed.status == "active"
    event_types = [e.event_type for e in audit.events]
    assert "contract.paused" in event_types
    assert "contract.resumed" in event_types


async def test_resume_preserves_visit_overdue_before_pause(svc, cust_repo, loc_repo, contract_repo):
    """A visit already overdue BEFORE the pause is still pending after resume.

    Only visits whose due date fell during the pause window are skipped; a
    pre-pause backlog belongs to the generation run, not the pause.
    """
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(
        svc, cust, loc, frequency="monthly", start_date=date(2020, 1, 15)
    )
    await svc.pause(TENANT_A, USER_A, contract.id)
    await svc.resume(TENANT_A, USER_A, contract.id)

    refreshed = await contract_repo.get_by_id(contract.id, TENANT_A)
    assert refreshed.next_due == date(2020, 1, 15)  # untouched — still due


async def test_resume_rolls_forward_visits_due_during_pause(
    svc, cust_repo, loc_repo, contract_repo
):
    """Visits whose due date fell while paused are skipped on resume.

    Simulates a long pause by back-dating paused_at and next_due so the due
    date lands inside the pause window. The day-of-month anchor (start_date
    day 15) must be preserved by the roll-forward.
    """
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(
        svc, cust, loc, frequency="monthly", start_date=date(2026, 1, 15)
    )
    await svc.pause(TENANT_A, USER_A, contract.id)
    # Back-date the pause to Jan 10 and pin next_due inside the pause window.
    await contract_repo.update_fields(
        contract.id,
        TENANT_A,
        paused_at=datetime(2026, 1, 10, tzinfo=UTC),
        next_due=date(2026, 1, 15),
    )

    await svc.resume(TENANT_A, USER_A, contract.id)

    refreshed = await contract_repo.get_by_id(contract.id, TENANT_A)
    assert refreshed.next_due >= datetime.now(UTC).date()
    assert refreshed.next_due.day == 15  # cadence anchor preserved


async def test_pause_paused_contract_raises_invalid_transition(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc)
    await svc.pause(TENANT_A, USER_A, contract.id)
    with pytest.raises(InvalidContractTransitionError):
        await svc.pause(TENANT_A, USER_A, contract.id)


async def test_end_is_terminal(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc)
    ended = await svc.end(TENANT_A, USER_A, contract.id, reason="customer moved")
    assert ended.status == "ended"
    assert ended.end_reason == "customer moved"
    with pytest.raises(InvalidContractTransitionError):
        await svc.resume(TENANT_A, USER_A, contract.id)
    with pytest.raises(InvalidContractTransitionError):
        await svc.pause(TENANT_A, USER_A, contract.id)


# ---------------------------------------------------------------------------
# generate_due_jobs
# ---------------------------------------------------------------------------


async def test_generate_creates_job_and_advances_next_due(
    svc, cust_repo, loc_repo, job_repo, contract_repo, audit
):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(svc, cust, loc, custom_fields={"pest_type": "termite"})

    jobs = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 6, 1))

    assert len(jobs) == 1
    job = jobs[0]
    assert job.contract_id == contract.id
    assert job.customer_id == cust.id
    assert job.location_id == loc.id
    assert job.status == "pending"
    assert job.custom_fields == {"pest_type": "termite"}
    assert "Quarterly pest plan" in job.title
    assert job.requested_at.date() == date(2026, 6, 1)

    refreshed = await contract_repo.get_by_id(contract.id, TENANT_A)
    assert refreshed.next_due == date(2026, 9, 1)
    assert any(e.event_type == "contract.jobs_generated" for e in audit.events)


async def test_generate_is_idempotent_for_same_as_of(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    await _create_contract(svc, cust, loc)

    first = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 6, 1))
    second = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 6, 1))

    assert len(first) == 1
    assert second == []


async def test_generate_catches_up_multiple_periods(svc, cust_repo, loc_repo, contract_repo):
    """A monthly contract 3 months behind produces 3 jobs in one run."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(
        svc, cust, loc, frequency="monthly", start_date=date(2026, 3, 10)
    )

    jobs = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 5, 15))

    assert [j.requested_at.date() for j in jobs] == [
        date(2026, 3, 10),
        date(2026, 4, 10),
        date(2026, 5, 10),
    ]
    refreshed = await contract_repo.get_by_id(contract.id, TENANT_A)
    assert refreshed.next_due == date(2026, 6, 10)


async def test_generate_skips_paused_and_ended_contracts(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    paused = await _create_contract(svc, cust, loc, title="Paused plan")
    ended = await _create_contract(svc, cust, loc, title="Ended plan")
    await svc.pause(TENANT_A, USER_A, paused.id)
    await svc.end(TENANT_A, USER_A, ended.id)

    jobs = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 6, 1))
    assert jobs == []


async def test_generate_respects_end_date_and_auto_ends(svc, cust_repo, loc_repo, contract_repo):
    """Generation stops at end_date and the contract transitions to ended."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(
        svc,
        cust,
        loc,
        frequency="monthly",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 15),
    )

    jobs = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 6, 1))

    # Jan 1 and Feb 1 are within the agreement; Mar 1 is past end_date.
    assert [j.requested_at.date() for j in jobs] == [date(2026, 1, 1), date(2026, 2, 1)]
    refreshed = await contract_repo.get_by_id(contract.id, TENANT_A)
    assert refreshed.status == "ended"
    assert refreshed.end_reason == "end_date reached"


async def test_generate_scopes_to_tenant(svc, cust_repo, loc_repo):
    """Tenant B's generation run must not touch tenant A's contracts."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    await _create_contract(svc, cust, loc)

    jobs = await svc.generate_due_jobs(TENANT_B, USER_A, as_of=date(2026, 6, 1))
    assert jobs == []


async def test_generate_not_due_yet_creates_nothing(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    await _create_contract(svc, cust, loc, start_date=date(2026, 7, 1))

    jobs = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 6, 30))
    assert jobs == []


async def test_generate_far_future_as_of_rejected(svc, cust_repo, loc_repo):
    """as_of beyond today+31d would mass-create jobs and irreversibly end contracts."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    await _create_contract(svc, cust, loc)

    far_future = datetime.now(UTC).date() + timedelta(days=60)
    with pytest.raises(ValueError):
        await svc.generate_due_jobs(TENANT_A, USER_A, as_of=far_future)


async def test_generate_preserves_month_end_anchor(svc, cust_repo, loc_repo, contract_repo):
    """A day-31 anchor must recover after short months, not drift to the 28th."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    contract = await _create_contract(
        svc, cust, loc, frequency="monthly", start_date=date(2026, 1, 31)
    )

    jobs = await svc.generate_due_jobs(TENANT_A, USER_A, as_of=date(2026, 6, 1))

    assert [j.requested_at.date() for j in jobs] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
    ]
    refreshed = await contract_repo.get_by_id(contract.id, TENANT_A)
    assert refreshed.next_due == date(2026, 6, 30)
