import React, { useEffect, useState } from 'react';
import { listJobs } from '@office-hero/api-client';
import type { AdminJob } from '@office-hero/api-client';

export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async (): Promise<void> => {
      setLoading(true);
      setError(null);

      try {
        const data = await listJobs();
        if (!cancelled) setJobs(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div><h1>Jobs</h1><p>Loading jobs…</p></div>;

  if (error) {
    return (
      <div>
        <h1>Jobs</h1>
        <p role="alert" style={{ color: '#b00020' }}>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Jobs</h1>
      <p style={{ marginBottom: '0.75rem' }}>Live jobs: {jobs.length}</p>

      {jobs.length === 0 ? (
        <p style={{ color: '#666' }}>No jobs found.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Job ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Customer</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Address</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job, index) => (
              <tr key={job.id ?? `job-${String(index)}`}>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{job.id}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{job.customer_name ?? job.customer ?? '—'}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{job.address ?? '—'}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{job.status ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
