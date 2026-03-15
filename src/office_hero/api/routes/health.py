"""Basic health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Return a lightweight liveness response."""
    return {"status": "ok"}
