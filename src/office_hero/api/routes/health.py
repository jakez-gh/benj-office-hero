"""Health check endpoint with DB and ORS reachability probes."""

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
async def health_check():
    """Check DB and ORS reachability. Returns 200 if healthy, 503 if not."""
    db_status = "ok"
    ors_status = "ok"

    # DB reachability: execute SELECT 1
    # Catch all exceptions: health checks must not crash; any DB error is a failure signal
    try:
        engine = get_engine()
        async with get_session(engine) as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("health.db_check_failed", error=str(exc))
        db_status = "error"

    # ORS reachability: HTTP GET to configured health URL
    # Catch all exceptions: timeouts, connection errors, etc. are health failures
    ors_url = os.getenv("ORS_HEALTH_URL", "http://localhost:5000/health")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(ors_url)
            if resp.status_code >= 500:
                ors_status = "degraded"
    except Exception as exc:
        log.warning("health.ors_check_failed", error=str(exc))
        ors_status = "error"

    overall = "ok" if db_status == "ok" and ors_status == "ok" else "unhealthy"
    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "db": db_status, "ors": ors_status},
    )
