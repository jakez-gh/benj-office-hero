---
id: 1.1.2.17
title: Slice 032 — Live route events via SSE
type: slice-design
parent: 1.1.2
status: complete
size: small
slice: live-route-events
dateCreated: 20260627
dateUpdated: 20260627
---

# Slice Design 032: Live Route Events via SSE

## Goal

Push route status changes to the admin web in real time so a dispatcher
sees stop-level progress (arrived, complete, cancelled) the moment a
technician acts — without page reloads or manual polling.

Architecture decision: ADR-064 (`064-adr.server-sent-events.md`)

## Definition of Done

- `GET /routes/{route_id}/events` streams `text/event-stream`
- Events emitted on: stop arrived, stop complete, stop skipped, route started,
  route cancelled
- `RoutesPage.tsx` subscribes to SSE for every `in_progress` route on the page
- When an event arrives the matching `RouteCard` updates without a page reload
- GPS 30 s poll unchanged by this slice (deferred to a future slice)
- TypeScript clean, `pnpm tsc --noEmit`
- At least one unit test for the event hub (publish → subscriber receives event)

## Architecture

```
tech mobile             admin web dispatcher
   |                          |
   POST /routes/{id}/stops/{sid}/arrived
                              |
   backend route handler ─────+──► publish("route:<id>", event)
                                        |
                              event hub (asyncio Queue per subscriber)
                                        |
                              GET /routes/{id}/events  (SSE stream)
                                        |
                              admin web EventSource → setState patch
```

## Backend

### `src/office_hero/core/route_events.py`

```python
from asyncio import Queue
from collections import defaultdict
from typing import AsyncGenerator
import json, asyncio

_subscribers: defaultdict[str, list[Queue]] = defaultdict(list)

async def subscribe(topic: str) -> AsyncGenerator[str, None]:
    q: Queue[str] = Queue()
    _subscribers[topic].append(q)
    try:
        while True:
            yield await q.get()
    finally:
        _subscribers[topic].remove(q)

async def publish(topic: str, payload: dict) -> None:
    for q in list(_subscribers.get(topic, [])):
        await q.put(json.dumps(payload))
```

### New SSE endpoint in `routes.py`

```python
@router.get("/{route_id}/events", response_class=StreamingResponse)
async def route_event_stream(route_id: UUID, ...):
    async def gen():
        async for msg in subscribe(f"route:{route_id}"):
            yield f"data: {msg}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
```

### Publish after each stop state change

After `mark_stop_arrived`, `mark_stop_complete`, `skip_stop`, `start_route`,
`cancel_route` — add:

```python
from office_hero.core.route_events import publish
await publish(f"route:{route_id}", {"type": "stop_arrived", "stop_id": str(stop_id), ...})
```

## Frontend

### `apps/admin-web/src/hooks/useRouteEvents.ts`

```typescript
import { useEffect } from 'react';
const BACKEND = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export function useRouteEvents(
  routeId: string | null,
  onEvent: (event: RouteEvent) => void,
): void {
  useEffect(() => {
    if (!routeId) return;
    const token = localStorage.getItem('access_token') ?? '';
    const es = new EventSource(`${BACKEND}/routes/${routeId}/events?token=${encodeURIComponent(token)}`);
    es.onmessage = (e) => { onEvent(JSON.parse(e.data) as RouteEvent); };
    es.onerror = () => {}; // browser auto-reconnects
    return () => es.close();
  }, [routeId, onEvent]);
}
```

### `RoutesPage.tsx` changes

For each `in_progress` route card, subscribe via `useRouteEvents` and apply
the event as a state patch:

```typescript
useRouteEvents(inProgressRouteId, useCallback((ev) => {
  setRoutes(prev => prev.map(r => r.id === ev.route_id ? applyEvent(r, ev) : r));
}, []));
```

`applyEvent` returns a new `RouteRead` with the relevant stop status updated.

## Out of scope

- GPS position push (still polled every 30 s — tracked as future work)
- Horizontal scaling / Redis pub/sub (single Fly.io instance)
- Persisting SSE event log

## Dependencies

- Slice 031 (UI improvements) complete — yes
- No new packages needed (`EventSource` is a browser built-in)

## Effort: 2/5
