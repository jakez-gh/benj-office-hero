"""BackOfficeSyncService — drains the transactional outbox through the
tenant's back-office adapter (ADR 056, Slice 24).

Trigger is manual/cron (``POST /admin/outbox/process``) in v1, same posture
as contract job generation; a background poller can replace the trigger
later without changing this service.

Delivery is at-least-once: an event is marked ``processing`` before dispatch
and ``done`` after, so a crash in between re-delivers on the next run.
Adapters must therefore be idempotent (each payload carries ``idem_key``).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from office_hero.adapters.back_office import Customer as BoCustomer
from office_hero.adapters.back_office import Job as BoJob
from office_hero.adapters.back_office.registry import (
    UnknownBackOfficeAdapterError,
    get_adapter_factory,
)
from office_hero.core.logging import get_logger
from office_hero.repositories.protocols import OutboxRepository

log = get_logger(__name__)

# After this many failed attempts an event dead-letters; operators retry via
# POST /admin/dead-letters/{id}/retry once the underlying cause is fixed.
MAX_ATTEMPTS = 5


class BackOfficeSyncService:
    """Processes pending outbox events for one tenant at a time."""

    def __init__(
        self,
        outbox: OutboxRepository,
        customer_repo: Any,
        job_repo: Any,
        tenant_repo: Any = None,
    ) -> None:
        """``tenant_repo`` resolves the tenant's adapter name; None = native."""
        self._outbox = outbox
        self._customer_repo = customer_repo
        self._job_repo = job_repo
        self._tenant_repo = tenant_repo

    async def _adapter_name(self, tenant_id: UUID) -> str:
        if self._tenant_repo is None:
            return "native"
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        return getattr(tenant, "back_office_adapter", None) or "native"

    async def _dispatch(self, adapter, event: dict[str, Any]) -> None:
        """Route one event to the adapter method for its type."""
        event_type: str = event["event_type"]
        payload: dict[str, Any] = event["payload"]

        if event_type in ("backoffice.customer.created", "backoffice.customer.updated"):
            customer = BoCustomer(
                id=UUID(str(payload["customer_id"])), name=payload.get("name", "")
            )
            if event_type.endswith("created"):
                await adapter.create_customer(customer)
            else:
                await adapter.update_customer(customer)
        elif event_type in (
            "backoffice.job.created",
            "backoffice.contract.created",
        ):
            # Contracts sync as their generated work definition; external
            # systems that model contracts natively can override in their
            # adapter (slices 25-27). Native acknowledges either way.
            job = BoJob(
                id=UUID(str(payload.get("job_id") or payload["contract_id"])),
                customer_id=UUID(str(payload["customer_id"])),
            )
            await adapter.create_job(job)
        else:
            raise ValueError(f"No back-office handler for event type {event_type!r}")

    async def process_pending(self, tenant_id: UUID, *, limit: int = 50) -> dict[str, int]:
        """Process up to ``limit`` pending events; returns counters.

        Failures increment ``attempt_count``; once it reaches
        :data:`MAX_ATTEMPTS` the event dead-letters with the error recorded.
        Until then the event returns to pending for the next run (the run
        cadence provides natural backoff).
        """
        adapter_name = await self._adapter_name(tenant_id)
        factory = get_adapter_factory(adapter_name)  # raises on unknown name
        adapter = factory(tenant_id, self._customer_repo, self._job_repo)

        processed = failed = dead = 0
        for event in await self._outbox.get_pending(tenant_id, limit=limit):
            event_id: UUID = event["id"]
            await self._outbox.mark_processing(event_id)
            try:
                await self._dispatch(adapter, event)
            except UnknownBackOfficeAdapterError:
                raise
            except Exception as exc:  # noqa: BLE001 — every failure mode dead-letters the same way
                attempts = await self._outbox.increment_attempt_count(event_id)
                if attempts >= MAX_ATTEMPTS:
                    await self._outbox.mark_dead_letter(event_id, reason=str(exc))
                    dead += 1
                    log.warning(
                        "backoffice.event_dead_lettered",
                        event_id=str(event_id),
                        event_type=event["event_type"],
                        attempts=attempts,
                        error=str(exc),
                    )
                else:
                    await self._outbox.mark_pending(event_id)  # requeue, attempts kept
                    failed += 1
                    log.warning(
                        "backoffice.event_failed",
                        event_id=str(event_id),
                        event_type=event["event_type"],
                        attempts=attempts,
                        error=str(exc),
                    )
            else:
                await self._outbox.mark_done(event_id)
                processed += 1

        if processed or failed or dead:
            log.info(
                "backoffice.outbox_processed",
                tenant_id=str(tenant_id),
                adapter=adapter_name,
                processed=processed,
                failed=failed,
                dead=dead,
            )
        return {"processed": processed, "failed": failed, "dead_lettered": dead}
