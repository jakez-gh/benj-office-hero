import React, { useCallback, useEffect, useState } from 'react';
import { listVehicles } from '@office-hero/api-client';
import type { AdminVehicle } from '@office-hero/api-client';
import { Button } from '../components/ui/Button';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { useAutoRecover } from '../hooks/useAutoRecover';
import { Skeleton } from '../components/ui/Skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/Table';

/** Derive a display name from make/model when `name` is absent. */
function vehicleDisplayName(v: AdminVehicle): string {
  if (v.name) return v.name;
  const parts = [v.make, v.model].filter(Boolean);
  return parts.length > 0 ? parts.join(' ') : '—';
}

const STATUS_COLORS: Record<string, string> = {
  active:      'bg-green-100 text-green-800',
  idle:        'bg-neutral-100 text-neutral-600',
  maintenance: 'bg-amber-100 text-amber-800',
  archived:    'bg-neutral-100 text-neutral-500',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status] ?? 'bg-neutral-100 text-neutral-600'}`}
    >
      {status}
    </span>
  );
}

export const VehiclesPage: React.FC = () => {
  const [vehicles, setVehicles] = useState<AdminVehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewHint, setShowNewHint] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await listVehicles();
      setVehicles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const isNetworkError = !!error && /failed to fetch|network error/i.test(error);
  useAutoRecover(isNetworkError, () => void load());

  if (loading) {
    return (
      <div>
        <h1 className="mb-6 text-2xl font-semibold text-neutral-900">Vehicles</h1>
        <p className="sr-only">Loading vehicles…</p>
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Vehicles</h1>
          {!loading && !error && (
            <p className="mt-0.5 text-sm text-neutral-500">Live vehicles: {vehicles.length}</p>
          )}
        </div>
        <Button onClick={() => setShowNewHint(v => !v)}>New Vehicle</Button>
      </div>
      {showNewHint && (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          Vehicle creation is managed via the backend API. Contact your administrator to add new vehicles.
        </p>
      )}

      {error && <ErrorBanner error={error} />}

      {vehicles.length === 0 && !loading && (
        <div className="rounded-lg border border-dashed border-neutral-300 py-12 text-center">
          <p className="text-neutral-500">
            {error ? 'Vehicles could not be loaded.' : 'No vehicles on record.'}
          </p>
        </div>
      )}

      {vehicles.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Vehicle ID</TableHead>
              <TableHead>Vehicle</TableHead>
              <TableHead>License Plate</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {vehicles.map((vehicle, index) => (
              <TableRow key={vehicle.id ?? `vehicle-${String(index)}`}>
                <TableCell className="max-w-[10rem] truncate font-mono text-xs text-neutral-400">
                  {vehicle.id}
                </TableCell>
                <TableCell className="font-medium">{vehicleDisplayName(vehicle)}</TableCell>
                <TableCell className="text-neutral-500">{vehicle.license_plate ?? '—'}</TableCell>
                <TableCell>
                  {vehicle.status ? <StatusBadge status={vehicle.status} /> : '—'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
};
