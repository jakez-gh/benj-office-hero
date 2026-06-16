import React, { useCallback, useEffect, useState } from 'react';
import {
  listCustomers,
  listLocations,
  listVehicles,
  type AdminVehicle,
  type CustomerSummary,
  type LocationRead,
} from '@office-hero/api-client';
import {
  type ApiError,
  type DispatchResponse,
  type JobCreate,
  type JobListParams,
  type JobStatus,
  type JobSummary,
  type ScheduleOptionItem,
  createJobApi,
  dispatchJobApi,
  getScheduleOptionsApi,
  listJobsApi,
} from '../api';
import { Alert } from '../components/ui/Alert';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { useAutoRecover } from '../hooks/useAutoRecover';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Skeleton } from '../components/ui/Skeleton';
import { JobStatusBadge } from '../components/StatusBadges';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/Table';

const STATUS_FILTER_OPTIONS: Array<{ value: JobStatus | ''; label: string }> = [
  { value: '',            label: 'All statuses' },
  { value: 'pending',     label: 'Pending' },
  { value: 'scheduled',   label: 'Scheduled' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed',   label: 'Completed' },
  { value: 'cancelled',   label: 'Cancelled' },
];

function CreateJobModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (job: JobSummary) => void;
}) {
  const [form, setForm] = useState<JobCreate>({
    customer_id: '',
    location_id: '',
    title: '',
    description: null,
    service_type: null,
    priority: 50,
    estimated_duration_min: 60,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [locations, setLocations] = useState<LocationRead[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listCustomers({ page_size: 100 })
      .then((r) => {
        if (!cancelled) setCustomers(r.items);
      })
      .catch(() => {
        // Customer list is a convenience; creation will still validate server-side.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!form.customer_id) {
      setLocations([]);
      return;
    }
    let cancelled = false;
    setLoadingLocations(true);
    listLocations(form.customer_id)
      .then((r) => {
        if (!cancelled) setLocations(r.items);
      })
      .catch(() => {
        if (!cancelled) setLocations([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingLocations(false);
      });
    return () => {
      cancelled = true;
    };
  }, [form.customer_id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const created = await createJobApi(form);
      onCreated(created);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="New Job" onClose={onClose} busy={submitting}>
        {error && (
          <Alert variant="destructive" className="mb-4">
            {error}
          </Alert>
        )}
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <label htmlFor="job-title" className="mb-1 block text-sm font-medium text-neutral-700">Title *</label>
            <Input
              id="job-title"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="e.g. Fix leaking pipe"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="job-customer" className="mb-1 block text-sm font-medium text-neutral-700">
                Customer *
              </label>
              <select
                id="job-customer"
                className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={form.customer_id}
                onChange={(e) =>
                  setForm((f) => ({ ...f, customer_id: e.target.value, location_id: '' }))
                }
                required
              >
                <option value="">Select a customer…</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="job-location" className="mb-1 block text-sm font-medium text-neutral-700">
                Location *
              </label>
              <select
                id="job-location"
                className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-neutral-50 disabled:text-neutral-400"
                value={form.location_id}
                onChange={(e) => setForm((f) => ({ ...f, location_id: e.target.value }))}
                disabled={!form.customer_id || loadingLocations}
                required
              >
                <option value="">
                  {!form.customer_id
                    ? 'Select a customer first'
                    : loadingLocations
                      ? 'Loading…'
                      : locations.length === 0
                        ? 'No locations on file'
                        : 'Select a location…'}
                </option>
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.label || loc.formatted_address}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-700">Service type</label>
              <Input
                value={form.service_type ?? ''}
                onChange={(e) =>
                  setForm((f) => ({ ...f, service_type: e.target.value || null }))
                }
                placeholder="e.g. Drain cleaning"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-700">Duration (min)</label>
              <Input
                type="number"
                min={5}
                max={1440}
                value={form.estimated_duration_min}
                onChange={(e) =>
                  setForm((f) => ({ ...f, estimated_duration_min: Number(e.target.value) }))
                }
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create job'}
            </Button>
          </div>
        </form>
    </Modal>
  );
}

function tomorrowWindow(): { start: string; end: string } {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const dateStr = `${year}-${month}-${day}`;
  return {
    start: `${dateStr}T08:00`,
    end: `${dateStr}T17:00`,
  };
}

function formatTravel(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem > 0 ? `${h}h ${rem}m` : `${h}h`;
}

function ScheduleModal({
  job,
  onClose,
  onDispatched,
}: {
  job: JobSummary;
  onClose: () => void;
  onDispatched: (result: DispatchResponse) => void;
}) {
  const [windowStart, setWindowStart] = useState(() => tomorrowWindow().start);
  const [windowEnd, setWindowEnd] = useState(() => tomorrowWindow().end);
  const [options, setOptions] = useState<ScheduleOptionItem[] | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [selectedOption, setSelectedOption] = useState<ScheduleOptionItem | null>(null);
  const windowInvalid = windowEnd <= windowStart;
  const [dispatching, setDispatching] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);
  // Manual override — the "fourth option": any vehicle, any time.
  const [manualMode, setManualMode] = useState(false);
  const [vehicles, setVehicles] = useState<AdminVehicle[]>([]);
  const [manualVehicleId, setManualVehicleId] = useState('');
  const [manualTime, setManualTime] = useState(() => tomorrowWindow().start);

  useEffect(() => {
    if (!manualMode || vehicles.length > 0) return;
    let cancelled = false;
    listVehicles()
      .then((v) => {
        if (!cancelled) setVehicles(v);
      })
      .catch(() => {
        // Selection list is a convenience; dispatch validates server-side.
      });
    return () => {
      cancelled = true;
    };
  }, [manualMode, vehicles.length]);

  const fetchOptions = async () => {
    setLoadingOptions(true);
    setOptionsError(null);
    setOptions(null);
    setSelectedOption(null);
    try {
      const resp = await getScheduleOptionsApi(job.id, {
        window_start: new Date(windowStart).toISOString(),
        window_end: new Date(windowEnd).toISOString(),
        max_results: 5,
      });
      setOptions(resp.options);
    } catch (err) {
      const apiErr = err as ApiError;
      setOptionsError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoadingOptions(false);
    }
  };

  const handleDispatch = async () => {
    const payload = manualMode
      ? manualVehicleId && manualTime
        ? { vehicle_id: manualVehicleId, scheduled_for: new Date(manualTime).toISOString() }
        : null
      : selectedOption
        ? {
            vehicle_id: selectedOption.vehicle_id,
            scheduled_for: selectedOption.suggested_start,
            travel_seconds: selectedOption.travel_seconds,
          }
        : null;
    if (!payload) return;
    setDispatching(true);
    setDispatchError(null);
    try {
      const result = await dispatchJobApi(job.id, payload);
      onDispatched(result);
    } catch (err) {
      const apiErr = err as ApiError;
      setDispatchError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setDispatching(false);
    }
  };

  const canConfirm = manualMode ? Boolean(manualVehicleId && manualTime) : Boolean(selectedOption);

  return (
    <Modal
      title="Schedule job"
      subtitle={job.title}
      onClose={onClose}
      busy={dispatching}
      maxWidth="max-w-2xl"
    >
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700">
              Window start
            </label>
            <Input
              type="datetime-local"
              value={windowStart}
              onChange={(e) => setWindowStart(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700">
              Window end
            </label>
            <Input
              type="datetime-local"
              value={windowEnd}
              onChange={(e) => setWindowEnd(e.target.value)}
            />
          </div>
        </div>

        {windowInvalid && (
          <p className="mb-2 text-sm text-red-600">Window end must be after window start.</p>
        )}
        <Button
          type="button"
          variant="outline"
          onClick={() => void fetchOptions()}
          disabled={loadingOptions || windowInvalid}
          className="mb-4 w-full"
        >
          {loadingOptions ? 'Finding options…' : 'Find available slots'}
        </Button>

        {optionsError && (
          <Alert variant="destructive" className="mb-4">
            {optionsError}
          </Alert>
        )}

        {options !== null && (
          <>
            {options.length === 0 ? (
              <p className="mb-4 text-center text-sm text-neutral-500">
                No vehicles available in this window.
              </p>
            ) : (
              <div className="mb-4 space-y-2">
                <p className="text-sm font-medium text-neutral-700">
                  Available slots — pick one:
                </p>
                {options.map((opt) => (
                  <button
                    key={`${opt.vehicle_id}-${opt.suggested_start}`}
                    type="button"
                    onClick={() => setSelectedOption(opt)}
                    className={`w-full rounded-lg border p-3 text-left transition-colors ${
                      selectedOption?.vehicle_id === opt.vehicle_id &&
                        selectedOption?.suggested_start === opt.suggested_start
                        ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500'
                        : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                          #{opt.rank}
                        </span>
                        <span className="ml-2 font-medium text-neutral-900">
                          {opt.vehicle_display}
                        </span>
                      </div>
                      <div className="text-right text-sm text-neutral-500">
                        <span>{formatTravel(opt.travel_seconds)} away</span>
                        <span className="ml-3">
                          {new Date(opt.suggested_start).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        <div className="mb-4 border-t border-neutral-200 pt-3">
          <label className="flex items-center gap-2 text-sm font-medium text-neutral-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
              checked={manualMode}
              onChange={(e) => setManualMode(e.target.checked)}
            />
            Assign manually instead (override suggestions)
          </label>
          {manualMode && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div>
                <label
                  htmlFor="manual-vehicle"
                  className="mb-1 block text-sm font-medium text-neutral-700"
                >
                  Vehicle
                </label>
                <select
                  id="manual-vehicle"
                  className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  value={manualVehicleId}
                  onChange={(e) => setManualVehicleId(e.target.value)}
                >
                  <option value="">Select a vehicle…</option>
                  {vehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name || v.license_plate || v.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="manual-time"
                  className="mb-1 block text-sm font-medium text-neutral-700"
                >
                  Start time
                </label>
                <Input
                  id="manual-time"
                  type="datetime-local"
                  value={manualTime}
                  onChange={(e) => setManualTime(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>

        {dispatchError && (
          <Alert variant="destructive" className="mb-4">
            {dispatchError}
          </Alert>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={dispatching}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!canConfirm || dispatching}
            onClick={() => void handleDispatch()}
          >
            {dispatching ? 'Booking…' : 'Confirm booking'}
          </Button>
        </div>
    </Modal>
  );
}

export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<JobStatus | ''>('');
  const [showCreate, setShowCreate] = useState(false);
  const [scheduleJob, setScheduleJob] = useState<JobSummary | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async (params: JobListParams) => {
    setLoading(true);
    try {
      const data = await listJobsApi(params);
      setJobs(data.items);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void load({
      search: debouncedSearch || undefined,
      status: statusFilter || undefined,
      limit: 50,
    }).then(() => {
      if (cancelled) return;
    });
    return () => {
      cancelled = true;
    };
  }, [debouncedSearch, statusFilter, load]);

  const isNetworkError = !!error && /failed to fetch|network error/i.test(error);
  useAutoRecover(isNetworkError, () => {
    void load({ search: debouncedSearch || undefined, status: statusFilter || undefined, limit: 50 });
  });

  const handleCreated = (job: JobSummary) => {
    setShowCreate(false);
    setJobs((prev) => [job, ...prev]);
    setTotal((t) => t + 1);
  };

  const [loadingMore, setLoadingMore] = useState(false);
  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const data = await listJobsApi({
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
        limit: 50,
        offset: jobs.length,
      });
      setJobs((prev) => [...prev, ...data.items]);
      setTotal(data.total);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Jobs</h1>
          {!loading && (
            <p className="mt-0.5 text-sm text-neutral-500">{total} job{total === 1 ? '' : 's'}</p>
          )}
        </div>
        <Button onClick={() => setShowCreate(true)}>New job</Button>
      </div>

      <div className="mb-4 flex gap-3">
        <Input
          className="max-w-xs"
          placeholder="Search jobs…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Filter by status"
          className="rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as JobStatus | '')}
        >
          {STATUS_FILTER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {error && <ErrorBanner error={error} />}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-300 py-12 text-center">
          <p className="text-neutral-500">No jobs found.</p>
          <Button className="mt-4" variant="ghost" onClick={() => setShowCreate(true)}>
            Create your first job
          </Button>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Service type</TableHead>
              <TableHead>Scheduled</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id} data-testid="job-row">
                <TableCell className="font-medium">{job.title}</TableCell>
                <TableCell>
                  <JobStatusBadge status={job.status} />
                </TableCell>
                <TableCell className="text-neutral-500">{job.service_type ?? '—'}</TableCell>
                <TableCell className="text-neutral-500">
                  {job.scheduled_for
                    ? new Date(job.scheduled_for).toLocaleString()
                    : '—'}
                </TableCell>
                <TableCell className="text-neutral-500">{job.priority}</TableCell>
                <TableCell className="text-right">
                  {job.status === 'pending' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setScheduleJob(job)}
                    >
                      Schedule
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {!loading && jobs.length < total && (
        <div className="mt-4 text-center">
          <Button variant="outline" onClick={() => void loadMore()} disabled={loadingMore}>
            {loadingMore ? 'Loading…' : `Load more (showing ${jobs.length} of ${total})`}
          </Button>
        </div>
      )}

      {showCreate && (
        <CreateJobModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}

      {scheduleJob && (
        <ScheduleModal
          job={scheduleJob}
          onClose={() => setScheduleJob(null)}
          onDispatched={(result) => {
            setScheduleJob(null);
            setJobs((prev) =>
              prev.map((j) =>
                j.id === result.id ? { ...j, status: result.status, scheduled_for: result.scheduled_for } : j,
              ),
            );
          }}
        />
      )}
    </div>
  );
};
