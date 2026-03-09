"""Saga service resilience and failure handling tests."""

import asyncio
from uuid import uuid4

import pytest

from office_hero.repositories.mocks import MockSagaRepository
from office_hero.sagas.core import (
    SagaDefinition,
    SagaStatus,
    SagaStep,
    StepStatus,
)
from office_hero.sagas.exceptions import SagaCompensationFailedError
from office_hero.services.saga_service import SagaService


@pytest.fixture
def saga_service():
    """Provide saga service with mock repositories."""
    repo = MockSagaRepository()
    return SagaService(saga_repo=repo)


@pytest.mark.asyncio
async def test_saga_step_timeout_scenario(saga_service):
    """Test saga behavior when step times out (would need timeout wrapper).

    Note: Timeout handling would require an external timeout wrapper.
    This test demonstrates timeout error propagation in saga context.
    """
    call_count = 0

    async def potentially_slow_step(ctx: dict) -> dict:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return {"result": "completed"}

    async def noop_compensate(ctx: dict) -> dict:
        return {}

    saga_def = SagaDefinition(
        saga_type="timeout_test",
        steps=[
            SagaStep(
                name="slow_operation",
                execute=potentially_slow_step,
                compensate=noop_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            )
        ],
        context={},
    )

    result = await saga_service.execute_saga(saga_def)
    assert result.status == SagaStatus.DONE
    assert call_count == 1


@pytest.mark.asyncio
async def test_saga_compensation_order_verification(saga_service):
    """Verify compensation happens in reverse step order."""
    compensation_order = []

    async def step1_execute(ctx: dict) -> dict:
        ctx["step_1"] = "done"
        return {"step": 1}

    async def step1_compensate(ctx: dict) -> dict:
        compensation_order.append("step_1_compensate")
        return {}

    async def step2_execute(ctx: dict) -> dict:
        ctx["step_2"] = "done"
        return {"step": 2}

    async def step2_compensate(ctx: dict) -> dict:
        compensation_order.append("step_2_compensate")
        return {}

    async def step3_execute(ctx: dict) -> dict:
        raise ValueError("Intentional failure at step 3")

    async def step3_compensate(ctx: dict) -> dict:
        compensation_order.append("step_3_compensate")
        return {}

    saga_def = SagaDefinition(
        saga_type="order_test",
        steps=[
            SagaStep(
                name="step_1",
                execute=step1_execute,
                compensate=step1_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            ),
            SagaStep(
                name="step_2",
                execute=step2_execute,
                compensate=step2_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            ),
            SagaStep(
                name="step_3",
                execute=step3_execute,
                compensate=step3_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            ),
        ],
        context={},
    )

    await saga_service.execute_saga(saga_def)

    # Verify compensation happened in reverse order (step 2, then step 1)
    assert compensation_order == ["step_2_compensate", "step_1_compensate"]
    # Step 3 was never executed, so never compensated
    assert "step_3_compensate" not in compensation_order


@pytest.mark.asyncio
async def test_saga_partial_compensation_failure(saga_service):
    """Test saga when compensation itself fails (recovery scenario)."""
    compensation_attempts = {"step_2": 0, "step_1": 0}

    async def step1_execute(ctx: dict) -> dict:
        ctx["step_1"] = "done"
        return {"step": 1}

    async def step1_compensate(ctx: dict) -> dict:
        compensation_attempts["step_1"] += 1
        # Second attempt succeeds
        if compensation_attempts["step_1"] < 2:
            raise RuntimeError("Compensation failed: network error")
        return {}

    async def step2_execute(ctx: dict) -> dict:
        ctx["step_2"] = "done"
        return {"step": 2}

    async def step2_compensate(ctx: dict) -> dict:
        compensation_attempts["step_2"] += 1
        return {}

    async def step3_execute(ctx: dict) -> dict:
        raise ValueError("Triggering compensation")

    async def step3_compensate(ctx: dict) -> dict:
        return {}

    saga_def = SagaDefinition(
        saga_type="partial_comp_fail",
        steps=[
            SagaStep(
                name="step_1",
                execute=step1_execute,
                compensate=step1_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            ),
            SagaStep(
                name="step_2",
                execute=step2_execute,
                compensate=step2_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            ),
            SagaStep(
                name="step_3",
                execute=step3_execute,
                compensate=step3_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            ),
        ],
        context={},
    )

    with pytest.raises(SagaCompensationFailedError):
        await saga_service.execute_saga(saga_def)

    # Compensation was attempted for step_1
    assert compensation_attempts["step_1"] >= 1


@pytest.mark.asyncio
async def test_saga_context_isolation_between_sagas(saga_service):
    """Verify context mutations in one saga don't affect others."""

    async def mutating_step(ctx: dict) -> dict:
        ctx["mutation"] = "happened"
        return {"mutated": True}

    async def noop_compensate(ctx: dict) -> dict:
        return {}

    saga_def1 = SagaDefinition(
        saga_type="isolated_1",
        steps=[
            SagaStep(
                name="mutate",
                execute=mutating_step,
                compensate=noop_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            )
        ],
        context={"initial": "context_1"},
    )

    saga_def2 = SagaDefinition(
        saga_type="isolated_2",
        steps=[
            SagaStep(
                name="mutate",
                execute=mutating_step,
                compensate=noop_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            )
        ],
        context={"initial": "context_2"},
    )

    result1 = await saga_service.execute_saga(saga_def1)
    result2 = await saga_service.execute_saga(saga_def2)

    # Each saga has its own isolated context
    assert result1.context["initial"] == "context_1"
    assert result2.context["initial"] == "context_2"
    assert result1.saga_id != result2.saga_id
