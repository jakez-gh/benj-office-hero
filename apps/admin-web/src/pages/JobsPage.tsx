import React, { useCallback, useEffect, useState } from 'react';
import {
  type ApiError,
  type JobCreate,
  type JobListParams,
  type JobStatus,
  type JobSummary,
  createJobApi,
  listJobsApi,
} from '../api';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/Table';

const STATUS_COLORS: Record<JobStatus, string> = {
  pending:     'bg-amber-100 text-amber-800',
  scheduled:   'bg-blue-100 text-blue-800',
  in_progress: 'bg-indigo-100 text-indigo-800',
  completed:   'bg-green-100 text-green-800',
  cancelled:   'bg-neutral-100 text-neutral-500',
};

const STATUS_LABELS: Record<JobStatus, string> = {
  pending:     'Pending',
  scheduled:   'Scheduled',
  in_progress: 'In Progress',
  completed:   'Completed',
  cancelled:   'Cancelled',
};

function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status] ?? 'bg-neutral-100 text-neutral-600'}`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-neutral-900">New Job</h2>
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
              <label className="mb-1 block text-sm font-medium text-neutral-700">Customer ID *</label>
              <Input
                value={form.customer_id}
                onChange={(e) => setForm((f) => ({ ...f, customer_id: e.target.value }))}
                placeholder="UUID"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-700">Location ID *</label>
              <Input
                value={form.location_id}
                onChange={(e) => setForm((f) => ({ ...f, location_id: e.target.value }))}
                placeholder="UUID"
                required
              />
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
      </div>
    </div>
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

  const handleCreated = (job: JobSummary) => {
    setShowCreate(false);
    setJobs((prev) => [job, ...prev]);
    setTotal((t) => t + 1);
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

      {error && (
        <Alert variant="destructive" className="mb-4" role="alert">
          {error}
        </Alert>
      )}

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
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id} data-testid="job-row">
                <TableCell className="font-medium">{job.title}</TableCell>
                <TableCell>
                  <StatusBadge status={job.status} />
                </TableCell>
                <TableCell className="text-neutral-500">{job.service_type ?? '—'}</TableCell>
                <TableCell className="text-neutral-500">
                  {job.scheduled_for
                    ? new Date(job.scheduled_for).toLocaleString()
                    : '—'}
                </TableCell>
                <TableCell className="text-neutral-500">{job.priority}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {showCreate && (
        <CreateJobModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
    </div>
  );
};
