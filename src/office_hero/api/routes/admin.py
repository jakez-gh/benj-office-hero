"""Admin routes for dead-letter, saga management, audit events, and rate-limit/ban control.

Provides:
    - GET    /admin/audit-events              - paginated audit event listing
    - GET    /admin/rate-limits               - list configured rate limits (Operator only)
    - PATCH  /admin/rate-limits/{name}        - upsert a rate limit (Operator only)
    - GET    /admin/ban-filters               - list ban entries (Operator only)
    - POST   /admin/ban-filters               - add a ban entry (Operator only)
    - DELETE /admin/ban-filters/{id}          - remove a ban entry (Operator only)
    - GET    /admin/dead-letters              - list dead-letter outbox events (Operator only)
    - POST   /admin/dead-letters/{event_id}/retry - reset dead-letter to pending (Operator only)
    - GET    /admin/sagas/{saga_id}/logs      - retrieve saga execution history (Operator only)

The dead-letter and saga routes are exposed via a factory (``create_admin_router``)
so that ``SagaService`` and ``OutboxRepository`` can be injected at app construction
time. Module-level routers (audit, rate-limits/bans) don't need injected dependencies.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel
from sqlalchemy import text

from office_hero.api.deps import require_role
from office_hero.core.roles import Role
from office_hero.repositories.protocols import OutboxRepository
from office_hero.services.audit_service import AuditService
from office_hero.services.saga_service import SagaService

_audit_service = AuditService()

logger = logging.getLogger(__name__)


# Module-level dependency so test fixtures can swap it via
# ``app.dependency_overrides[require_operator] = lambda: "operator"``.
require_operator = require_role([Role.Operator])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class DeadLetterItem(BaseModel):
    """Single dead-letter event in the list response."""

    id: str
    tenant_id: str
    event_type: str
    payload: dict
    status: str
    attempt_count: int
    created_at: str | None = None
    processed_at: str | None = None
    dead_letter_reason: str | None = None


class DeadLetterListResponse(BaseModel):
    """Paginated dead-letter list response."""

    items: list[DeadLetterItem]
    total: int
    limit: int
    offset: int


class DeadLetterRetryResponse(BaseModel):
    """Response after retrying a dead-letter event."""

    id: str
    status: str
    message: str


class OutboxProcessResponse(BaseModel):
    """Counters from one outbox processing run."""

    processed: int
    failed: int
    dead_lettered: int


class SagaLogResponse(BaseModel):
    """Saga execution log response."""

    saga_id: str
    saga_type: str
    status: str
    current_step: int
    context: dict
    last_error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ---------------------------------------------------------------------------
# Audit Events (Slice 4 — Observability)
#
# Audit-events is intentionally kept at module scope because it doesn't need
# saga_service / outbox_repo. ``app.py`` mounts this router under /admin
# alongside the factory-built router.
# ---------------------------------------------------------------------------

audit_router = APIRouter()


@audit_router.get(
    "/audit-events",
    response_model=dict,
    summary="List audit events",
    description="Paginated, filterable audit event listing for admin panel",
)
async def list_audit_events(
    limit: int = Query(50, ge=1, le=1000, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    event_type: str | None = Query(None, description="Filter by event type"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
) -> dict:
    """List audit events with pagination and optional filters.

    Returns paginated audit events from the append-only audit_events table.
    Supports filtering by event_type and tenant_id for efficient admin
    investigation. Falls back to an empty result set when no database engine
    is available (e.g. unit-test environments that use in-memory repositories).
    """
    try:
        from office_hero.api.state import get_engine
        from office_hero.db.session import get_session

        engine = get_engine()
        async with get_session(engine) as session:
            items, total = await _audit_service.list_events(
                session,
                tenant_id=tenant_id,
                event_type=event_type,
                limit=limit,
                offset=offset,
            )
    except RuntimeError:
        items, total = [], 0

    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------------------------------------------------------------------------
# Rate limits & ban filters (Slice 7a)
# ---------------------------------------------------------------------------

_RATE_LIMIT_DEFAULTS: list[dict[str, Any]] = [
    {"name": "auth", "limit": 10, "per_seconds": 60, "scope": "auth"},
    {"name": "write", "limit": 60, "per_seconds": 60, "scope": "write"},
    {"name": "read", "limit": 300, "per_seconds": 60, "scope": "read"},
    {"name": "global", "limit": 1000, "per_seconds": 60, "scope": "global"},
]


class RateLimitItem(BaseModel):
    id: str | None = None
    name: str
    limit: int
    per_seconds: int
    scope: str


class RateLimitUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    limit: int
    per_seconds: int = 60
    scope: str | None = None


class BanFilterItem(BaseModel):
    id: str
    name: str
    scope: str
    created_at: str | None = None


class BanFilterCreate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    scope: str


rate_limits_router = APIRouter()


@rate_limits_router.get(
    "/rate-limits",
    response_model=dict,
    summary="List rate limits",
    dependencies=[Depends(require_operator)],
)
async def list_rate_limits() -> dict:
    """Return DB-configured rate limits, falling back to hard-coded defaults when empty."""
    try:
        from office_hero.api.state import get_engine
        from office_hero.db.session import get_session

        engine = get_engine()
        async with get_session(engine) as session:
            rows = (
                (
                    await session.execute(
                        text(
                            'SELECT CAST(id AS TEXT) AS id, name, "limit", per_seconds, scope '
                            "FROM rate_limits ORDER BY name"
                        )
                    )
                )
                .mappings()
                .all()
            )
    except Exception:
        rows = []

    items = [dict(r) for r in rows] if rows else _RATE_LIMIT_DEFAULTS
    return {"items": items, "total": len(items)}


@rate_limits_router.patch(
    "/rate-limits/{name}",
    response_model=RateLimitItem,
    summary="Upsert a rate limit",
    dependencies=[Depends(require_operator)],
)
async def upsert_rate_limit(
    name: Annotated[str, Path(description="Rate limit scope name")],
    body: RateLimitUpdate,
) -> RateLimitItem:
    """Create or update a rate limit entry by name."""
    scope = body.scope or name
    try:
        from office_hero.api.state import get_engine
        from office_hero.db.session import get_session

        engine = get_engine()
        async with get_session(engine) as session:
            row = (
                (
                    await session.execute(
                        text(
                            'INSERT INTO rate_limits (id, name, "limit", per_seconds, scope) '
                            "VALUES (gen_random_uuid(), :name, :limit, :per_seconds, :scope) "
                            "ON CONFLICT (name) DO UPDATE "
                            'SET "limit" = EXCLUDED."limit", '
                            "    per_seconds = EXCLUDED.per_seconds, "
                            "    updated_at = now() "
                            'RETURNING id::text, name, "limit", per_seconds, scope'
                        ),
                        {
                            "name": name,
                            "limit": body.limit,
                            "per_seconds": body.per_seconds,
                            "scope": scope,
                        },
                    )
                )
                .mappings()
                .one()
            )
            await session.commit()
    except RuntimeError:
        return RateLimitItem(name=name, limit=body.limit, per_seconds=body.per_seconds, scope=scope)

    return RateLimitItem(**dict(row))


@rate_limits_router.get(
    "/ban-filters",
    response_model=dict,
    summary="List ban entries",
    dependencies=[Depends(require_operator)],
)
async def list_ban_filters() -> dict:
    """Return all active ban-list entries."""
    try:
        from office_hero.api.state import get_engine
        from office_hero.db.session import get_session

        engine = get_engine()
        async with get_session(engine) as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT CAST(id AS TEXT) AS id, name, scope, CAST(created_at AS TEXT) AS created_at "
                            "FROM ban_list ORDER BY created_at DESC"
                        )
                    )
                )
                .mappings()
                .all()
            )
    except RuntimeError:
        rows = []

    items = [dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@rate_limits_router.post(
    "/ban-filters",
    response_model=BanFilterItem,
    status_code=201,
    summary="Add a ban entry",
    dependencies=[Depends(require_operator)],
)
async def create_ban_filter(body: BanFilterCreate) -> BanFilterItem:
    """Insert a new entry into the ban list."""
    try:
        from office_hero.api.state import get_engine
        from office_hero.db.session import get_session

        engine = get_engine()
        async with get_session(engine) as session:
            row = (
                (
                    await session.execute(
                        text(
                            'INSERT INTO ban_list (id, name, "limit", per_seconds, scope) '
                            "VALUES (gen_random_uuid(), :name, 0, 1, :scope) "
                            "RETURNING id::text, name, scope, created_at::text"
                        ),
                        {"name": body.name, "scope": body.scope},
                    )
                )
                .mappings()
                .one()
            )
            await session.commit()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc

    return BanFilterItem(**dict(row))


@rate_limits_router.delete(
    "/ban-filters/{ban_id}",
    status_code=204,
    summary="Remove a ban entry",
    dependencies=[Depends(require_operator)],
)
async def delete_ban_filter(
    ban_id: Annotated[str, Path(description="Ban entry UUID")],
) -> None:
    """Delete an entry from the ban list by ID."""
    try:
        from office_hero.api.state import get_engine
        from office_hero.db.session import get_session

        engine = get_engine()
        async with get_session(engine) as session:
            result = await session.execute(
                text("DELETE FROM ban_list WHERE id = :id RETURNING id"),
                {"id": ban_id},
            )
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Ban entry {ban_id} not found")
            await session.commit()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


# ---------------------------------------------------------------------------
# Factory-built router with injected dependencies
# ---------------------------------------------------------------------------


def create_admin_router(
    *,
    saga_service: SagaService,
    outbox_repo: OutboxRepository,
    sync_service_provider=None,
) -> APIRouter:
    """Factory that creates admin routes with injected dependencies (DI).

    The factory is invoked once at application startup (see ``api/app.py``),
    not per-request. The returned ``APIRouter`` should be ``include_router``'d
    onto the FastAPI app at the ``/admin`` prefix.
    """
    router = APIRouter()

    @router.get(
        "/dead-letters",
        response_model=DeadLetterListResponse,
        summary="List dead-letter events",
        description="Retrieve failed outbox events (Operator only)",
        dependencies=[Depends(require_operator)],
    )
    async def list_dead_letters(
        request: Request,
        limit: int = Query(50, ge=1, le=1000, description="Max results"),
        offset: int = Query(0, ge=0, description="Result offset"),
    ) -> DeadLetterListResponse:
        """List dead-lettered events for the authenticated tenant.

        ADR 056 mandates tenant isolation: rows must be filtered by
        ``request.state.tenant_id`` (set by ``JWTAuthMiddleware``) rather
        than aggregated across all tenants.
        """
        tenant_id = getattr(request.state, "tenant_id", None)

        all_dead = await _list_dead_letters(outbox_repo, tenant_id=tenant_id)

        # Sort by created_at descending (newest first)
        all_dead.sort(key=lambda e: e.get("created_at") or "", reverse=True)

        total = len(all_dead)
        page = all_dead[offset : offset + limit]

        items = [
            DeadLetterItem(
                id=str(evt["id"]),
                tenant_id=str(evt["tenant_id"]),
                event_type=evt["event_type"],
                payload=evt["payload"],
                status=evt["status"],
                attempt_count=evt["attempt_count"],
                created_at=evt.get("created_at"),
                processed_at=evt.get("processed_at"),
                dead_letter_reason=evt.get("dead_letter_reason"),
            )
            for evt in page
        ]

        logger.info(
            "admin.list_dead_letters",
            extra={"tenant_id": tenant_id, "total": total, "returned": len(items)},
        )

        return DeadLetterListResponse(items=items, total=total, limit=limit, offset=offset)

    @router.post(
        "/dead-letters/{event_id}/retry",
        response_model=DeadLetterRetryResponse,
        summary="Retry dead-letter event",
        description="Move failed event back to pending (Operator only)",
        dependencies=[Depends(require_operator)],
    )
    async def retry_dead_letter(
        request: Request,
        event_id: Annotated[UUID, Path(description="Event ID")],
    ) -> DeadLetterRetryResponse:
        """Retry a dead-lettered event - reset to pending for reprocessing.

        Enforces tenant isolation: an Operator can only retry events that
        belong to their own tenant.
        """
        tenant_id = getattr(request.state, "tenant_id", None)

        # Protocol-friendly lookup (works for both the in-memory mock and the
        # SQL repository — never reach into a private ``.events`` dict).
        candidates = await outbox_repo.list_events(tenant_id=tenant_id)
        event = next((e for e in candidates if str(e["id"]) == str(event_id)), None)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        if event.get("status") != "dead":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Event {event_id} is not in dead-letter state "
                    f"(current: {event.get('status')})"
                ),
            )

        await outbox_repo.retry_dead_letter(event_id)

        logger.info(
            "admin.retry_dead_letter",
            extra={"tenant_id": tenant_id, "event_id": str(event_id)},
        )

        return DeadLetterRetryResponse(
            id=str(event_id),
            status="pending",
            message="Event reset to pending for reprocessing",
        )

    @router.post(
        "/outbox/process",
        response_model=OutboxProcessResponse,
        summary="Process pending outbox events",
        description=(
            "Drain pending back-office sync events for the authenticated tenant "
            "through its configured adapter (Operator only). Designed for cron."
        ),
        dependencies=[Depends(require_operator)],
    )
    async def process_outbox(
        request: Request,
        limit: int = Query(50, ge=1, le=500, description="Max events per run"),
    ) -> OutboxProcessResponse:
        """Run one back-office sync pass for the caller's tenant."""
        if sync_service_provider is None:
            raise HTTPException(status_code=503, detail="Back-office sync service not configured")
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        service = sync_service_provider()
        counters = await service.process_pending(
            tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id)),
            limit=limit,
        )
        logger.info(
            "admin.outbox_processed",
            extra={"tenant_id": str(tenant_id), **counters},
        )
        return OutboxProcessResponse(**counters)

    @router.get(
        "/sagas/{saga_id}/logs",
        response_model=SagaLogResponse,
        summary="Get saga execution log",
        description="Retrieve detailed saga step execution history (Operator only)",
        dependencies=[Depends(require_operator)],
    )
    async def get_saga_logs(
        saga_id: Annotated[UUID, Path(description="Saga ID")],
    ) -> SagaLogResponse:
        """Retrieve saga execution log and current state."""
        saga_ctx = await saga_service.get_saga_status(saga_id)
        if saga_ctx is None:
            raise HTTPException(status_code=404, detail=f"Saga {saga_id} not found")

        return SagaLogResponse(
            saga_id=str(saga_ctx.saga_id),
            saga_type=saga_ctx.saga_type,
            status=(
                saga_ctx.status.value if hasattr(saga_ctx.status, "value") else str(saga_ctx.status)
            ),
            current_step=saga_ctx.current_step,
            context=saga_ctx.context,
            last_error=saga_ctx.last_error,
            created_at=saga_ctx.created_at,
            updated_at=saga_ctx.updated_at,
        )

    return router


async def _list_dead_letters(
    outbox_repo: OutboxRepository,
    *,
    tenant_id: str | None,
) -> list[dict]:
    """List dead-letter events via the repository protocol.

    Prefers ``OutboxRepository.list_events(status='dead', tenant_id=...)``
    when available so a real Postgres impl can satisfy the same interface.
    Falls back to ``get_dead_letters(tenant_id)`` for protocol compatibility.
    """
    list_events = getattr(outbox_repo, "list_events", None)
    if list_events is not None:
        return await list_events(status="dead", tenant_id=tenant_id)

    # Fallback to protocol method (single-tenant view).
    if tenant_id is None:
        # Without a tenant_id we cannot safely cross-tenant query through the
        # protocol; return an empty list rather than leaking state.
        return []

    return await outbox_repo.get_dead_letters(tenant_id)
