/**
 * DispatchPage — dispatch a pending job via the back-office saga API.
 *
 * Jobs and technicians are loaded from the API and presented as searchable
 * dropdowns. Tenant ID is read from the session automatically.
 * After submission the live saga state is shown with step-by-step status.
 */

import React, { useContext, useEffect, useState } from 'react';
import { listUsers } from '@office-hero/api-client';
import type { AdminUser } from '@office-hero/api-client';
import { type ApiError, type SagaState, type JobSummary, createSaga, listJobsApi } from '../api';
import { AuthContext } from '../auth';
import { SagaStatusBadge } from '../components/SagaStatusBadge';
import { useSagaStatus } from '../hooks/useSagaStatus';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';
import { Skeleton } from '../components/ui/Skeleton';

const SELECT_CLASS =
  'block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-neutral-50 disabled:text-neutral-400';

export const DispatchPage: React.FC = () => {
  const { user } = useContext(AuthContext);

  // Resolved tenant ID: from auth user, localStorage (demo mode), or empty.
  const tenantId =
    (user as { tenant_id?: string } | null)?.tenant_id ??
    localStorage.getItem('tenant_id') ??
    '';

  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [technicians, setTechnicians] = useState<AdminUser[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  const [jobSearch, setJobSearch] = useState('');
  const [selectedJobId, setSelectedJobId] = useState('');
  const [selectedTechnicianId, setSelectedTechnicianId] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [submittedSaga, setSubmittedSaga] = useState<SagaState | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [optionsRetryKey, setOptionsRetryKey] = useState(0);

  const { saga: liveSaga, error: pollError, refresh } = useSagaStatus(
    submittedSaga?.saga_id ?? null
  );
  const displaySaga: SagaState | null = liveSaga ?? submittedSaga;

  // Load pending jobs and technicians; re-runs when optionsRetryKey increments.
  useEffect(() => {
    let cancelled = false;
    setLoadingOptions(true);
    setOptionsError(null);

    Promise.all([
      listJobsApi({ status: 'pending', limit: 100 }),
      listUsers(),
    ])
      .then(([jobsResp, usersResp]) => {
        if (cancelled) return;
        setJobs(jobsResp.items);
        setTechnicians(
          usersResp.filter((u) =>
            ['technician', 'tech'].includes(u.role?.toLowerCase() ?? '')
          )
        );
      })
      .catch((err) => {
        if (!cancelled) setOptionsError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoadingOptions(false);
      });

    return () => { cancelled = true; };
  }, [optionsRetryKey]);

  const filteredJobs = jobSearch
    ? jobs.filter((j) => j.title.toLowerCase().includes(jobSearch.toLowerCase()))
    : jobs;

  const selectedJob = jobs.find((j) => j.id === selectedJobId) ?? null;
  const selectedTech = technicians.find((t) => t.id === selectedTechnicianId) ?? null;

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (!selectedJobId) return;
    setSubmitting(true);
    setSubmitError(null);
    setSubmittedSaga(null);

    try {
      const saga = await createSaga({
        saga_type: 'dispatch_job',
        context: {
          tenant_id: tenantId,
          job_id: selectedJobId,
          technician_id: selectedTechnicianId || undefined,
        },
      });
      setSubmittedSaga(saga);
    } catch (err) {
      const apiErr = err as ApiError;
      setSubmitError(apiErr?.detail || (err instanceof Error ? err.message : String(err)));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">Dispatch</h1>
        <p className="mt-0.5 text-sm text-neutral-500">
          Assign a pending job to a technician and track the orchestration live.
        </p>
      </div>

      <div className="grid max-w-4xl gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-4">
            <CardTitle>Job details</CardTitle>
            <CardDescription>
              Select a pending job and assign a technician to dispatch it.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingOptions ? (
              <div className="space-y-3">
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : optionsError ? (
              <div className="space-y-3">
                <Alert variant="destructive">
                  Could not load jobs — {optionsError}
                </Alert>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOptionsRetryKey((k) => k + 1)}
                >
                  Retry
                </Button>
              </div>
            ) : (
              <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
                {/* Job selector with inline search */}
                <div className="space-y-1.5">
                  <Label htmlFor="dispatch-job-search">Search jobs</Label>
                  <Input
                    id="dispatch-job-search"
                    placeholder="Filter by title or customer…"
                    value={jobSearch}
                    onChange={(e) => {
                      setJobSearch(e.target.value);
                      setSelectedJobId('');
                    }}
                  />
                  <select
                    aria-label="Select job"
                    className={SELECT_CLASS}
                    size={Math.min(filteredJobs.length + 1, 6)}
                    value={selectedJobId}
                    onChange={(e) => setSelectedJobId(e.target.value)}
                    required
                  >
                    <option value="">— pick a job —</option>
                    {filteredJobs.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.title}
                      </option>
                    ))}
                    {filteredJobs.length === 0 && (
                      <option value="" disabled>
                        No pending jobs match
                      </option>
                    )}
                  </select>
                </div>

                {/* Selected job summary */}
                {selectedJob && (
                  <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm">
                    <p className="font-medium text-neutral-900">{selectedJob.title}</p>
                    {selectedJob.service_type && (
                      <p className="text-neutral-400">{selectedJob.service_type}</p>
                    )}
                  </div>
                )}

                {/* Technician selector */}
                <div className="space-y-1.5">
                  <Label htmlFor="dispatch-technician">
                    Technician{' '}
                    <span className="font-normal text-neutral-400">(optional)</span>
                  </Label>
                  <select
                    id="dispatch-technician"
                    aria-label="Select technician"
                    className={SELECT_CLASS}
                    value={selectedTechnicianId}
                    onChange={(e) => setSelectedTechnicianId(e.target.value)}
                  >
                    <option value="">— assign later —</option>
                    {technicians.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.full_name ?? t.email}
                      </option>
                    ))}
                    {technicians.length === 0 && (
                      <option value="" disabled>
                        No technicians found
                      </option>
                    )}
                  </select>
                </div>

                {selectedTech && (
                  <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm">
                    <p className="font-medium text-neutral-900">
                      {selectedTech.full_name ?? selectedTech.email}
                    </p>
                    <p className="capitalize text-neutral-500">{selectedTech.role}</p>
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={submitting || !selectedJobId}
                  className="w-full"
                >
                  {submitting ? 'Dispatching…' : 'Dispatch Job'}
                </Button>

                {submitError && (
                  <Alert variant="destructive" role="alert" className="mt-2">
                    {submitError}
                  </Alert>
                )}
              </form>
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
                <span className="text-neutral-500">Status</span>
                <SagaStatusBadge status={displaySaga.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-neutral-500">Step</span>
                <span className="font-medium text-neutral-900">{displaySaga.current_step}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-neutral-500">Saga ID</span>
                <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">
                  {displaySaga.saga_id}
                </code>
              </div>
              {displaySaga.status === 'done' && (
                <Alert variant="success">
                  Job dispatched — view it on the{' '}
                  <a href="/routes" className="underline">
                    Routes
                  </a>{' '}
                  page.
                </Alert>
              )}
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
