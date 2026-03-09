"""Saga pattern exception types."""

from __future__ import annotations

from uuid import UUID


class SagaError(Exception):
    """Base exception for saga orchestration failures.

    Always includes request_id and step_name for debugging and audit trails.
    """

    def __init__(
        self,
        message: str,
        saga_id: UUID,
        step_name: str,
        cause: Exception | None = None,
    ):
        self.message = message
        self.saga_id = saga_id
        self.step_name = step_name
        self.cause = cause
        super().__init__(f"Saga {saga_id} step '{step_name}' failed: {message}")


class SagaCompensationFailedError(SagaError):
    """Raised when a compensating transaction fails.

    This is a critical error: the saga could not clean up after a failure.
    The saga is moved to the dead-letter queue for operator intervention.
    """

    pass


class BackOfficeAdapterError(Exception):
    """Raised when a back-office adapter operation fails.

    Includes the adapter name and the underlying error for diagnostic purposes.
    """

    def __init__(self, adapter_name: str, operation: str, cause: Exception):
        self.adapter_name = adapter_name
        self.operation = operation
        self.cause = cause
        super().__init__(f"Adapter '{adapter_name}' operation '{operation}' failed: {cause}")
