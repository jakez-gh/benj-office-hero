import { useEffect, useRef } from 'react';

const BASE_URL =
  (import.meta.env as { VITE_API_BASE_URL?: string }).VITE_API_BASE_URL ??
  'http://localhost:8000';

/**
 * Polls /health every 5 s while a network error is active.
 * Calls onRecover() as soon as the backend responds 2xx, triggering a refetch.
 */
export function useAutoRecover(isNetworkError: boolean, onRecover: () => void): void {
  const callbackRef = useRef(onRecover);
  // eslint-disable-next-line react-hooks/refs
  callbackRef.current = onRecover;

  useEffect(() => {
    if (!isNetworkError) return;

    const id = setInterval(async () => {
      try {
        const r = await fetch(`${BASE_URL}/health`, {
          signal: AbortSignal.timeout(3000),
        });
        if (r.ok) callbackRef.current();
      } catch {
        // still down
      }
    }, 5000);

    return () => clearInterval(id);
  }, [isNetworkError]);
}
