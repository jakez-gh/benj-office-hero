import React, { useEffect, useState } from 'react';
import { listVehicles } from '@office-hero/api-client';
import type { AdminVehicle } from '@office-hero/api-client';

/** Derive a display name from make/model when `name` is absent. */
function vehicleDisplayName(v: AdminVehicle): string {
  if (v.name) return v.name;
  const parts = [v.make, v.model].filter(Boolean);
  return parts.length > 0 ? parts.join(' ') : '—';
}

export const VehiclesPage: React.FC = () => {
  const [vehicles, setVehicles] = useState<AdminVehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async (): Promise<void> => {
      setLoading(true);
      setError(null);

      try {
        const data = await listVehicles();
        if (!cancelled) setVehicles(data);
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

  if (loading) return <div><h1>Vehicles</h1><p>Loading vehicles…</p></div>;

  if (error) {
    return (
      <div>
        <h1>Vehicles</h1>
        <p role="alert" style={{ color: '#b00020' }}>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Vehicles</h1>
      <p style={{ marginBottom: '0.75rem' }}>Live vehicles: {vehicles.length}</p>

      {vehicles.length === 0 ? (
        <p style={{ color: '#666' }}>No vehicles found.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Vehicle ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Vehicle</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>License Plate</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.map((vehicle, index) => (
              <tr key={vehicle.id ?? `vehicle-${String(index)}`}>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{vehicle.id}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{vehicleDisplayName(vehicle)}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{vehicle.license_plate ?? '—'}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{vehicle.status ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
