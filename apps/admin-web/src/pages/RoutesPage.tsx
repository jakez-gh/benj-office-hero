import React, { useCallback, useEffect, useState } from 'react';
import { listVehicles, type AdminVehicle } from '@office-hero/api-client';
import {
  type ApiError,
  type RouteRead,
  type RouteStatus,
  type RouteStopStatus,
  cancelRouteApi,
  listRoutesApi,
  resequenceRouteApi,
  startRouteApi,
} from '../api';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';

const ROUTE_STATUS_COLORS: Record<RouteStatus, string> = {
  draft:       'bg-neutral-100 text-neutral-600',
  committed:   'bg-blue-100 text-blue-800',
  in_progress: 'bg-indigo-100 text-indigo-800',
  complete:    'bg-green-100 text-green-800',
  cancelled:   'bg-neutral-100 text-neutral-500',
};

const ROUTE_STATUS_LABELS: Record<RouteStatus, string> = {
  draft:       'Draft',
  committed:   'Committed',
  in_progress: 'In Progress',
  complete:    'Complete',
  cancelled:   'Cancelled',
};

const STOP_STATUS_COLORS: Record<RouteStopStatus, string> = {
  pending:  'bg-amber-100 text-amber-800',
  arrived:  'bg-indigo-100 text-indigo-800',
  complete: 'bg-green-100 text-green-800',
  skipped:  'bg-neutral-100 text-neutral-500',
};

function StatusBadge({ status }: { status: RouteStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROUTE_STATUS_COLORS[status] ?? 'bg-neutral-100 text-neutral-600'}`}
    >
      {ROUTE_STATUS_LABELS[status] ?? status}
    </span>
  );
}

function todayISODate(): string {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

function formatDuration(seconds: number): string {
  if (seconds <= 0) return '—';
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem > 0 ? `${h}h ${rem}m` : `${h}h`;
}

function formatDistance(meters: number): string {
  if (meters <= 0) return '—';
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${meters} m`;
}

function CancelRouteModal({
  route,
  onClose,
  onCancelled,
}: {
  route: RouteRead;
  onClose: () => void;
  onCancelled: (route: RouteRead) => void;
}) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCancel = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const cancelled = await cancelRouteApi(route.id, reason);
      onCancelled(cancelled);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-1 text-lg font-semibold text-neutral-900">Cancel route</h2>
        <p className="mb-4 text-sm text-neutral-500">
          All remaining stops will be skipped and their jobs returned to pending.
        </p>
        {error && (
          <Alert variant="destructive" className="mb-4">
            {error}
          </Alert>
        )}
        <label htmlFor="cancel-reason" className="mb-1 block text-sm font-medium text-neutral-700">
          Reason *
        </label>
        <Input
          id="cancel-reason"
          value={reason}
          maxLength={512}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Technician called in sick"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
            Keep route
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => void handleCancel()}
            disabled={submitting || reason.trim().length < 3}
          >
            {submitting ? 'Cancelling…' : 'Cancel route'}
          </Button>
        </div>
      </div>
    </div>
  );
}

function RouteCard({
  route,
  vehicleName,
  onUpdated,
  onError,
}: {
  route: RouteRead;
  vehicleName: string;
  onUpdated: (route: RouteRead) => void;
  onError: (message: string) => void;
}) {
  // Local working order for the manual override; null = not editing.
  const [order, setOrder] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);
  const [showCancel, setShowCancel] = useState(false);

  const stops = [...route.stops].sort((a, b) => a.sequence_index - b.sequence_index);
  const displayedJobIds = order ?? stops.map((s) => s.job_id);
  const byJobId = new Map(stops.map((s) => [s.job_id, s]));
  const dirty = order !== null && order.join() !== stops.map((s) => s.job_id).join();

  const move = (index: number, delta: number) => {
    const next = [...displayedJobIds];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setOrder(next);
  };

  const saveOrder = async () => {
    if (!order) return;
    setSaving(true);
    try {
      const updated = await resequenceRouteApi(route.id, order);
      setOrder(null);
      onUpdated(updated);
    } catch (err) {
      const apiErr = err as ApiError;
      onError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setSaving(false);
    }
  };

  const start = async () => {
    setStarting(true);
    try {
      onUpdated(await startRouteApi(route.id));
    } catch (err) {
      const apiErr = err as ApiError;
      onError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setStarting(false);
    }
  };

  const reorderable = route.status === 'committed';

  return (
    <Card data-testid="route-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-neutral-900">{vehicleName}</span>
            <StatusBadge status={route.status} />
          </div>
          <p className="mt-0.5 text-sm text-neutral-500">
            {stops.length} stop{stops.length === 1 ? '' : 's'} ·{' '}
            {formatDuration(route.total_duration_s)} travel ·{' '}
            {formatDistance(route.total_distance_m)}
            {route.cancel_reason ? ` · ${route.cancel_reason}` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          {route.status === 'committed' && (
            <>
              <Button size="sm" onClick={() => void start()} disabled={starting || dirty}>
                {starting ? 'Starting…' : 'Start route'}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowCancel(true)}>
                Cancel
              </Button>
            </>
          )}
          {route.status === 'in_progress' && (
            <Button size="sm" variant="ghost" onClick={() => setShowCancel(true)}>
              Cancel
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ol className="space-y-1.5">
          {displayedJobIds.map((jobId, i) => {
            const stop = byJobId.get(jobId);
            if (!stop) return null;
            return (
              <li
                key={jobId}
                data-testid="route-stop"
                className="flex items-center justify-between rounded-md border border-neutral-200 px-3 py-2"
              >
                <div className="flex items-center gap-3">
                  <span className="w-6 text-center text-sm font-semibold text-neutral-400">
                    {i + 1}
                  </span>
                  <div>
                    <span className="font-mono text-xs text-neutral-500">
                      Job {jobId.slice(0, 8)}
                    </span>
                    <span
                      className={`ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STOP_STATUS_COLORS[stop.status] ?? ''}`}
                    >
                      {stop.status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm text-neutral-500">
                  {stop.planned_eta && (
                    <span>
                      {new Date(stop.planned_eta).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  )}
                  {reorderable && (
                    <span className="flex gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        aria-label={`Move stop ${i + 1} up`}
                        disabled={i === 0 || saving}
                        onClick={() => move(i, -1)}
                      >
                        ↑
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        aria-label={`Move stop ${i + 1} down`}
                        disabled={i === displayedJobIds.length - 1 || saving}
                        onClick={() => move(i, 1)}
                      >
                        ↓
                      </Button>
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
        {dirty && (
          <div className="mt-3 flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setOrder(null)} disabled={saving}>
              Discard order
            </Button>
            <Button size="sm" onClick={() => void saveOrder()} disabled={saving}>
              {saving ? 'Saving…' : 'Save new order'}
            </Button>
          </div>
        )}
      </CardContent>
      {showCancel && (
        <CancelRouteModal
          route={route}
          onClose={() => setShowCancel(false)}
          onCancelled={(cancelled) => {
            setShowCancel(false);
            onUpdated(cancelled);
          }}
        />
      )}
    </Card>
  );
}

export const RoutesPage: React.FC = () => {
  const [workDate, setWorkDate] = useState(() => todayISODate());
  const [routes, setRoutes] = useState<RouteRead[]>([]);
  const [vehicles, setVehicles] = useState<AdminVehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listVehicles()
      .then((v) => {
        if (!cancelled) setVehicles(v);
      })
      .catch(() => {
        // Vehicle names are display sugar; IDs still render.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const load = useCallback(async (date: string) => {
    setLoading(true);
    try {
      const data = await listRoutesApi(date);
      setRoutes(data.items);
      setError(null);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(workDate);
  }, [workDate, load]);

  const vehicleName = (vehicleId: string): string => {
    const v = vehicles.find((x) => x.id === vehicleId);
    return v?.name || v?.license_plate || `Vehicle ${vehicleId.slice(0, 8)}`;
  };

  const replaceRoute = (updated: RouteRead) => {
    setRoutes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Routes</h1>
          {!loading && (
            <p className="mt-0.5 text-sm text-neutral-500">
              {routes.length} route{routes.length === 1 ? '' : 's'} on{' '}
              {new Date(`${workDate}T00:00:00`).toLocaleDateString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="route-date" className="text-sm font-medium text-neutral-700">
            Date
          </label>
          <Input
            id="route-date"
            type="date"
            className="w-44"
            value={workDate}
            onChange={(e) => setWorkDate(e.target.value)}
          />
          <Button variant="outline" onClick={() => void load(workDate)} disabled={loading}>
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          {error}
        </Alert>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : routes.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-300 py-12 text-center">
          <p className="text-neutral-500">
            No routes for this date. Dispatch a job from the Jobs page to create one.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {routes.map((route) => (
            <RouteCard
              key={route.id}
              route={route}
              vehicleName={vehicleName(route.vehicle_id)}
              onUpdated={replaceRoute}
              onError={setError}
            />
          ))}
        </div>
      )}
    </div>
  );
};
