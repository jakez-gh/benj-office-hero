from typing import Any

from pydantic import BaseModel

from office_hero_mcp.client import client
from office_hero_mcp.server import tool


class RoutingOptionsInput(BaseModel):
    job_id: int


@tool(name="get_routing_options", description="Fetch routing options for a job")
async def get_routing_options(input: RoutingOptionsInput) -> list[Any]:
    # call REST API POST /jobs/{id}/routing-options
    resp = await client.post(f"/jobs/{input.job_id}/routing-options")
    # assume response is list of option objects
    return resp


class DispatchJobInput(BaseModel):
    job_id: int
    option_id: Any


@tool(name="dispatch_job", description="Dispatch a job using selected option")
async def dispatch_job(input: DispatchJobInput) -> Any:
    data = {"option_id": input.option_id}
    return await client.post(f"/jobs/{input.job_id}/dispatch", json=data)
