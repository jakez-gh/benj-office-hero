from typing import Any

from pydantic import BaseModel

from office_hero_mcp.client import client
from office_hero_mcp.server import tool


class GetHealthInput(BaseModel):
    # no parameters for health check
    pass


@tool(name="get_health", description="Return platform health", structured_output=False)
async def get_health(input: GetHealthInput) -> Any:
    # propagate call to REST API /health
    return await client.get("/health")
