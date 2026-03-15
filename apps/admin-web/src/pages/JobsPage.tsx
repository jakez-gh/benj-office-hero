/**
 * JobsPage — lists dead-letter events and provides retry controls.
 *
 * Interactive controls:
 *   1. Table of dead-letter events from GET /admin/dead-letters
 *   2. "Retry" button per row calls POST /admin/dead-letters/{id}/retry
 *   3. Saga logs panel for selected saga (GET /admin/sagas/{id}/logs)
 */

import { useCallback, useEffect, useState } from 'react';
import {
  listDeadLetters,
  retryDeadLetter,
  getSagaLogs,
  type DeadLetterItem,
  type SagaState,
} from '../api';
import { SagaStatusBadge } from '../components/SagaStatusBadge';

export function JobsPage() {
  const [events, setEvents] = useState<DeadLetterItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedLogs, setSelectedLogs] = useState<SagaState | null>(null);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listDeadLetters();
      setEvents(data.items);
    } catch {
      setError('Failed to load dead-letter events');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleRetry = useCallback(
    async (eventId: string) => {
      setRetrying(eventId);
      setError(null);
      setSuccess(null);
      try {
        await retryDeadLetter(eventId);
        setSuccess(`Event ${eventId.slice(0, 8)}… queued for retry`);
        await fetchEvents(); // Refresh list
      } catch {
        setError(`Failed to retry event ${eventId.slice(0, 8)}…`);
      } finally {
        setRetrying(null);
      }
    },
    [fetchEvents],
  );

  const handleViewLogs = useCallback(async (sagaId: string) => {
    try {
      const logs = await getSagaLogs(sagaId);
      setSelectedLogs(logs);
    } catch {
      setError(`Failed to load logs for saga ${sagaId.slice(0, 8)}…`);
    }
  }, []);

  return (
    <div data-testid="jobs-page">
      <h1>📋 Jobs &amp; Dead Letters</h1>
      <p>View failed saga events and retry them.</p>

      <button
        onClick={fetchEvents}
        disabled={loading}
        style={refreshBtnStyle}
        data-testid="refresh-button"
      >
        {loading ? '⏳ Loading...' : '🔄 Refresh'}
      </button>

      {error && (
        <div style={errorStyle} data-testid="jobs-error">
          ❌ {error}
        </div>
      )}

      {success && (
        <div style={successStyle} data-testid="jobs-success">
          ✅ {success}
        </div>
      )}

      {!loading && events.length === 0 && (
        <div style={emptyStyle} data-testid="no-events">
          🎉 No dead-letter events — all sagas running smoothly!
        </div>
      )}

      {events.length > 0 && (
        <table style={tableStyle} data-testid="dead-letter-table">
          <thead>
            <tr>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Event Type</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Attempts</th>
              <th style={thStyle}>Payload</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {events.map((evt) => (
              <tr key={evt.id}>
                <td style={tdStyle}>{evt.id.slice(0, 8)}…</td>
                <td style={tdStyle}>{evt.event_type}</td>
                <td style={tdStyle}>
                  <SagaStatusBadge status={evt.status} />
                </td>
                <td style={tdStyle}>{evt.attempt_count}</td>
                <td style={tdStyle}>
                  <code style={{ fontSize: '0.8rem' }}>
                    {JSON.stringify(evt.payload).slice(0, 60)}
                  </code>
                </td>
                <td style={tdStyle}>
                  <button
                    onClick={() => handleRetry(evt.id)}
                    disabled={retrying === evt.id}
                    style={retryBtnStyle}
                    data-testid={`retry-${evt.id}`}
                  >
                    {retrying === evt.id ? '⏳' : '🔁 Retry'}
                  </button>
                  <button
                    onClick={() => handleViewLogs(evt.id)}
                    style={logsBtnStyle}
                    data-testid={`logs-${evt.id}`}
                  >
                    📜 Logs
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedLogs && (
        <div style={logsCardStyle} data-testid="saga-logs-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <h3>Saga Details — {selectedLogs.saga_id.slice(0, 8)}…</h3>
            <button onClick={() => setSelectedLogs(null)} style={closeBtnStyle}>
              ✕
            </button>
          </div>
          <p><strong>Type:</strong> {selectedLogs.saga_type}</p>
          <p><strong>Status:</strong> <SagaStatusBadge status={selectedLogs.status} /></p>
          <p><strong>Step:</strong> {selectedLogs.current_step}</p>
          {selectedLogs.last_error && (
            <p style={{ color: '#ef4444' }}><strong>Error:</strong> {selectedLogs.last_error}</p>
          )}
          <p style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
            <strong>Context:</strong> {JSON.stringify(selectedLogs.context, null, 2)}
          </p>
        </div>
      )}
    </div>
  );
}

// Styles
const refreshBtnStyle: React.CSSProperties = {
  padding: '0.4rem 1rem',
  background: '#6366f1',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: '0.85rem',
  marginBottom: '1rem',
};
const retryBtnStyle: React.CSSProperties = {
  padding: '0.25rem 0.75rem',
  background: '#f59e0b',
  color: '#fff',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: '0.8rem',
  marginRight: '0.5rem',
};
const logsBtnStyle: React.CSSProperties = {
  padding: '0.25rem 0.75rem',
  background: '#8b5cf6',
  color: '#fff',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: '0.8rem',
};
const errorStyle: React.CSSProperties = {
  padding: '0.75rem',
  background: '#fef2f2',
  color: '#991b1b',
  borderRadius: '6px',
  border: '1px solid #fca5a5',
  margin: '0.5rem 0',
};
const successStyle: React.CSSProperties = {
  padding: '0.75rem',
  background: '#f0fdf4',
  color: '#166534',
  borderRadius: '6px',
  border: '1px solid #86efac',
  margin: '0.5rem 0',
};
const emptyStyle: React.CSSProperties = {
  padding: '2rem',
  textAlign: 'center',
  color: '#6b7280',
  fontSize: '1.1rem',
};
const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '0.9rem',
};
const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '0.5rem',
  borderBottom: '2px solid #e5e7eb',
  fontWeight: 600,
};
const tdStyle: React.CSSProperties = {
  padding: '0.5rem',
  borderBottom: '1px solid #f3f4f6',
};
const logsCardStyle: React.CSSProperties = {
  marginTop: '1.5rem',
  padding: '1rem',
  background: '#faf5ff',
  border: '1px solid #ddd6fe',
  borderRadius: '8px',
};
const closeBtnStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: '1.2rem',
  cursor: 'pointer',
  color: '#6b7280',
};
