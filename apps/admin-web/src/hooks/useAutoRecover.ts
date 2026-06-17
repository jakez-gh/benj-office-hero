import { useEffect, useRef } from 'react';

function resolveBaseUrl(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const meta = (Function('return import.meta') as any)();
    if (meta?.env?.VITE_API_BASE_URL) return meta.env.VITE_API_BASE_URL as string;
  } catch { /* import.meta not available in CommonJS/Jest */ }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const proc = (globalThis as any).process;
  if (proc?.env?.VITE_API_BASE_URL) return proc.env.VITE_API_BASE_URL as string;
  return 'http://localhost:8000';
}

const BASE_URL = resolveBaseUrl();

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
