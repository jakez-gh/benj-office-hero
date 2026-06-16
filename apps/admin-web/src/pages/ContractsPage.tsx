import React, { useCallback, useEffect, useState } from 'react';
import {
  listCustomers,
  listLocations,
  type CustomerSummary,
  type LocationRead,
} from '@office-hero/api-client';
import {
  type ApiError,
  type ContractCreate,
  type ContractFrequency,
  type ContractListParams,
  type ContractRead,
  type ContractStatus,
  type ContractSummary,
  createContractApi,
  endContractApi,
  generateContractJobsApi,
  listContractsApi,
  pauseContractApi,
  resumeContractApi,
} from '../api';
import { Alert } from '../components/ui/Alert';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { useAutoRecover } from '../hooks/useAutoRecover';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Skeleton } from '../components/ui/Skeleton';
import { ContractStatusBadge } from '../components/StatusBadges';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/Table';

const FREQUENCY_LABELS: Record<ContractFrequency, string> = {
  weekly:     'Weekly',
  biweekly:   'Every 2 weeks',
  monthly:    'Monthly',
  quarterly:  'Quarterly',
  semiannual: 'Twice a year',
  annual:     'Yearly',
};

const STATUS_FILTER_OPTIONS: Array<{ value: ContractStatus | ''; label: string }> = [
  { value: '',       label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'ended',  label: 'Ended' },
];

function todayISODate(): string {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

function CreateContractModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (contract: ContractRead) => void;
}) {
  const [form, setForm] = useState<ContractCreate>({
    customer_id: '',
    location_id: '',
    title: '',
    description: null,
    service_type: null,
    priority: 50,
    estimated_duration_min: 60,
    frequency: 'monthly',
    start_date: todayISODate(),
    end_date: null,
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
      const created = await createContractApi(form);
      onCreated(created);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="New Contract" onClose={onClose} busy={submitting}>
        {error && (
          <Alert variant="destructive" className="mb-4">
            {error}
          </Alert>
        )}
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <label htmlFor="contract-title" className="mb-1 block text-sm font-medium text-neutral-700">
              Title *
            </label>
            <Input
              id="contract-title"
              value={form.title}
              maxLength={255}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="e.g. Quarterly pest control plan"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="contract-customer" className="mb-1 block text-sm font-medium text-neutral-700">
                Customer *
              </label>
              <select
                id="contract-customer"
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
              <label htmlFor="contract-location" className="mb-1 block text-sm font-medium text-neutral-700">
                Location *
              </label>
              <select
                id="contract-location"
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
              <label htmlFor="contract-frequency" className="mb-1 block text-sm font-medium text-neutral-700">
                Frequency *
              </label>
              <select
                id="contract-frequency"
                className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={form.frequency}
                onChange={(e) =>
                  setForm((f) => ({ ...f, frequency: e.target.value as ContractFrequency }))
                }
                required
              >
                {(Object.keys(FREQUENCY_LABELS) as ContractFrequency[]).map((freq) => (
                  <option key={freq} value={freq}>
                    {FREQUENCY_LABELS[freq]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="contract-service-type" className="mb-1 block text-sm font-medium text-neutral-700">
                Service type
              </label>
              <Input
                id="contract-service-type"
                value={form.service_type ?? ''}
                maxLength={120}
                onChange={(e) =>
                  setForm((f) => ({ ...f, service_type: e.target.value || null }))
                }
                placeholder="e.g. Pest inspection"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="contract-start" className="mb-1 block text-sm font-medium text-neutral-700">
                First visit *
              </label>
              <Input
                id="contract-start"
                type="date"
                value={form.start_date}
                onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                required
              />
            </div>
            <div>
              <label htmlFor="contract-end" className="mb-1 block text-sm font-medium text-neutral-700">
                Ends (optional)
              </label>
              <Input
                id="contract-end"
                type="date"
                value={form.end_date ?? ''}
                min={form.start_date}
                onChange={(e) =>
                  setForm((f) => ({ ...f, end_date: e.target.value || null }))
                }
              />
            </div>
          </div>
          <div>
            <label htmlFor="contract-duration" className="mb-1 block text-sm font-medium text-neutral-700">
              Visit duration (min)
            </label>
            <Input
              id="contract-duration"
              type="number"
              min={5}
              max={1440}
              value={form.estimated_duration_min}
              onChange={(e) =>
                setForm((f) => ({ ...f, estimated_duration_min: Number(e.target.value) }))
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create contract'}
            </Button>
          </div>
        </form>
    </Modal>
  );
}

function EndContractModal({
  contract,
  onClose,
  onEnded,
}: {
  contract: ContractSummary;
  onClose: () => void;
  onEnded: (contract: ContractRead) => void;
}) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEnd = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const ended = await endContractApi(contract.id, reason || undefined);
      onEnded(ended);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="End contract"
      subtitle={`“${contract.title}” will stop generating jobs. This cannot be undone.`}
      onClose={onClose}
      busy={submitting}
      maxWidth="max-w-md"
    >
        {error && (
          <Alert variant="destructive" className="mb-4">
            {error}
          </Alert>
        )}
        <label htmlFor="end-reason" className="mb-1 block text-sm font-medium text-neutral-700">
          Reason (optional)
        </label>
        <Input
          id="end-reason"
          value={reason}
          maxLength={512}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Customer moved away"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => void handleEnd()}
            disabled={submitting}
          >
            {submitting ? 'Ending…' : 'End contract'}
          </Button>
        </div>
    </Modal>
  );
}

export const ContractsPage: React.FC = () => {
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ContractStatus | ''>('');
  const [showCreate, setShowCreate] = useState(false);
  const [endTarget, setEndTarget] = useState<ContractSummary | null>(null);
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async (params: ContractListParams) => {
    setLoading(true);
    try {
      const data = await listContractsApi(params);
      setContracts(data.items);
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
    void load({
      search: debouncedSearch || undefined,
      status: statusFilter || undefined,
      limit: 50,
    });
  }, [debouncedSearch, statusFilter, load]);

  const isNetworkError = !!error && /failed to fetch|network error/i.test(error);
  useAutoRecover(isNetworkError, () => {
    void load({ search: debouncedSearch || undefined, status: statusFilter || undefined, limit: 50 });
  });

  const replaceRow = (updated: ContractRead) => {
    setContracts((prev) =>
      prev.map((c) =>
        c.id === updated.id
          ? { ...c, status: updated.status, next_due: updated.next_due }
          : c,
      ),
    );
  };

  const handlePauseResume = async (contract: ContractSummary) => {
    setRowBusy(contract.id);
    setError(null);
    try {
      const updated =
        contract.status === 'active'
          ? await pauseContractApi(contract.id)
          : await resumeContractApi(contract.id);
      replaceRow(updated);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setRowBusy(null);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setGenerateResult(null);
    setError(null);
    try {
      const result = await generateContractJobsApi();
      setGenerateResult(
        result.count === 0
          ? 'No visits due — nothing to generate.'
          : `Created ${result.count} job${result.count === 1 ? '' : 's'} from due contracts. Find them under Jobs.`,
      );
      // next_due moved forward on generated contracts — refresh the list.
      void load({
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
        limit: 50,
      });
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail ?? (err instanceof Error ? err.message : String(err)));
    } finally {
      setGenerating(false);
    }
  };

  const handleCreated = (contract: ContractRead) => {
    setShowCreate(false);
    setContracts((prev) => [
      {
        id: contract.id,
        title: contract.title,
        status: contract.status,
        frequency: contract.frequency,
        next_due: contract.next_due,
        end_date: contract.end_date,
        customer_id: contract.customer_id,
        location_id: contract.location_id,
        industry: contract.industry,
        service_type: contract.service_type,
        priority: contract.priority,
      },
      ...prev,
    ]);
    setTotal((t) => t + 1);
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Contracts</h1>
          {!loading && (
            <p className="mt-0.5 text-sm text-neutral-500">
              {total} contract{total === 1 ? '' : 's'}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            variant="outline"
            onClick={() => void handleGenerate()}
            disabled={generating}
          >
            {generating ? 'Generating…' : 'Generate due jobs'}
          </Button>
          <Button onClick={() => setShowCreate(true)}>New contract</Button>
        </div>
      </div>

      <div className="mb-4 flex gap-3">
        <Input
          className="max-w-xs"
          placeholder="Search contracts…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Filter by status"
          className="rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ContractStatus | '')}
        >
          {STATUS_FILTER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {generateResult && (
        <Alert variant="success" className="mb-4">
          {generateResult}
        </Alert>
      )}

      {error && <ErrorBanner error={error} />}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : contracts.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-300 py-12 text-center">
          <p className="text-neutral-500">No contracts found.</p>
          <Button className="mt-4" variant="ghost" onClick={() => setShowCreate(true)}>
            Create your first contract
          </Button>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Frequency</TableHead>
              <TableHead>Next visit</TableHead>
              <TableHead>Service type</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {contracts.map((contract) => (
              <TableRow key={contract.id} data-testid="contract-row">
                <TableCell className="font-medium">{contract.title}</TableCell>
                <TableCell>
                  <ContractStatusBadge status={contract.status} />
                </TableCell>
                <TableCell className="text-neutral-500">
                  {FREQUENCY_LABELS[contract.frequency] ?? contract.frequency}
                </TableCell>
                <TableCell className="text-neutral-500">
                  {contract.status === 'ended'
                    ? '—'
                    : new Date(`${contract.next_due}T00:00:00`).toLocaleDateString()}
                </TableCell>
                <TableCell className="text-neutral-500">
                  {contract.service_type ?? '—'}
                </TableCell>
                <TableCell className="text-right">
                  {contract.status !== 'ended' && (
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handlePauseResume(contract)}
                        disabled={rowBusy === contract.id}
                      >
                        {contract.status === 'active' ? 'Pause' : 'Resume'}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEndTarget(contract)}
                        disabled={rowBusy === contract.id}
                      >
                        End
                      </Button>
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {showCreate && (
        <CreateContractModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}

      {endTarget && (
        <EndContractModal
          contract={endTarget}
          onClose={() => setEndTarget(null)}
          onEnded={(ended) => {
            setEndTarget(null);
            replaceRow(ended);
          }}
        />
      )}
    </div>
  );
};
