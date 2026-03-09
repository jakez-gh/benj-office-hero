"""Office Hero FastAPI application."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from office_hero.api.routes import admin, sagas

app = FastAPI(
    title="Office Hero",
    description="Back-office management API for office services",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


# Include routers
app.include_router(sagas.router, prefix="/sagas", tags=["sagas"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
