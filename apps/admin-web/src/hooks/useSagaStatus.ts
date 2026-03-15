/**
 * useSagaStatus hook — polls saga state and returns reactive status.
 *
 * Used by DispatchPage to show saga progress (pending → running → done/failed).
 */

import { useCallback, useEffect, useState } from 'react';
import { type SagaState, getSagaState } from '../api';

export type SagaStatusState = {
  saga: SagaState | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
};

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

  const fetchState = useCallback(async () => {
    if (!sagaId) return;
    setLoading(true);
    setError(null);
    try {
      const state = await getSagaState(sagaId);
      setSaga(state);
    } catch (err: unknown) {
      const message = (err as { detail?: string })?.detail || 'Failed to fetch saga state';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [sagaId]);

  useEffect(() => {
    if (!sagaId) return;
    fetchState();

    // Poll until terminal state
    const id = setInterval(() => {
      if (saga?.status === 'done' || saga?.status === 'failed') {
        clearInterval(id);
        return;
      }
      fetchState();
    }, intervalMs);

    return () => clearInterval(id);
  }, [sagaId, intervalMs, fetchState, saga?.status]);

  return { saga, loading, error, refresh: fetchState };
}
