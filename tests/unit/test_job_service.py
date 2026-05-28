"""Unit tests for :class:`JobService` (TDD-first, no DB required).

Status transitions, cross-tenant defence, custom-field validation, and
immutable-field protection are all exercised here using in-memory repositories.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from office_hero.core.exceptions import (
    CustomerNotFoundError,
    InvalidJobTransitionError,
    LocationNotFoundError,
)
from office_hero.core.job_status import JobStatus
from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.location_repository import InMemoryLocationRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.custom_field_templates import registry as template_registry
from office_hero.services.job_service import JobService

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
def svc(job_repo, cust_repo, loc_repo, audit) -> JobService:
    return JobService(
        repo=job_repo,
        customer_repo=cust_repo,
        location_repo=loc_repo,
        audit=audit,
        template_registry=template_registry,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_customer_and_location(cust_repo, loc_repo, *, tenant_id=TENANT_A):
    """Create a customer + one location; return (customer, location)."""
    cust = await cust_repo.create(tenant_id, name="Acme Plumbing")
    loc = await loc_repo.create(
        tenant_id,
        customer_id=cust.id,
        street="1 Main St",
        city="Austin",
        state="TX",
        postal_code="78701",
    )
    return cust, loc


async def _create_job(svc, cust_id, loc_id, *, tenant_id=TENANT_A, title="Pipe Fix"):
    return await svc.create(
        tenant_id,
        USER_A,
        customer_id=cust_id,
        location_id=loc_id,
        title=title,
        industry="generic",
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_job_with_valid_custom_fields_emits_audit(svc, audit, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await svc.create(
        TENANT_A,
        USER_A,
        customer_id=cust.id,
        location_id=loc.id,
        title="Boiler Service",
        custom_fields={"note": "annual maintenance"},
        industry="generic",
    )
    assert job.status == "pending"
    assert job.custom_fields == {"note": "annual maintenance"}
    assert len(audit.events) == 1
    assert audit.events[0].event_type == "job.created"
    assert audit.events[0].details["title"] == "Boiler Service"


@pytest.mark.asyncio
async def test_create_job_unknown_customer_raises_not_found(svc):
    with pytest.raises(CustomerNotFoundError):
        await svc.create(
            TENANT_A,
            USER_A,
            customer_id=uuid4(),
            location_id=uuid4(),
            title="X",
        )


@pytest.mark.asyncio
async def test_create_job_location_belongs_to_other_customer_raises(svc, cust_repo, loc_repo):
    cust_a, loc_a = await _seed_customer_and_location(cust_repo, loc_repo)
    cust_b = await cust_repo.create(TENANT_A, name="Beta Co")

    with pytest.raises(LocationNotFoundError):
        await svc.create(
            TENANT_A,
            USER_A,
            customer_id=cust_b.id,
            location_id=loc_a.id,  # belongs to cust_a, not cust_b
            title="Bad Location",
        )


@pytest.mark.asyncio
async def test_create_job_other_tenant_customer_raises_not_found(svc, cust_repo, loc_repo):
    """Customer in tenant B must not be visible to tenant A (cross-tenant)."""
    cust_b, loc_b = await _seed_customer_and_location(cust_repo, loc_repo, tenant_id=TENANT_B)
    with pytest.raises(CustomerNotFoundError):
        await svc.create(
            TENANT_A,  # caller is tenant A
            USER_A,
            customer_id=cust_b.id,  # belongs to tenant B
            location_id=loc_b.id,
            title="Cross-tenant job",
        )


@pytest.mark.asyncio
async def test_create_job_invalid_custom_fields_raises_422_via_template(
    svc, cust_repo, loc_repo, monkeypatch
):
    """When the template raises CustomFieldValidationError the service surfaces it."""
    from office_hero.core.exceptions import CustomFieldValidationError
    from office_hero.services.custom_field_templates import registry as reg

    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)

    def bad_template_get(industry):
        class _Bad:
            industry = "generic"

            def validate(self, cf):
                raise CustomFieldValidationError(
                    field_name="fixture_type",
                    errors=["must be one of: toilet, sink"],
                )

        return _Bad()

    monkeypatch.setattr(reg, "get_template", bad_template_get)
    with pytest.raises(CustomFieldValidationError):
        await svc.create(
            TENANT_A,
            USER_A,
            customer_id=cust.id,
            location_id=loc.id,
            title="Bad Fields",
            custom_fields={"fixture_type": "dishwasher"},
        )


# ---------------------------------------------------------------------------
# schedule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_job_from_pending_succeeds(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)

    scheduled_for = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    job = await svc.schedule(TENANT_A, USER_A, job.id, scheduled_for)
    assert job.status == JobStatus.SCHEDULED
    assert job.scheduled_for == scheduled_for


@pytest.mark.asyncio
async def test_schedule_job_from_in_progress_raises_invalid_transition(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    job = await svc.schedule(TENANT_A, USER_A, job.id, datetime(2026, 6, 1, tzinfo=UTC))
    job = await svc.start(TENANT_A, USER_A, job.id)
    assert job.status == JobStatus.IN_PROGRESS

    with pytest.raises(InvalidJobTransitionError):
        await svc.schedule(TENANT_A, USER_A, job.id, datetime(2026, 6, 2, tzinfo=UTC))


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_job_from_scheduled_succeeds_and_sets_started_at(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    job = await svc.schedule(TENANT_A, USER_A, job.id, datetime(2026, 6, 1, tzinfo=UTC))

    before = datetime.now(UTC)
    job = await svc.start(TENANT_A, USER_A, job.id)
    after = datetime.now(UTC)

    assert job.status == JobStatus.IN_PROGRESS
    assert job.started_at is not None
    assert before <= job.started_at.replace(tzinfo=UTC) <= after


# ---------------------------------------------------------------------------
# complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_job_from_in_progress_sets_completed_at_and_audits(
    svc, audit, cust_repo, loc_repo
):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    job = await svc.schedule(TENANT_A, USER_A, job.id, datetime(2026, 6, 1, tzinfo=UTC))
    job = await svc.start(TENANT_A, USER_A, job.id)

    before = datetime.now(UTC)
    job = await svc.complete(TENANT_A, USER_A, job.id, completion_notes="All done.")
    after = datetime.now(UTC)

    assert job.status == JobStatus.COMPLETE
    assert job.completed_at is not None
    assert before <= job.completed_at.replace(tzinfo=UTC) <= after

    completed_event = next(e for e in audit.events if e.event_type == "job.completed")
    assert completed_event.details["completion_notes"] == "All done."


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setup_fn",
    [
        None,  # pending
        "schedule",
        "start",
    ],
)
async def test_cancel_job_from_any_non_terminal_status_succeeds(
    svc, cust_repo, loc_repo, audit, setup_fn
):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)

    if setup_fn == "schedule" or setup_fn == "start":
        job = await svc.schedule(TENANT_A, USER_A, job.id, datetime(2026, 6, 1, tzinfo=UTC))
    if setup_fn == "start":
        job = await svc.start(TENANT_A, USER_A, job.id)

    job = await svc.cancel(TENANT_A, USER_A, job.id, reason="Customer request")
    assert job.status == JobStatus.CANCELLED
    assert job.cancel_reason == "Customer request"
    assert job.cancelled_at is not None


@pytest.mark.asyncio
async def test_cancel_job_requires_reason_min_3_chars(svc, cust_repo, loc_repo):
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    with pytest.raises(ValueError, match="at least 3"):
        await svc.cancel(TENANT_A, USER_A, job.id, reason="x")


@pytest.mark.asyncio
async def test_cancel_job_from_complete_raises_invalid_transition(svc, cust_repo, loc_repo):
    """A completed Job cannot be cancelled — terminal state."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    job = await svc.schedule(TENANT_A, USER_A, job.id, datetime(2026, 6, 1, tzinfo=UTC))
    job = await svc.start(TENANT_A, USER_A, job.id)
    job = await svc.complete(TENANT_A, USER_A, job.id)

    with pytest.raises(InvalidJobTransitionError) as exc_info:
        await svc.cancel(TENANT_A, USER_A, job.id, reason="changed my mind")
    assert exc_info.value.from_status == JobStatus.COMPLETE
    assert exc_info.value.to_status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_job_from_cancelled_raises_invalid_transition(svc, cust_repo, loc_repo):
    """A cancelled Job cannot be cancelled again — terminal state."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    job = await svc.cancel(TENANT_A, USER_A, job.id, reason="First cancel")

    with pytest.raises(InvalidJobTransitionError) as exc_info:
        await svc.cancel(TENANT_A, USER_A, job.id, reason="Second cancel")
    assert exc_info.value.from_status == JobStatus.CANCELLED


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_job_status_field_via_patch_is_rejected(svc, cust_repo, loc_repo):
    """Patching status directly must raise ValueError."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    with pytest.raises(ValueError, match="status"):
        await svc.update(TENANT_A, USER_A, job.id, {"status": "scheduled"})


@pytest.mark.asyncio
async def test_update_job_industry_field_via_patch_is_rejected(svc, cust_repo, loc_repo):
    """Patching industry directly must raise ValueError."""
    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    with pytest.raises(ValueError, match="industry"):
        await svc.update(TENANT_A, USER_A, job.id, {"industry": "hvac"})


@pytest.mark.asyncio
async def test_update_job_custom_fields_revalidates_against_template(
    svc, cust_repo, loc_repo, monkeypatch
):
    """Updating custom_fields calls the template validate() gate."""
    from office_hero.services.custom_field_templates import registry as reg

    validate_calls: list[dict] = []
    original_get = reg.get_template

    def tracking_get(industry):
        t = original_get(industry)
        orig_validate = t.validate

        def tracked_validate(cf):
            validate_calls.append(cf)
            return orig_validate(cf)

        t.validate = tracked_validate
        return t

    monkeypatch.setattr(reg, "get_template", tracking_get)

    cust, loc = await _seed_customer_and_location(cust_repo, loc_repo)
    job = await _create_job(svc, cust.id, loc.id)
    await svc.update(TENANT_A, USER_A, job.id, {"custom_fields": {"updated": True}})
    # validate was called at least once (create) + once for update
    assert len(validate_calls) >= 2
