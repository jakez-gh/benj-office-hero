from typing import Any

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from office_hero_mcp.client import get_client
from office_hero_mcp.server import tool


class GetHealthInput(BaseModel):
    # no parameters for health check
    pass


@tool(name="get_health", description="Return platform health", structured_output=False)
async def get_health(input: GetHealthInput, ctx: Context) -> Any:
    # propagate call to REST API /health, forwarding the caller's JWT
    return await get_client(ctx).get("/health")
