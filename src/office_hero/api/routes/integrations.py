"""Integration management routes (Slice 25-28).

Exposes:
  PATCH /admin/tenants/{tenant_id}/adapter  — set the tenant's back-office adapter
  GET   /admin/integrations/jobber/connect  — begin Jobber OAuth2 authorization flow
  GET   /admin/integrations/jobber/callback — exchange OAuth2 code for tokens

All routes require operator permission (``require_operator`` dependency).
The Jobber OAuth2 endpoints are meant to be visited in a browser — they redirect
rather than returning JSON.
"""

from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, text

from office_hero.api.routes.admin import require_operator

VALID_ADAPTERS: frozenset[str] = frozenset({"native", "servicetitan", "pestpac", "jobber"})


def create_integrations_router() -> APIRouter:
    """Create and return the integrations router (mount at /admin)."""
    router = APIRouter()

    # -----------------------------------------------------------------------
    # Tenant adapter management
    # -----------------------------------------------------------------------

    class AdapterUpdateRequest(BaseModel):
        model_config = {"extra": "forbid"}
        adapter: str

    @router.patch(
        "/tenants/{tenant_id}/adapter",
        summary="Update tenant back-office adapter",
        description=(
            "Set the back-office adapter for a tenant.  Valid values: "
            f"{sorted(VALID_ADAPTERS)}.  Operator only."
        ),
        dependencies=[Depends(require_operator)],
    )
    async def update_tenant_adapter(
        tenant_id: Annotated[UUID, Path(description="Tenant UUID")],
        body: AdapterUpdateRequest,
    ) -> dict:
        if body.adapter not in VALID_ADAPTERS:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid adapter '{body.adapter}'. "
                    f"Valid options: {sorted(VALID_ADAPTERS)}"
                ),
            )
        try:
            from office_hero.api.state import get_engine  # noqa: PLC0415
            from office_hero.db.session import get_session  # noqa: PLC0415
            from office_hero.models.tenant import Tenant  # noqa: PLC0415

            engine = get_engine()
            async with get_session(engine) as session:
                result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
                tenant = result.scalars().first()
                if tenant is None:
                    raise HTTPException(
                        status_code=404, detail=f"Tenant {tenant_id} not found"
                    )
                tenant.back_office_adapter = body.adapter
                await session.commit()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Database not available") from exc
        return {"tenant_id": str(tenant_id), "adapter": body.adapter}

    # -----------------------------------------------------------------------
    # Jobber OAuth2 connect / callback
    # -----------------------------------------------------------------------

    @router.get(
        "/integrations/jobber/connect",
        summary="Begin Jobber OAuth2 authorization flow",
        description=(
            "Redirects the operator's browser to the Jobber authorization page. "
            "Pass ``tenant_id`` so the callback can associate the tokens with the "
            "correct tenant.  Requires ``JOBBER_CLIENT_ID`` env var."
        ),
        dependencies=[Depends(require_operator)],
    )
    async def jobber_connect(
        tenant_id: Annotated[UUID, Query(description="Tenant to connect to Jobber")],
    ) -> RedirectResponse:
        client_id = os.environ.get("JOBBER_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=503, detail="JOBBER_CLIENT_ID not configured")
        params = {
            "client_id": client_id,
            "redirect_uri": _jobber_redirect_uri(),
            "scope": (
                "read_clients write_clients "
                "read_jobs write_jobs "
                "custom_field_configurations_read_write"
            ),
            "response_type": "code",
            "state": str(tenant_id),
        }
        return RedirectResponse(
            f"https://api.getjobber.com/api/oauth/authorize?{urlencode(params)}"
        )

    @router.get(
        "/integrations/jobber/callback",
        summary="Jobber OAuth2 callback — stores tokens and enables the adapter",
        description=(
            "Jobber redirects here after the operator authorizes the app. "
            "Exchanges the authorization code for access + refresh tokens, stores "
            "them in ``jobber_credentials``, and updates the tenant's adapter to "
            "``jobber``."
        ),
    )
    async def jobber_callback(code: str, state: str) -> RedirectResponse:
        try:
            tenant_id = UUID(state)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        client_id = os.environ.get("JOBBER_CLIENT_ID")
        client_secret = os.environ.get("JOBBER_CLIENT_SECRET")
        if not (client_id and client_secret):
            raise HTTPException(
                status_code=503, detail="JOBBER_CLIENT_ID / JOBBER_CLIENT_SECRET not configured"
            )

        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                "https://api.getjobber.com/api/oauth/token",
                content=urlencode(
                    {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": code,
                        "redirect_uri": _jobber_redirect_uri(),
                        "grant_type": "authorization_code",
                    }
                ).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Jobber token exchange failed: {resp.text[:300]}",
                )
            tokens = resp.json()

        try:
            from office_hero.api.state import get_engine  # noqa: PLC0415
            from office_hero.db.session import get_session  # noqa: PLC0415

            engine = get_engine()
            async with get_session(engine) as session:
                # Upsert credentials row (one per tenant)
                await session.execute(
                    text(
                        "INSERT INTO jobber_credentials "
                        "    (id, tenant_id, access_token, refresh_token, expires_at) "
                        "VALUES "
                        "    (gen_random_uuid(), :tid, :at, :rt, "
                        "     NOW() + (:expires_in * INTERVAL '1 second')) "
                        "ON CONFLICT (tenant_id) DO UPDATE SET "
                        "    access_token = EXCLUDED.access_token, "
                        "    refresh_token = EXCLUDED.refresh_token, "
                        "    expires_at    = EXCLUDED.expires_at, "
                        "    updated_at    = NOW()"
                    ),
                    {
                        "tid": tenant_id,
                        "at": tokens["access_token"],
                        "rt": tokens["refresh_token"],
                        "expires_in": tokens.get("expires_in", 3600),
                    },
                )
                # Switch tenant to the Jobber adapter
                await session.execute(
                    text(
                        "UPDATE tenants SET back_office_adapter = 'jobber' WHERE id = :id"
                    ),
                    {"id": tenant_id},
                )
                await session.commit()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Database not available") from exc

        return RedirectResponse("/admin")

    return router


def _jobber_redirect_uri() -> str:
    return os.environ.get(
        "JOBBER_OAUTH_REDIRECT_URI",
        "http://localhost:8000/admin/integrations/jobber/callback",
    )
