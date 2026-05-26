/**
 * JobsPage — dead-letter outbox events with retry action.
 *
 * Lists failed outbox events from GET /admin/dead-letters and lets an
 * Operator re-queue any of them via POST /admin/dead-letters/{id}/retry.
 * After a successful retry the list refreshes so the event disappears.
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  type ApiError,
  type DeadLetterItem,
  listDeadLetters,
  retryDeadLetter,
} from '../api';

export const JobsPage: React.FC = () => {
  const [items, setItems] = useState<DeadLetterItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDeadLetters(50, 0);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      const apiErr = err as ApiError;
      const detail = apiErr?.detail || (err instanceof Error ? err.message : String(err));
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRetry = async (eventId: string): Promise<void> => {
    setRetryingId(eventId);
    setRetryError(null);
    try {
      await retryDeadLetter(eventId);
      await load();
    } catch (err) {
      const apiErr = err as ApiError;
      const detail = apiErr?.detail || (err instanceof Error ? err.message : String(err));
      setRetryError(detail);
    } finally {
      setRetryingId(null);
    }
  };

  if (loading) {
    return (
      <div>
        <h1>Jobs</h1>
        <h2 style={{ marginTop: 0, color: '#475569' }}>Dead-letter events</h2>
        <p>Loading dead-letter events…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1>Jobs</h1>
        <h2 style={{ marginTop: 0, color: '#475569' }}>Dead-letter events</h2>
        <p role="alert" style={{ color: '#b00020' }}>
          {error}
        </p>
        <button onClick={() => void load()}>Retry</button>
      </div>
    );
  }

  return (
    <div>
      <h1>Jobs</h1>
      <h2 style={{ marginTop: 0, color: '#475569' }}>Dead-letter events</h2>
      <p style={{ marginBottom: '0.75rem' }}>
        {total} dead-lettered event{total === 1 ? '' : 's'}.{' '}
        <button onClick={() => void load()}>Refresh</button>
      </p>

      {retryError && (
        <p role="alert" style={{ color: '#b00020' }}>
          {retryError}
        </p>
      )}

      {items.length === 0 ? (
        <p style={{ color: '#666' }}>No dead-letter events. </p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Event ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Type</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Attempts</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Reason</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} data-testid="dead-letter-row">
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>
                  <code>{item.id}</code>
                </td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{item.event_type}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{item.attempt_count}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>
                  {item.dead_letter_reason ?? '—'}
                </td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>
                  <button
                    onClick={() => void handleRetry(item.id)}
                    disabled={retryingId === item.id}
                  >
                    {retryingId === item.id ? 'Retrying…' : 'Retry'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
