"""Async pub/sub hub for route state-change events.

Admin-web clients subscribe to a route's event stream via SSE
(GET /routes/{id}/events). Route API handlers publish here after each
state-changing operation so connected dispatchers see updates instantly.

Scalability note: subscriptions live in process memory, so this works
correctly on a single Fly.io instance. Replace `_subscribers` with a
Redis pub/sub backend if the deployment ever scales horizontally.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, AsyncGenerator

_subscribers: defaultdict[str, list[asyncio.Queue[str]]] = defaultdict(list)


async def subscribe(topic: str) -> AsyncGenerator[str, None]:
    """Yield JSON-encoded event strings until the caller disconnects."""
    q: asyncio.Queue[str] = asyncio.Queue()
    _subscribers[topic].append(q)
    try:
        while True:
            yield await q.get()
    finally:
        try:
            _subscribers[topic].remove(q)
        except ValueError:
            pass


async def publish(topic: str, payload: dict[str, Any]) -> None:
    """Broadcast a payload to all current subscribers of *topic*."""
    message = json.dumps(payload)
    for q in list(_subscribers.get(topic, [])):
        await q.put(message)


def subscriber_count(topic: str) -> int:
    """Return the number of active SSE subscribers for *topic* (test helper)."""
    return len(_subscribers.get(topic, []))
