/**
 * DispatchPage — dispatch a job via the backoffice saga API.
 *
 * Posts to POST /sagas with saga_type="dispatch_job" and the form payload,
 * then polls GET /sagas/{id}/state via useSagaStatus and renders the live
 * saga state with SagaStatusBadge.
 */

import React, { useState } from 'react';
import { type ApiError, type SagaState, createSaga } from '../api';
import { SagaStatusBadge } from '../components/SagaStatusBadge';
import { useSagaStatus } from '../hooks/useSagaStatus';

export const DispatchPage: React.FC = () => {
  const [tenantId, setTenantId] = useState('');
  const [jobId, setJobId] = useState('');
  const [technicianId, setTechnicianId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submittedSaga, setSubmittedSaga] = useState<SagaState | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    saga: liveSaga,
    error: pollError,
    refresh,
  } = useSagaStatus(submittedSaga?.saga_id ?? null);

  // Prefer the polled state once it arrives so the badge reflects later steps.
  const displaySaga: SagaState | null = liveSaga ?? submittedSaga;

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    setSubmittedSaga(null);

    try {
      const saga = await createSaga({
        saga_type: 'dispatch_job',
        context: {
          tenant_id: tenantId,
          job_id: jobId,
          technician_id: technicianId,
        },
      });
      setSubmittedSaga(saga);
    } catch (err) {
      const apiErr = err as ApiError;
      const detail = apiErr?.detail || (err instanceof Error ? err.message : String(err));
      setSubmitError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    display: 'block',
    width: '100%',
    padding: '0.5rem',
    marginTop: '0.25rem',
    marginBottom: '0.75rem',
    border: '1px solid #ccc',
    borderRadius: '4px',
  };

  return (
    <div>
      <h1>Dispatch</h1>
      <p style={{ color: '#666', marginBottom: '1rem' }}>
        Dispatch a job through the backoffice saga orchestrator.
      </p>

      <form onSubmit={(e) => void handleSubmit(e)} style={{ maxWidth: '32rem' }}>
        <label htmlFor="dispatch-tenant">
          Tenant ID
          <input
            id="dispatch-tenant"
            type="text"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            required
            style={inputStyle}
          />
        </label>

        <label htmlFor="dispatch-job">
          Job ID
          <input
            id="dispatch-job"
            type="text"
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
            required
            style={inputStyle}
          />
        </label>

        <label htmlFor="dispatch-technician">
          Technician ID
          <input
            id="dispatch-technician"
            type="text"
            value={technicianId}
            onChange={(e) => setTechnicianId(e.target.value)}
            required
            style={inputStyle}
          />
        </label>

        <button
          type="submit"
          disabled={submitting}
          style={{
            padding: '0.5rem 1rem',
            background: submitting ? '#94a3b8' : '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: submitting ? 'not-allowed' : 'pointer',
          }}
        >
          {submitting ? 'Dispatching…' : 'Dispatch Job'}
        </button>
      </form>

      {submitError && (
        <p role="alert" style={{ color: '#b00020', marginTop: '1rem' }}>
          {submitError}
        </p>
      )}

      {displaySaga && (
        <section style={{ marginTop: '2rem', padding: '1rem', background: '#f8fafc', borderRadius: '6px' }}>
          <h2 style={{ marginTop: 0 }}>Saga state</h2>
          <p>
            <strong>ID:</strong> <code>{displaySaga.saga_id}</code>
          </p>
          <p>
            <strong>Status:</strong> <SagaStatusBadge status={displaySaga.status} />
          </p>
          <p>
            <strong>Current step:</strong> {displaySaga.current_step}
          </p>
          {displaySaga.last_error && (
            <p style={{ color: '#b00020' }}>
              <strong>Last error:</strong> {displaySaga.last_error}
            </p>
          )}
          {pollError && (
            <p role="alert" style={{ color: '#b00020' }}>
              Polling error: {pollError}
            </p>
          )}
          <button onClick={refresh} style={{ marginTop: '0.5rem' }}>
            Refresh
          </button>
        </section>
      )}
    </div>
  );
};
