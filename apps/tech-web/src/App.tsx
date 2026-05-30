import React, { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  type JobSummary,
  type JobCreatePayload,
  type LoginResponse,
  completeJobApi,
  createJobApi,
  getToken,
  listJobsApi,
  loginApi,
  myCrewTodayApi,
  setToken,
  startJobApi,
} from './api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function fmtErr(e: unknown): string {
  if (e instanceof ApiError) return e.detail;
  if (e instanceof Error) return e.message;
  return String(e);
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending', scheduled: 'Scheduled', in_progress: 'In Progress',
  completed: 'Completed', cancelled: 'Cancelled',
};

function Badge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status] ?? status}</span>;
}

// ---------------------------------------------------------------------------
// Login view
// ---------------------------------------------------------------------------

function LoginView({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp: LoginResponse = await loginApi(email, password);
      onLogin(resp.access_token);
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="screen" style={{ paddingTop: 48 }}>
      <h1 style={{ textAlign: 'center', marginBottom: 24, fontSize: 22 }}>Office Hero</h1>
      <div className="card">
        <h2 style={{ margin: '0 0 16px', fontSize: 17 }}>Technician sign in</h2>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Job detail view
// ---------------------------------------------------------------------------

function JobDetailView({ job, onBack, onUpdate }: {
  job: JobSummary;
  onBack: () => void;
  onUpdate: (j: JobSummary) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    setLoading(true); setError(null);
    try { onUpdate(await startJobApi(job.id)); }
    catch (err) { setError(fmtErr(err)); }
    finally { setLoading(false); }
  }

  async function handleComplete() {
    setLoading(true); setError(null);
    try { onUpdate(await completeJobApi(job.id)); }
    catch (err) { setError(fmtErr(err)); }
    finally { setLoading(false); }
  }

  return (
    <>
      <div className="header">
        <button className="btn btn-secondary btn-sm" onClick={onBack}>← Back</button>
        <h1>Job details</h1>
        <span />
      </div>
      <div className="screen">
        {error && <div className="alert alert-error">{error}</div>}
        <div className="card">
          <div style={{ marginBottom: 8 }}><Badge status={job.status} /></div>
          <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>{job.title}</h2>
          {job.service_type && <p style={{ margin: '0 0 12px', color: '#6b7280', fontSize: 14 }}>{job.service_type}</p>}
          <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
            <tbody>
              {[
                ['Scheduled', fmtTime(job.scheduled_for)],
                ['Duration', `${job.estimated_duration_min} min`],
                ['Priority', String(job.priority)],
                ['Customer ID', job.customer_id.slice(0, 8) + '…'],
                ['Location ID', job.location_id.slice(0, 8) + '…'],
              ].map(([k, v]) => (
                <tr key={k}>
                  <td style={{ padding: '4px 0', color: '#6b7280', width: 110 }}>{k}</td>
                  <td style={{ padding: '4px 0', fontWeight: 500 }}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {job.status === 'scheduled' && (
          <button className="btn btn-primary btn-full" onClick={() => void handleStart()} disabled={loading}>
            {loading ? 'Starting…' : 'Mark in progress'}
          </button>
        )}
        {job.status === 'in_progress' && (
          <button className="btn btn-success btn-full" onClick={() => void handleComplete()} disabled={loading}>
            {loading ? 'Completing…' : 'Mark complete'}
          </button>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// New job form
// ---------------------------------------------------------------------------

function NewJobView({ onBack, onCreated }: { onBack: () => void; onCreated: (j: JobSummary) => void }) {
  const [form, setForm] = useState<JobCreatePayload>({
    customer_id: '', location_id: '', title: '', service_type: null, estimated_duration_min: 60,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError(null);
    try { onCreated(await createJobApi(form)); }
    catch (err) { setError(fmtErr(err)); }
    finally { setLoading(false); }
  }

  return (
    <>
      <div className="header">
        <button className="btn btn-secondary btn-sm" onClick={onBack}>← Back</button>
        <h1>New job</h1>
        <span />
      </div>
      <div className="screen">
        {error && <div className="alert alert-error">{error}</div>}
        <div className="card">
          <form onSubmit={(e) => void handleSubmit(e)}>
            {(['title', 'customer_id', 'location_id'] as const).map((key) => (
              <div className="field" key={key}>
                <label htmlFor={key}>{key === 'title' ? 'Job title *' : key === 'customer_id' ? 'Customer ID *' : 'Location ID *'}</label>
                <input
                  id={key} type="text" required
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                />
              </div>
            ))}
            <div className="field">
              <label htmlFor="service_type">Service type</label>
              <input
                id="service_type" type="text"
                value={form.service_type ?? ''}
                onChange={e => setForm(f => ({ ...f, service_type: e.target.value || null }))}
              />
            </div>
            <div className="field">
              <label htmlFor="duration">Duration (min)</label>
              <input id="duration" type="number" min={5} max={1440}
                value={form.estimated_duration_min}
                onChange={e => setForm(f => ({ ...f, estimated_duration_min: Number(e.target.value) }))}
              />
            </div>
            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? 'Creating…' : 'Create job'}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Today view
// ---------------------------------------------------------------------------

function TodayView({ vehicleId, workDate, onLogout }: { vehicleId: string; workDate: string; onLogout: () => void }) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobSummary | null>(null);
  const [showNew, setShowNew] = useState(false);

  const loadJobs = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await listJobsApi({ assigned_vehicle_id: vehicleId, scheduled_for_date: workDate });
      setJobs(data.items.slice().sort((a, b) => {
        if (!a.scheduled_for) return 1;
        if (!b.scheduled_for) return -1;
        return a.scheduled_for.localeCompare(b.scheduled_for);
      }));
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setLoading(false);
    }
  }, [vehicleId, workDate]);

  useEffect(() => { void loadJobs(); }, [loadJobs]);

  if (selectedJob) {
    return (
      <JobDetailView
        job={selectedJob}
        onBack={() => setSelectedJob(null)}
        onUpdate={(updated) => {
          setJobs(prev => prev.map(j => j.id === updated.id ? updated : j));
          setSelectedJob(updated);
        }}
      />
    );
  }

  if (showNew) {
    return (
      <NewJobView
        onBack={() => setShowNew(false)}
        onCreated={(j) => {
          setJobs(prev => [...prev, j]);
          setShowNew(false);
        }}
      />
    );
  }

  return (
    <>
      <div className="header">
        <h1>My jobs today</h1>
        <button className="btn btn-secondary btn-sm" onClick={onLogout}>Sign out</button>
      </div>
      <div className="screen">
        {error && <div className="alert alert-error">{error}</div>}
        {loading ? (
          <div className="empty">Loading…</div>
        ) : jobs.length === 0 ? (
          <div className="empty">
            <p>No jobs assigned today.</p>
            <button className="btn btn-secondary" onClick={() => setShowNew(true)}>Enter a job</button>
          </div>
        ) : (
          <>
            {jobs.map(job => (
              <div
                key={job.id}
                className="card"
                style={{ cursor: 'pointer' }}
                onClick={() => setSelectedJob(job)}
              >
                <div className="job-row">
                  <span className="job-row-time">{fmtTime(job.scheduled_for)}</span>
                  <div className="job-row-body">
                    <div className="job-row-title">{job.title}</div>
                    <div className="job-row-sub">{job.service_type ?? '—'}</div>
                  </div>
                  <Badge status={job.status} />
                </div>
              </div>
            ))}
            <button className="btn btn-secondary btn-full" style={{ marginTop: 8 }} onClick={() => setShowNew(true)}>
              + Enter a job
            </button>
          </>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Root App
// ---------------------------------------------------------------------------

type View =
  | { kind: 'login' }
  | { kind: 'loading' }
  | { kind: 'today'; vehicleId: string; workDate: string }
  | { kind: 'no-crew' }
  | { kind: 'error'; message: string };

export default function App() {
  const [view, setView] = useState<View>(getToken() ? { kind: 'loading' } : { kind: 'login' });

  useEffect(() => {
    if (view.kind !== 'loading') return;
    myCrewTodayApi()
      .then(c => setView({ kind: 'today', vehicleId: c.vehicle_id, workDate: c.work_date }))
      .catch(err => {
        const status = err instanceof ApiError ? err.status : 0;
        if (status === 401 || status === 403) {
          setToken(null);
          setView({ kind: 'login' });
        } else if (status === 404) {
          setView({ kind: 'no-crew' });
        } else {
          setView({ kind: 'error', message: fmtErr(err) });
        }
      });
  }, [view.kind]);

  function handleLogin(token: string) {
    setToken(token);
    setView({ kind: 'loading' });
  }

  function handleLogout() {
    setToken(null);
    setView({ kind: 'login' });
  }

  if (view.kind === 'login') return <LoginView onLogin={handleLogin} />;
  if (view.kind === 'loading') return <div className="empty" style={{ paddingTop: 80 }}>Loading…</div>;

  if (view.kind === 'error') {
    return (
      <div className="screen" style={{ paddingTop: 48 }}>
        <div className="alert alert-error">{view.message}</div>
        <button className="btn btn-secondary" onClick={handleLogout}>Sign out</button>
      </div>
    );
  }

  if (view.kind === 'no-crew') {
    return (
      <div className="screen" style={{ paddingTop: 48, textAlign: 'center' }}>
        <div className="card">
          <p style={{ marginBottom: 16 }}>No vehicle assignment found for today.</p>
          <button className="btn btn-secondary" onClick={handleLogout}>Sign out</button>
        </div>
      </div>
    );
  }

  return <TodayView vehicleId={view.vehicleId} workDate={view.workDate} onLogout={handleLogout} />;
}
