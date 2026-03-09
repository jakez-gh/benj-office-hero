"""Core saga pattern infrastructure: status enums, step definitions, and context."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class SagaStatus(StrEnum):
    """State of a saga orchestration."""

    RUNNING = "running"
    DONE = "done"
    COMPENSATING = "compensating"
    FAILED = "failed"


class StepStatus(StrEnum):
    """State of a single saga step."""

    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    COMPENSATED = "compensated"


@dataclass
class SagaStep:
    """A single step in a saga: execute async action + compensating action.

    Saga steps are ordered; execution proceeds sequentially. If step N fails,
    steps 1..N-1 are compensated in reverse order.
    """

    name: str
    """Step identifier; appears in logs and saga_log context."""

    execute: Callable[..., Awaitable[Any]]
    """Async callable that performs the forward action.

    Signature: async def execute(context: dict[str, Any]) -> dict[str, Any]
    Receives the saga context (with prior step results) and returns output
    that is merged into the context for downstream steps.
    """

    compensate: Callable[..., Awaitable[None]]
    """Async callable that undoes the step if a later step fails.

    Signature: async def compensate(context: dict[str, Any]) -> None
    Receives the full saga context and should reverse the effect of execute().
    """

    idempotency_key: UUID | None = None
    """UUID used for deduplication on external API calls.

    If the step fails and is retried, the same key is sent to the backend,
    allowing it to detect and suppress duplicate operations.
    Multiple steps may share the same key if they are part of one logical operation.
    """

    status: StepStatus = field(default=StepStatus.PENDING)
    """Current execution state of the step."""


@dataclass
class SagaDefinition:
    """Definition of a multi-step saga: type, sequence of steps, and execution context."""

    saga_type: str
    """Saga identifier; used in saga_log.saga_type to group related executions.

    Examples: "sync_customer_to_servicetitan", "create_job_with_dispatch".
    """

    steps: list[SagaStep]
    """Ordered list of steps to execute.

    Executed sequentially in order. On failure, steps are compensated in reverse.
    """

    context: dict[str, Any] = field(default_factory=dict)
    """Context dict passed and modified through saga execution.

    Initially populated by the caller (e.g., tenant_id, external_id).
    Each step output is merged into context for downstream steps.
    On compensation, steps receive the full context including intermediate results.
    """


@dataclass
class SagaContext:
    """Runtime state of a saga execution."""

    saga_id: UUID
    """Database row ID in saga_log table."""

    tenant_id: UUID
    """Tenant that owns this saga."""

    saga_type: str
    """Saga identifier for routing to handler."""

    current_step: int = 0
    """Index into SagaDefinition.steps (0-indexed)."""

    status: SagaStatus = SagaStatus.RUNNING
    """Overall saga state."""

    context: dict[str, Any] = field(default_factory=dict)
    """Accumulated context: input params + step outputs."""

    last_error: str | None = None
    """Error message if status is FAILED."""

    created_at: str | None = None
    """ISO 8601 timestamp of saga start."""

    updated_at: str | None = None
    """ISO 8601 timestamp of last state change."""
