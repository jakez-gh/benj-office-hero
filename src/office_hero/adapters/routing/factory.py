"""Factory for building a :class:`RoutingAdapter` from environment."""

from __future__ import annotations

import os

from office_hero.adapters.routing.protocol import RoutingAdapter
from office_hero.adapters.routing.stub import StubRoutingAdapter


def build_routing_adapter() -> RoutingAdapter:
    """Return StubRoutingAdapter unless ORS_API_KEY is set in the environment."""
    api_key = os.environ.get("ORS_API_KEY", "").strip()
    if not api_key:
        return StubRoutingAdapter()

    from office_hero.adapters.routing.ors import ORSRoutingAdapter

    return ORSRoutingAdapter(api_key=api_key)
