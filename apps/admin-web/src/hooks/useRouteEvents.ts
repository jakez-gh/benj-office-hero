import { useCallback, useEffect } from 'react';

const BACKEND = (import.meta as { env: { VITE_API_BASE_URL?: string } }).env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface RouteEvent {
  type:
    | 'route_started'
    | 'route_cancelled'
    | 'stop_arrived'
    | 'stop_completed'
    | 'stop_skipped';
  route_id: string;
  stop_id?: string;
  reason?: string;
}

/**
 * Subscribe to the SSE stream for a route's state-change events.
 * The browser's EventSource reconnects automatically on network errors.
 * Pass null routeId to disable (no connection opened).
 */
export function useRouteEvents(
  routeId: string | null,
  onEvent: (event: RouteEvent) => void,
): void {
  // Wrap onEvent in useCallback at the call site, or stabilise here with a ref
  // to avoid re-subscribing on every render.
  const stableOnEvent = useCallback(onEvent, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!routeId) return;

    const url = `${BACKEND}/routes/${encodeURIComponent(routeId)}/events`;
    const es = new EventSource(url);

    es.onmessage = (e: MessageEvent) => {
      try {
        stableOnEvent(JSON.parse(e.data as string) as RouteEvent);
      } catch {
        // Malformed event — ignore
      }
    };

    // onerror: browser will auto-reconnect with exponential backoff
    es.onerror = () => {};

    return () => {
      es.close();
    };
  }, [routeId, stableOnEvent]);
}
