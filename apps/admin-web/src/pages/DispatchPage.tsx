import React, { useEffect, useState } from 'react';
import { listRoutes } from '@office-hero/api-client';
import type { AdminRoute } from '@office-hero/api-client';

export const DispatchPage: React.FC = () => {
  const [routes, setRoutes] = useState<AdminRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async (): Promise<void> => {
      setLoading(true);
      setError(null);

      try {
        const data = await listRoutes();
        if (!cancelled) setRoutes(data);
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

  if (loading) return <div><h1>Dispatch</h1><p>Loading routes…</p></div>;

  if (error) {
    return (
      <div>
        <h1>Dispatch</h1>
        <p role="alert" style={{ color: '#b00020' }}>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Dispatch</h1>
      <p style={{ marginBottom: '0.75rem' }}>Live routes: {routes.length}</p>

      {routes.length === 0 ? (
        <p style={{ color: '#666' }}>No dispatch routes found.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Route ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Vehicle</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Technician</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((route, index) => (
              <tr key={route.id ?? `route-${String(index)}`}>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{route.id}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{route.vehicle_id ?? '—'}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{route.technician_id ?? '—'}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{route.status ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
