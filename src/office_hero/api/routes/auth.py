"""Authentication endpoints: login, refresh, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, EmailStr

from office_hero.api.deps import require_auth
from office_hero.api.state import get_auth_service, get_engine
from office_hero.core.exceptions import AuthError
from office_hero.db.session import get_session

# Router for auth endpoints
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request with email and password."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens and user info."""

    access_token: str
    refresh_token: str
    user: dict


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Refresh response with new access token."""

    access_token: str
    user: dict


class LogoutResponse(BaseModel):
    """Logout response."""

    status: str


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request_body: LoginRequest):
    """Authenticate user and return access/refresh tokens."""
    auth_service = get_auth_service()
    engine = get_engine()

    try:
        async with get_session(engine) as session:
            user, access_token, refresh_token = await auth_service.login(
                request_body.email, request_body.password, session
            )

            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                user={"id": str(user.id), "email": user.email, "role": user.role},
            )
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e.message)) from e


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
async def refresh(request_body: RefreshRequest):
    """Refresh access token using refresh token."""
    auth_service = get_auth_service()
    engine = get_engine()

    try:
        async with get_session(engine) as session:
            user, access_token = await auth_service.refresh(request_body.refresh_token, session)

            return RefreshResponse(
                access_token=access_token,
                user={"id": str(user.id), "email": user.email, "role": user.role},
            )
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e.message)) from e


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(request: Request, user_id: str = Depends(require_auth)):
    """Logout user by revoking refresh token."""
    # Refresh token revocation wired in Slice 4 (Observability) audit events.
    # JWT middleware handles token expiry; client should discard tokens on logout.
    return LogoutResponse(status="ok")
