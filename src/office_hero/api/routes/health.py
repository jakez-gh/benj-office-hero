"""Health check endpoints.

ADR 050 specifies that the API surface includes a health endpoint that probes
DB connectivity and routing engine reachability. We split this into two
endpoints to match Kubernetes/Fly.io liveness vs readiness semantics:

* ``GET /health`` is a cheap liveness check — used by Fly.io and the
  ``server_manager`` hook to determine whether the process is responsive.
  It returns ``{"status": "ok"}`` and intentionally performs no I/O.
* ``GET /health/ready`` is a readiness check — it probes DB connectivity and
  the routing engine (ORS) and returns the full ``{status, db, ors}`` shape
  with status 200 when both are healthy and 503 otherwise.
"""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from office_hero.api.state import get_engine
from office_hero.core.logging import get_logger
from office_hero.db.session import get_session

log = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight liveness probe.

    Returns immediately without performing any I/O. Used by container
    orchestrators (Fly.io) to detect a wedged process and by the
    ``tools/server_manager.py`` post-merge hook to confirm the test backend is
    accepting requests. Deeper checks live on ``/health/ready``.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> JSONResponse:
    """Readiness probe — verifies DB + ORS reachability.

    Returns 200 with ``{"status": "ok", "db": "ok", "ors": "ok"}`` when both
    dependencies respond; 503 with per-dependency status strings otherwise.
    """
    db_status = "ok"
    ors_status = "ok"

    # DB reachability: execute SELECT 1.
    # Catch broad Exception — a readiness probe must not crash; any error is
    # a failure signal regardless of class.
    try:
        engine = get_engine()
        async with get_session(engine) as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - intentional broad catch
        log.warning("health.db_check_failed", error=str(exc))
        db_status = "error"

    # ORS reachability: HTTP GET to the configured health URL.
    ors_url = os.getenv("ORS_HEALTH_URL", "http://localhost:5000/health")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(ors_url)
            if resp.status_code >= 500:
                ors_status = "degraded"
    except Exception as exc:  # noqa: BLE001 - intentional broad catch
        log.warning("health.ors_check_failed", error=str(exc))
        ors_status = "error"

    overall = "ok" if db_status == "ok" and ors_status == "ok" else "unhealthy"
    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "db": db_status, "ors": ors_status},
    )
