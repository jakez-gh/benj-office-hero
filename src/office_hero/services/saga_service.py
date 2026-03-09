"""Saga orchestration service: executes multi-step sagas with compensation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from office_hero.repositories.protocols import SagaRepository
from office_hero.sagas.core import SagaContext, SagaDefinition, SagaStatus
from office_hero.sagas.exceptions import (
    SagaCompensationFailedError,
)

logger = logging.getLogger(__name__)


class SagaService:
    """Orchestrates multi-step sagas with compensating transactions.

    Sagas are sequences of local transactions, each with a compensating action.
    If any step fails, prior steps are unwound in reverse order.
    """

    def __init__(self, saga_repo: SagaRepository):
        self.saga_repo = saga_repo

    async def execute_saga(self, saga_definition: SagaDefinition) -> SagaContext:
        """Execute a saga: run each step in sequence with compensation on failure.

        Args:
            saga_definition: The definition (saga_type, steps, initial context)

        Returns:
            The final SagaContext with status (DONE or FAILED) and context.

        On failure, the saga status is COMPENSATING as steps are unwound, then
        either DONE (if compensation succeeds) or FAILED (if compensation fails).
        """
        # Create saga record in database
        saga_ctx = await self.saga_repo.create(
            tenant_id=saga_definition.context.get("tenant_id"),
            saga_type=saga_definition.saga_type,
            context=saga_definition.context,
        )

        try:
            # Execute steps sequentially
            for step_idx, step in enumerate(saga_definition.steps):
                try:
                    logger.info(
                        "Saga %s: executing step %s: %s",
                        saga_ctx.saga_id,
                        step_idx,
                        step.name,
                    )
                    step_result = await step.execute(saga_ctx.context)
                    # Merge step result into saga context
                    if step_result:
                        saga_ctx.context.update(step_result)
                    # Update current_step and status
                    await self.saga_repo.update_current_step(saga_ctx.saga_id, step_idx + 1)
                except Exception as e:
                    logger.error(
                        "Saga %s: step %s failed: %s",
                        saga_ctx.saga_id,
                        step.name,
                        e,
                    )
                    # Compensate: unwind prior steps
                    try:
                        await self.compensate(saga_ctx, saga_definition, step_idx)
                        # Compensation succeeded; saga status already updated to DONE
                        saga_ctx = await self.saga_repo.get_by_id(saga_ctx.saga_id)
                        return saga_ctx
                    except SagaCompensationFailedError:
                        # Compensation failed; saga already marked as FAILED by compensate()
                        # Re-raise to propagate the error to the caller
                        raise

            # All steps succeeded
            saga_ctx = await self.saga_repo.update_status(
                saga_ctx.saga_id,
                SagaStatus.DONE,
                context_update={"completed_at": datetime.now(timezone.utc).isoformat()},
            )
            logger.info(
                "Saga %s (%s) completed successfully",
                saga_ctx.saga_id,
                saga_definition.saga_type,
            )
            return saga_ctx

        except Exception as e:
            logger.exception(
                "Saga %s: unexpected error during execution: %s",
                saga_ctx.saga_id,
                e,
            )
            raise

    async def compensate(
        self,
        saga_ctx: SagaContext,
        saga_definition: SagaDefinition,
        failed_step_idx: int,
    ) -> None:
        """Unwind a failed saga by compensating steps in reverse order.

        Compensates steps [0..failed_step_idx-1] in reverse order.
        If a compensation fails, the saga is left in FAILED status with the error.

        Args:
            saga_ctx: The saga context (will be updated to COMPENSATING status)
            saga_definition: The saga definition (to access steps)
            failed_step_idx: The index of the step that failed; compensate up to this
        """
        # Mark saga as COMPENSATING
        await self.saga_repo.update_status(
            saga_ctx.saga_id,
            SagaStatus.COMPENSATING,
        )

        # Compensate steps in reverse order (only those that executed)
        for step_idx in range(failed_step_idx - 1, -1, -1):
            step = saga_definition.steps[step_idx]
            try:
                logger.info(
                    "Saga %s: compensating step %s: %s",
                    saga_ctx.saga_id,
                    step_idx,
                    step.name,
                )
                await step.compensate(saga_ctx.context)
            except Exception as e:
                logger.error(
                    "Saga %s: compensation of step %s failed: %s",
                    saga_ctx.saga_id,
                    step.name,
                    e,
                )
                # Compensation itself failed: mark saga as FAILED
                await self.saga_repo.update_status(
                    saga_ctx.saga_id,
                    SagaStatus.FAILED,
                    error_msg=(f"Compensation failed at step {step.name}: {e}"),
                )
                raise SagaCompensationFailedError(
                    message=f"Compensation of {step.name} failed",
                    saga_id=saga_ctx.saga_id,
                    step_name=step.name,
                    cause=e,
                ) from e

        # All compensations succeeded
        await self.saga_repo.update_status(
            saga_ctx.saga_id,
            SagaStatus.DONE,
            context_update={"compensated": True},
        )
        logger.info("Saga %s: all compensation steps completed", saga_ctx.saga_id)

    async def get_saga_status(self, saga_id: Any) -> SagaContext | None:
        """Retrieve the current status and context of a saga."""
        return await self.saga_repo.get_by_id(saga_id)
