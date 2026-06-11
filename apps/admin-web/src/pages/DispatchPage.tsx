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
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';

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

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">Dispatch</h1>
        <p className="mt-0.5 text-sm text-neutral-500">
          Dispatch a job through the backoffice saga orchestrator.
        </p>
      </div>

      <div className="grid max-w-4xl gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-4">
            <CardTitle>Job details</CardTitle>
            <CardDescription>
              Assign a job to a technician and track the orchestration live.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="dispatch-tenant">Tenant ID</Label>
                <Input
                  id="dispatch-tenant"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="dispatch-job">Job ID</Label>
                <Input
                  id="dispatch-job"
                  value={jobId}
                  onChange={(e) => setJobId(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="dispatch-technician">Technician ID</Label>
                <Input
                  id="dispatch-technician"
                  value={technicianId}
                  onChange={(e) => setTechnicianId(e.target.value)}
                  required
                />
              </div>

              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? 'Dispatching…' : 'Dispatch Job'}
              </Button>
            </form>

            {submitError && (
              <Alert variant="destructive" role="alert" className="mt-4">
                {submitError}
              </Alert>
            )}
          </CardContent>
        </Card>

        {displaySaga && (
          <Card>
            <CardHeader className="pb-4">
              <CardTitle>Saga state</CardTitle>
              <CardDescription>Live orchestration status for this dispatch.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-neutral-500">ID</span>
                <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">
                  {displaySaga.saga_id}
                </code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-neutral-500">Status</span>
                <SagaStatusBadge status={displaySaga.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-neutral-500">Current step</span>
                <span className="font-medium text-neutral-900">{displaySaga.current_step}</span>
              </div>
              {displaySaga.last_error && (
                <Alert variant="destructive">Last error: {displaySaga.last_error}</Alert>
              )}
              {pollError && (
                <Alert variant="destructive" role="alert">
                  Polling error: {pollError}
                </Alert>
              )}
              <Button variant="outline" size="sm" onClick={refresh}>
                Refresh
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};
