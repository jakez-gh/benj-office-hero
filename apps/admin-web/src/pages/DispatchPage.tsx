/**
 * DispatchPage — dispatches a job via POST /sagas and shows saga status.
 *
 * Interactive controls:
 *   1. Form to specify saga_type (dispatch_job), job_id, technician_id
 *   2. "Dispatch" button calls createSaga()
 *   3. SagaStatusBadge shows real-time status (pending → running → done/failed)
 */

import React, { useCallback, useState } from 'react';
import { createSaga, type SagaState } from '../api';
import { SagaStatusBadge } from '../components/SagaStatusBadge';
import { useSagaStatus } from '../hooks/useSagaStatus';

export function DispatchPage() {
  const [jobId, setJobId] = useState('');
  const [technicianId, setTechnicianId] = useState('');
  const [dispatching, setDispatching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSagaId, setLastSagaId] = useState<string | null>(null);
  const [history, setHistory] = useState<SagaState[]>([]);

  const { saga: liveSaga } = useSagaStatus(lastSagaId);

  const handleDispatch = useCallback(async () => {
    setDispatching(true);
    setError(null);
    try {
      const result = await createSaga({
        saga_type: 'dispatch_job',
        context: {
          job_id: jobId || crypto.randomUUID(),
          technician_id: technicianId || crypto.randomUUID(),
        },
      });
      setLastSagaId(result.saga_id);
      setHistory((prev) => [result, ...prev]);
      setJobId('');
      setTechnicianId('');
    } catch (err: unknown) {
      const message = (err as { detail?: string })?.detail || 'Dispatch failed';
      setError(message);
    } finally {
      setDispatching(false);
    }
  }, [jobId, technicianId]);

  return (
    <div data-testid="dispatch-page">
      <h1>🚀 Dispatch</h1>
      <p>Dispatch a job to a technician via the saga orchestration system.</p>

      <div style={{ display: 'flex', gap: '1rem', margin: '1rem 0', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Job ID (auto-generated if empty)"
          value={jobId}
          onChange={(e) => setJobId(e.target.value)}
          style={inputStyle}
          data-testid="job-id-input"
        />
        <input
          type="text"
          placeholder="Technician ID (auto-generated if empty)"
          value={technicianId}
          onChange={(e) => setTechnicianId(e.target.value)}
          style={inputStyle}
          data-testid="technician-id-input"
        />
        <button
          onClick={handleDispatch}
          disabled={dispatching}
          style={buttonStyle}
          data-testid="dispatch-button"
        >
          {dispatching ? '⏳ Dispatching...' : '🚀 Dispatch Job'}
        </button>
      </div>

      {error && (
        <div style={errorStyle} data-testid="dispatch-error">
          ❌ {error}
        </div>
      )}

      {liveSaga && (
        <div style={statusCardStyle} data-testid="live-saga-status">
          <h3>Current Saga</h3>
          <p>
            <strong>ID:</strong> {liveSaga.saga_id}
          </p>
          <p>
            <strong>Status:</strong> <SagaStatusBadge status={liveSaga.status} />
          </p>
          <p>
            <strong>Step:</strong> {liveSaga.current_step}
          </p>
          {liveSaga.last_error && (
            <p style={{ color: '#ef4444' }}>
              <strong>Error:</strong> {liveSaga.last_error}
            </p>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <h3>Dispatch History</h3>
          <table style={tableStyle} data-testid="dispatch-history">
            <thead>
              <tr>
                <th style={thStyle}>Saga ID</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Step</th>
                <th style={thStyle}>Created</th>
              </tr>
            </thead>
            <tbody>
              {history.map((s) => (
                <tr key={s.saga_id}>
                  <td style={tdStyle}>{s.saga_id.slice(0, 8)}…</td>
                  <td style={tdStyle}>{s.saga_type}</td>
                  <td style={tdStyle}>
                    <SagaStatusBadge status={s.status} />
                  </td>
                  <td style={tdStyle}>{s.current_step}</td>
                  <td style={tdStyle}>{s.created_at || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Inline styles (SOLID — presentation isolated from logic)
const inputStyle: React.CSSProperties = {
  padding: '0.5rem',
  border: '1px solid #d1d5db',
  borderRadius: '6px',
  fontSize: '0.9rem',
  minWidth: '220px',
};
const buttonStyle: React.CSSProperties = {
  padding: '0.5rem 1.25rem',
  background: '#3b82f6',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: '0.9rem',
};
const errorStyle: React.CSSProperties = {
  padding: '0.75rem',
  background: '#fef2f2',
  color: '#991b1b',
  borderRadius: '6px',
  border: '1px solid #fca5a5',
  margin: '0.5rem 0',
};
const statusCardStyle: React.CSSProperties = {
  padding: '1rem',
  background: '#f0f9ff',
  border: '1px solid #bae6fd',
  borderRadius: '8px',
  margin: '1rem 0',
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
