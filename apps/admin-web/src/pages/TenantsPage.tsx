import React, { useCallback, useEffect, useState } from 'react';
import {
  listTenantsApi,
  createTenantApi,
  patchTenantAdapterApi,
  type Tenant,
} from '../api';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/Table';

const INDUSTRIES = [
  'generic',
  'pest_control',
  'hvac',
  'plumbing',
  'electrical',
  'landscaping',
] as const;

const ADAPTERS = ['native', 'servicetitan', 'pestpac', 'jobber'] as const;

export const TenantsPage: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-tenant saving state
  const [savingAdapter, setSavingAdapter] = useState<Record<string, boolean>>({});

  // New tenant form
  const [newName, setNewName] = useState('');
  const [newIndustry, setNewIndustry] = useState<string>('generic');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTenantsApi();
      setTenants(data.items);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const handleAdapterChange = useCallback(async (tenant: Tenant, adapter: string) => {
    setSavingAdapter(prev => ({ ...prev, [tenant.id]: true }));
    try {
      await patchTenantAdapterApi(tenant.id, adapter);
      setTenants(prev =>
        prev.map(t => t.id === tenant.id ? { ...t, back_office_adapter: adapter } : t),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to update adapter');
    } finally {
      setSavingAdapter(prev => ({ ...prev, [tenant.id]: false }));
    }
  }, []);

  const handleCreate = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const tenant = await createTenantApi({ name: newName.trim(), industry: newIndustry });
      setTenants(prev => [tenant, ...prev]);
      setNewName('');
      setNewIndustry('generic');
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : 'Failed to create tenant');
    } finally {
      setCreating(false);
    }
  }, [newName, newIndustry]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-neutral-900">Tenants</h1>

      {error && <ErrorBanner error={error} />}

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map(i => <Skeleton key={i} className="h-10 w-full" />)}
        </div>
      ) : (
        <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Adapter</TableHead>
              <TableHead>Integration</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tenants.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-neutral-400">
                  No tenants yet — create one below.
                </TableCell>
              </TableRow>
            ) : (
              tenants.map(tenant => (
                <TableRow key={tenant.id}>
                  <TableCell className="font-medium">{tenant.name}</TableCell>
                  <TableCell>{tenant.industry}</TableCell>
                  <TableCell>
                    <select
                      aria-label={`Adapter for ${tenant.name}`}
                      value={tenant.back_office_adapter}
                      disabled={savingAdapter[tenant.id]}
                      onChange={e => void handleAdapterChange(tenant, e.target.value)}
                      className="rounded border border-neutral-300 bg-white px-2 py-1 text-sm disabled:opacity-50"
                    >
                      {ADAPTERS.map(a => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </TableCell>
                  <TableCell>
                    <IntegrationCell tenant={tenant} />
                  </TableCell>
                  <TableCell className="text-sm text-neutral-500">
                    {new Date(tenant.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        </div>
      )}

      {/* New tenant form */}
      <div className="rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-neutral-700">New Tenant</h2>
        {createError && <ErrorBanner error={createError} />}
        <form onSubmit={e => void handleCreate(e)} className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <Label htmlFor="tenant-name">Name</Label>
            <Input
              id="tenant-name"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="Acme Pest Control"
              className="w-56"
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="tenant-industry">Industry</Label>
            <select
              id="tenant-industry"
              aria-label="Industry"
              value={newIndustry}
              onChange={e => setNewIndustry(e.target.value)}
              className="rounded border border-neutral-300 bg-white px-2 py-1.5 text-sm"
            >
              {INDUSTRIES.map(i => (
                <option key={i} value={i}>{i}</option>
              ))}
            </select>
          </div>
          <Button type="submit" disabled={creating || !newName.trim()}>
            {creating ? 'Creating…' : 'Create'}
          </Button>
        </form>
      </div>
    </div>
  );
};

const IntegrationCell: React.FC<{ tenant: Tenant }> = ({ tenant }) => {
  const { back_office_adapter: adapter, jobber_connected, id } = tenant;

  if (adapter === 'jobber') {
    if (jobber_connected) {
      return <span className="text-xs font-medium text-green-600">Connected</span>;
    }
    return (
      <a
        href={`/admin/integrations/jobber/connect?tenant_id=${encodeURIComponent(id)}`}
        className="text-xs font-medium text-primary-600 hover:underline"
      >
        Connect Jobber
      </a>
    );
  }

  if (adapter === 'servicetitan' || adapter === 'pestpac') {
    return (
      <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-500">
        Env vars
      </span>
    );
  }

  return <span className="text-xs text-neutral-400">—</span>;
};
