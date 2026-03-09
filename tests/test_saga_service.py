"""Tests for SagaService orchestration and compensation logic."""

from uuid import uuid4

import pytest

from office_hero.repositories.mocks import MockSagaRepository
from office_hero.sagas.core import (
    SagaDefinition,
    SagaStatus,
    SagaStep,
)
from office_hero.sagas.exceptions import SagaCompensationFailedError
from office_hero.services.saga_service import SagaService


@pytest.mark.asyncio
async def test_saga_service_success():
    """SagaService executes all steps successfully."""
    repo = MockSagaRepository()
    svc = SagaService(saga_repo=repo)

    execution_record = []

    async def step1_exec(context):
        execution_record.append("step1_exec")
        context["step1_result"] = "done"
        return {"step1_result": "done"}

    async def step1_comp(context):
        execution_record.append("step1_comp")

    async def step2_exec(context):
        execution_record.append("step2_exec")
        # Verify step1 result is available
        assert context.get("step1_result") == "done"
        return {"step2_result": "done"}

    async def step2_comp(context):
        execution_record.append("step2_comp")

    step1 = SagaStep(
        name="step1",
        execute=step1_exec,
        compensate=step1_comp,
    )
    step2 = SagaStep(
        name="step2",
        execute=step2_exec,
        compensate=step2_comp,
    )

    definition = SagaDefinition(
        saga_type="test_success",
        steps=[step1, step2],
        context={"tenant_id": uuid4()},
    )

    result = await svc.execute_saga(definition)

    assert result.status == SagaStatus.DONE
    assert result.context["step1_result"] == "done"
    assert result.context["step2_result"] == "done"
    # Compensation should NOT have run
    assert "step1_comp" not in execution_record
    assert "step2_comp" not in execution_record
    # Only forward execution
    assert execution_record == ["step1_exec", "step2_exec"]


@pytest.mark.asyncio
async def test_saga_service_failure_and_compensation():
    """SagaService compensates steps when a later step fails."""
    repo = MockSagaRepository()
    svc = SagaService(saga_repo=repo)

    execution_record = []

    async def step1_exec(context):
        execution_record.append("step1_exec")
        return {"step1_result": "done"}

    async def step1_comp(context):
        execution_record.append("step1_comp")

    async def step2_exec(context):
        execution_record.append("step2_exec")
        # This step fails!
        raise RuntimeError("step2 failed")

    async def step2_comp(context):
        execution_record.append("step2_comp")

    step1 = SagaStep(
        name="step1",
        execute=step1_exec,
        compensate=step1_comp,
    )
    step2 = SagaStep(
        name="step2",
        execute=step2_exec,
        compensate=step2_comp,
    )

    definition = SagaDefinition(
        saga_type="test_failure",
        steps=[step1, step2],
        context={"tenant_id": uuid4()},
    )

    result = await svc.execute_saga(definition)

    assert result.status == SagaStatus.DONE  # DONE, not FAILED (after compensation)
    # Executed step1, failed on step2, then compensated step1
    assert execution_record == ["step1_exec", "step2_exec", "step1_comp"]


@pytest.mark.asyncio
async def test_saga_service_compensation_failure():
    """SagaService fails if compensation itself fails."""
    repo = MockSagaRepository()
    svc = SagaService(saga_repo=repo)

    async def step1_exec(context):
        return {}

    async def step1_comp(context):
        # Compensation fails!
        raise RuntimeError("compensation failed")

    async def step2_exec(context):
        raise RuntimeError("step2 failed")

    async def step2_comp(context):
        pass

    step1 = SagaStep(
        name="step1",
        execute=step1_exec,
        compensate=step1_comp,
    )
    step2 = SagaStep(
        name="step2",
        execute=step2_exec,
        compensate=step2_comp,
    )

    definition = SagaDefinition(
        saga_type="test_comp_failure",
        steps=[step1, step2],
        context={"tenant_id": uuid4()},
    )

    with pytest.raises(SagaCompensationFailedError):
        await svc.execute_saga(definition)


@pytest.mark.asyncio
async def test_saga_service_get_status():
    """SagaService can retrieve saga status by ID."""
    repo = MockSagaRepository()
    svc = SagaService(saga_repo=repo)

    async def noop_exec(context):
        return {}

    async def noop_comp(context):
        pass

    step = SagaStep(
        name="test",
        execute=noop_exec,
        compensate=noop_comp,
    )

    definition = SagaDefinition(
        saga_type="test_status",
        steps=[step],
        context={"tenant_id": uuid4()},
    )

    executed = await svc.execute_saga(definition)
    retrieved = await svc.get_saga_status(executed.saga_id)

    assert retrieved is not None
    assert retrieved.saga_id == executed.saga_id
    assert retrieved.status == SagaStatus.DONE
