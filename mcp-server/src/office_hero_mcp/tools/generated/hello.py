# AUTO-GENERATED from openapi spec - DO NOT EDIT
from typing import Any

from pydantic import BaseModel

from office_hero_mcp.client import client
from office_hero_mcp.server import tool


class HelloInput(BaseModel):
    pass


@tool(name="hello", description="Say hello")
async def hello(input: HelloInput) -> Any:
    # stub implementation; replace with actual HTTP call
    return await client.request("GET", "")
