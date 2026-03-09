"""Comprehensive saga lifecycle tests."""

from uuid import uuid4

import pytest

from office_hero.sagas.core import SagaContext, SagaDefinition, SagaStatus, SagaStep, StepStatus
from office_hero.sagas.exceptions import SagaError


@pytest.mark.asyncio
async def test_saga_step_with_none_idempotency_key():
    """SagaStep allows explicit None idempotency_key."""

    async def dummy_execute(ctx: dict) -> dict:
        return {"result": "done"}

    async def dummy_compensate(ctx: dict) -> dict:
        return {"compensated": True}

    step = SagaStep(
        name="test_step",
        execute=dummy_execute,
        compensate=dummy_compensate,
        idempotency_key=None,
        status=StepStatus.PENDING,
    )
    assert step.idempotency_key is None
    assert step.status == StepStatus.PENDING


@pytest.mark.asyncio
async def test_saga_context_is_mutable():
    """SagaContext allows context dict mutations during execution."""
    ctx = SagaContext(
        saga_id=uuid4(),
        tenant_id=uuid4(),
        saga_type="test",
        current_step=0,
        status=SagaStatus.RUNNING,
        context={"initial": "value"},
        last_error=None,
    )
    assert ctx.context["initial"] == "value"

    # Simulate step mutation
    ctx.context["step_1_result"] = "done"
    assert ctx.context["step_1_result"] == "done"


@pytest.mark.asyncio
async def test_saga_definition_empty_steps():
    """SagaDefinition allows empty steps list (edge case)."""
    saga_def = SagaDefinition(
        saga_type="empty_saga",
        steps=[],
        context={},
    )
    assert len(saga_def.steps) == 0


@pytest.mark.asyncio
async def test_saga_error_preserves_chain():
    """SagaError preserves cause chain for debugging."""
    original_error = ValueError("database connection failed")
    saga_error = SagaError(
        message="Failed to connect to database",
        saga_id=uuid4(),
        step_name="connect_db",
        cause=original_error,
    )
    assert saga_error.cause is original_error
    assert "database connection failed" in str(saga_error.cause)


@pytest.mark.asyncio
async def test_saga_status_enum_values():
    """SagaStatus enum has all required states."""
    assert SagaStatus.RUNNING.value == "running"
    assert SagaStatus.DONE.value == "done"
    assert SagaStatus.COMPENSATING.value == "compensating"
    assert SagaStatus.FAILED.value == "failed"
    assert len(SagaStatus) == 4


@pytest.mark.asyncio
async def test_step_status_enum_values():
    """StepStatus enum has all required states."""
    assert StepStatus.PENDING.value == "pending"
    assert StepStatus.DONE.value == "done"
    assert StepStatus.FAILED.value == "failed"
    assert StepStatus.COMPENSATED.value == "compensated"
    assert len(StepStatus) == 4


@pytest.mark.asyncio
async def test_saga_context_with_large_context_dict():
    """SagaContext handles large nested context dictionaries."""
    large_context = {f"key_{i}": {"nested_key": f"value_{i}", "count": i} for i in range(100)}
    ctx = SagaContext(
        saga_id=uuid4(),
        tenant_id=uuid4(),
        saga_type="large_saga",
        current_step=5,
        status=SagaStatus.RUNNING,
        context=large_context,
        last_error=None,
    )
    assert len(ctx.context) == 100
    assert ctx.context["key_50"]["count"] == 50


@pytest.mark.asyncio
async def test_multiple_saga_steps_creation():
    """Multiple SagaStep instances are independent."""

    async def step1_execute(ctx: dict) -> dict:
        return {"step": 1}

    async def step2_execute(ctx: dict) -> dict:
        return {"step": 2}

    async def noop_compensate(ctx: dict) -> dict:
        return {}

    step1 = SagaStep(
        name="step_1",
        execute=step1_execute,
        compensate=noop_compensate,
        idempotency_key=uuid4(),
        status=StepStatus.PENDING,
    )
    step2 = SagaStep(
        name="step_2",
        execute=step2_execute,
        compensate=noop_compensate,
        idempotency_key=uuid4(),
        status=StepStatus.PENDING,
    )

    assert step1.name != step2.name
    assert step1.idempotency_key != step2.idempotency_key
    assert step1.execute != step2.execute
