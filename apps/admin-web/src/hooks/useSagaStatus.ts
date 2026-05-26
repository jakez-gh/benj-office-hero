/**
 * useSagaStatus hook — polls saga state and returns reactive status.
 *
 * Used by DispatchPage to show saga progress (pending -> running -> done/failed).
 *
 * The polling interval is started once per `sagaId` (or `intervalMs`) change.
 * To avoid the "interval restarted on every tick" stale-closure bug, the
 * latest saga reference is held in a ref and the interval reads that ref
 * each tick. The interval is cleared once a terminal status is observed.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { type SagaState, getSagaState } from '../api';

export type SagaStatusState = {
  saga: SagaState | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
};

const TERMINAL_STATUSES = new Set(['done', 'failed']);

/**
 * Poll a saga's state every `intervalMs` milliseconds.
 * Stops polling once status is 'done' or 'failed'.
 */
export function useSagaStatus(
  sagaId: string | null,
  intervalMs = 2000,
): SagaStatusState {
  const [saga, setSaga] = useState<SagaState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Hold the latest saga in a ref so the interval can read it without
  // being re-mounted every time the status updates.
  const sagaRef = useRef<SagaState | null>(null);

  const fetchState = useCallback(async () => {
    if (!sagaId) return;
    setLoading(true);
    setError(null);
    try {
      const state = await getSagaState(sagaId);
      sagaRef.current = state;
      setSaga(state);
    } catch (err: unknown) {
      const message = (err as { detail?: string })?.detail || 'Failed to fetch saga state';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [sagaId]);

  useEffect(() => {
    // Reset cached state when the saga id changes so a stale previous
    // saga doesn't keep us from polling.
    sagaRef.current = null;
    setSaga(null);

    if (!sagaId) return;

    // Kick off an immediate read.
    void fetchState();

    const id = setInterval(() => {
      const current = sagaRef.current;
      if (current && TERMINAL_STATUSES.has(current.status)) {
        clearInterval(id);
        return;
      }
      void fetchState();
    }, intervalMs);

    return () => clearInterval(id);
    // We intentionally exclude `saga` (or `saga?.status`) from deps so that
    // the interval is mounted once per sagaId and reads the latest state
    // from `sagaRef` without re-creating the timer on every tick.
  }, [sagaId, intervalMs, fetchState]);

  return { saga, loading, error, refresh: fetchState };
}
