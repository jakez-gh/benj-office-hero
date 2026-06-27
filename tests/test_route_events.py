"""Unit tests for the route_events pub/sub hub."""

import asyncio
import json

import pytest

from office_hero.core.route_events import _subscribers, publish, subscribe, subscriber_count


@pytest.fixture(autouse=True)
def clear_route_event_state():
    """Reset global subscriber dict before/after each test to prevent cross-test leakage."""
    _subscribers.clear()
    yield
    _subscribers.clear()


@pytest.mark.asyncio
async def test_publish_reaches_subscriber() -> None:
    topic = "route:aaaaaaaa-0000-0000-0000-000000000001"
    received: list[dict] = []

    async def consumer() -> None:
        async for msg in subscribe(topic):
            received.append(json.loads(msg))
            return  # consume one message then exit

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0)  # yield so consumer can register

    await publish(topic, {"type": "stop_arrived", "stop_id": "s1"})
    await task

    assert received == [{"type": "stop_arrived", "stop_id": "s1"}]


@pytest.mark.asyncio
async def test_publish_to_multiple_subscribers() -> None:
    topic = "route:bbbbbbbb-0000-0000-0000-000000000002"
    received_a: list[dict] = []
    received_b: list[dict] = []

    async def consumer_a() -> None:
        async for msg in subscribe(topic):
            received_a.append(json.loads(msg))
            return

    async def consumer_b() -> None:
        async for msg in subscribe(topic):
            received_b.append(json.loads(msg))
            return

    ta = asyncio.create_task(consumer_a())
    tb = asyncio.create_task(consumer_b())
    await asyncio.sleep(0)

    await publish(topic, {"type": "route_started"})
    await ta
    await tb

    assert received_a == [{"type": "route_started"}]
    assert received_b == [{"type": "route_started"}]


@pytest.mark.asyncio
async def test_publish_to_unknown_topic_is_noop() -> None:
    await publish("route:nonexistent", {"type": "test"})  # must not raise


@pytest.mark.asyncio
async def test_subscriber_count() -> None:
    topic = "route:cccccccc-0000-0000-0000-000000000003"
    assert subscriber_count(topic) == 0

    received: asyncio.Event = asyncio.Event()

    async def consumer() -> None:
        async for _msg in subscribe(topic):
            received.set()
            # Stay in the loop so the generator remains open until we cancel.
            # This mirrors the real SSE use-case and lets cancel() propagate
            # CancelledError directly into the generator's finally block.

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0)

    assert subscriber_count(topic) == 1

    await publish(topic, {"type": "ping"})
    await received.wait()
    # Consumer re-enters the generator after received.set(), suspending at
    # yield await q.get() before the event loop returns here.
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert subscriber_count(topic) == 0


@pytest.mark.asyncio
async def test_subscriber_removed_on_cancellation() -> None:
    topic = "route:dddddddd-0000-0000-0000-000000000004"

    async def consumer() -> None:
        async for _msg in subscribe(topic):
            pass  # pragma: no cover

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0)
    assert subscriber_count(topic) == 1

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert subscriber_count(topic) == 0
