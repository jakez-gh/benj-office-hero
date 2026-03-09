"""Tests for core saga infrastructure (enums, step definitions, context)."""

from uuid import uuid4

import pytest

from office_hero.sagas.core import (
    SagaContext,
    SagaDefinition,
    SagaStatus,
    SagaStep,
    StepStatus,
)
from office_hero.sagas.exceptions import (
    BackOfficeAdapterError,
    SagaCompensationFailed,
    SagaError,
)


class TestSagaStatus:
    """Test SagaStatus enum values."""

    def test_saga_status_values(self):
        """All saga statuses are defined and have expected values."""
        assert SagaStatus.RUNNING.value == "running"
        assert SagaStatus.DONE.value == "done"
        assert SagaStatus.COMPENSATING.value == "compensating"
        assert SagaStatus.FAILED.value == "failed"


class TestStepStatus:
    """Test StepStatus enum values."""

    def test_step_status_values(self):
        """All step statuses are defined and have expected values."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.DONE.value == "done"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.COMPENSATED.value == "compensated"


@pytest.mark.asyncio
async def test_saga_step_creation():
    """SagaStep can be created with execute and compensate callables."""

    async def step_execute(context):
        context["result"] = "executed"
        return context

    async def step_compensate(context):
        context.pop("result", None)

    step = SagaStep(
        name="test_step",
        execute=step_execute,
        compensate=step_compensate,
    )

    assert step.name == "test_step"
    assert step.execute is step_execute
    assert step.compensate is step_compensate
    assert step.status == StepStatus.PENDING
    assert step.idempotency_key is None


@pytest.mark.asyncio
async def test_saga_step_with_idempotency_key():
    """SagaStep can include an idempotency key."""

    async def noop_execute(context):
        return context

    async def noop_compensate(context):
        pass

    key = uuid4()
    step = SagaStep(
        name="idempotent_step",
        execute=noop_execute,
        compensate=noop_compensate,
        idempotency_key=key,
    )

    assert step.idempotency_key == key


@pytest.mark.asyncio
async def test_saga_definition():
    """SagaDefinition holds a sequence of steps and context."""

    async def step1_exec(context):
        context["step1"] = True
        return context

    async def step1_comp(context):
        pass

    step1 = SagaStep(name="step1", execute=step1_exec, compensate=step1_comp)

    definition = SagaDefinition(
        saga_type="test_saga",
        steps=[step1],
        context={"tenant_id": str(uuid4())},
    )

    assert definition.saga_type == "test_saga"
    assert len(definition.steps) == 1
    assert definition.steps[0].name == "step1"
    assert "tenant_id" in definition.context


def test_saga_context():
    """SagaContext holds runtime state of a saga."""
    saga_id = uuid4()
    tenant_id = uuid4()

    ctx = SagaContext(
        saga_id=saga_id,
        tenant_id=tenant_id,
        saga_type="test_saga",
        current_step=0,
        status=SagaStatus.RUNNING,
        context={"key": "value"},
    )

    assert ctx.saga_id == saga_id
    assert ctx.tenant_id == tenant_id
    assert ctx.saga_type == "test_saga"
    assert ctx.current_step == 0
    assert ctx.status == SagaStatus.RUNNING
    assert ctx.context == {"key": "value"}
    assert ctx.last_error is None


def test_saga_error_includes_saga_id_and_step():
    """SagaError captures saga_id, step_name, and cause."""
    saga_id = uuid4()
    cause = ValueError("original error")

    err = SagaError(
        message="step failed",
        saga_id=saga_id,
        step_name="test_step",
        cause=cause,
    )

    assert err.saga_id == saga_id
    assert err.step_name == "test_step"
    assert err.cause is cause
    assert "test_step" in str(err)
    assert str(saga_id) in str(err)


def test_saga_compensation_failed():
    """SagaCompensationFailed is a specific SagaError subtype."""
    saga_id = uuid4()

    err = SagaCompensationFailed(
        message="compensation failed",
        saga_id=saga_id,
        step_name="rollback_step",
    )

    assert isinstance(err, SagaError)
    assert err.step_name == "rollback_step"


def test_backoffice_adapter_error():
    """BackOfficeAdapterError wraps adapter operation failures."""
    cause = RuntimeError("api timeout")

    err = BackOfficeAdapterError(
        adapter_name="ServiceTitan",
        operation="create_customer",
        cause=cause,
    )

    assert err.adapter_name == "ServiceTitan"
    assert err.operation == "create_customer"
    assert err.cause is cause
    assert "ServiceTitan" in str(err)
    assert "create_customer" in str(err)
