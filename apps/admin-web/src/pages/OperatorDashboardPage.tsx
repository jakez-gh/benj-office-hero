import React, { useCallback, useEffect, useState } from 'react';
import {
  type RateLimitItem,
  type BanFilterItem,
  type AuditEvent,
  listRateLimitsApi,
  updateRateLimitApi,
  listBanFiltersApi,
  createBanFilterApi,
  deleteBanFilterApi,
  listAuditEventsApi,
  type ApiError,
} from '../api';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { Button } from '../components/ui/Button';

type Tab = 'rate-limits' | 'ban-filters' | 'audit-log';

// ---------------------------------------------------------------------------
// Rate Limits tab
// ---------------------------------------------------------------------------

function RateLimitsTab() {
  const [items, setItems] = useState<RateLimitItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    listRateLimitsApi()
      .then(r => { setItems(r.items); setError(null); })
      .catch((e: ApiError) => setError(e.detail ?? 'Failed to load rate limits'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  function beginEdit(name: string, current: number) {
    setEditing(prev => ({ ...prev, [name]: current }));
  }

  async function saveEdit(item: RateLimitItem) {
    const newLimit = editing[item.name];
    if (newLimit == null) return;
    setSaving(item.name);
    try {
      const updated = await updateRateLimitApi(item.name, {
        limit: newLimit,
        per_seconds: item.per_seconds,
        scope: item.scope,
      });
      setItems(prev => prev.map(i => (i.name === item.name ? { ...i, ...updated } : i)));
      setEditing(prev => { const n = { ...prev }; delete n[item.name]; return n; });
      setError(null);
    } catch (e: unknown) {
      setError((e as ApiError).detail ?? 'Save failed');
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <p className="text-sm text-neutral-500">Loading…</p>;
  if (error) return (
    <div className="space-y-3">
      <ErrorBanner error={error} />
      <button
        className="text-sm font-medium text-primary-600 hover:underline"
        type="button"
        onClick={() => void load()}
      >
        Retry
      </button>
    </div>
  );

  return (
    <div>
      <p className="mb-3 text-sm text-neutral-600">
        Override default rate limits for each request scope. Changes take effect immediately.
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs font-semibold uppercase text-neutral-500">
            <th className="py-2 pr-4">Scope</th>
            <th className="py-2 pr-4">Limit (req / window)</th>
            <th className="py-2 pr-4">Window (s)</th>
            <th className="py-2"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {items.map(item => (
            <tr key={item.name}>
              <td className="py-2 pr-4 font-mono text-neutral-800">{item.name}</td>
              <td className="py-2 pr-4">
                {item.name in editing ? (
                  <input
                    type="number"
                    min={1}
                    aria-label={`Limit for ${item.name}`}
                    value={editing[item.name]}
                    onChange={e =>
                      setEditing(prev => ({ ...prev, [item.name]: Number(e.target.value) }))
                    }
                    className="w-24 rounded border border-neutral-300 px-2 py-0.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                ) : (
                  <span>{item.limit}</span>
                )}
              </td>
              <td className="py-2 pr-4 text-neutral-500">{item.per_seconds}</td>
              <td className="py-2">
                {item.name in editing ? (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => saveEdit(item)}
                      disabled={saving === item.name}
                    >
                      {saving === item.name ? 'Saving…' : 'Save'}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        setEditing(prev => { const n = { ...prev }; delete n[item.name]; return n; })
                      }
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button size="sm" variant="ghost" onClick={() => beginEdit(item.name, item.limit)}>
                    Edit
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ban Filters tab
// ---------------------------------------------------------------------------

function BanFiltersTab() {
  const [items, setItems] = useState<BanFilterItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newScope, setNewScope] = useState('ip');
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);

  const loadBans = useCallback(() => {
    setLoading(true);
    listBanFiltersApi()
      .then(r => { setItems(r.items); setError(null); })
      .catch((e: ApiError) => setError(e.detail ?? 'Failed to load ban filters'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadBans(); }, [loadBans]);

  async function addBan() {
    if (!newName.trim()) return;
    setAdding(true);
    try {
      const created = await createBanFilterApi({ name: newName.trim(), scope: newScope });
      setItems(prev => [created, ...prev]);
      setNewName('');
      setError(null);
    } catch (e: unknown) {
      setError((e as ApiError).detail ?? 'Failed to add ban');
    } finally {
      setAdding(false);
    }
  }

  async function removeBan(id: string) {
    setRemoving(id);
    try {
      await deleteBanFilterApi(id);
      setItems(prev => prev.filter(b => b.id !== id));
      setError(null);
    } catch (e: unknown) {
      setError((e as ApiError).detail ?? 'Failed to remove ban');
    } finally {
      setRemoving(null);
    }
  }

  return (
    <div>
      {error && <ErrorBanner error={error} className="mb-3" />}
      <div className="mb-4 flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-neutral-600">
            IP / Tenant ID / User ID
          </label>
          <input
            type="text"
            placeholder="e.g. 192.168.1.1 or tenant-uuid"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addBan()}
            className="w-full rounded border border-neutral-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>
        <div>
          <label htmlFor="ban-scope" className="mb-1 block text-xs font-medium text-neutral-600">Scope</label>
          <select
            id="ban-scope"
            value={newScope}
            onChange={e => setNewScope(e.target.value)}
            className="rounded border border-neutral-300 px-2 py-1.5 text-sm"
          >
            <option value="ip">IP</option>
            <option value="tenant">Tenant</option>
            <option value="user">User</option>
          </select>
        </div>
        <Button onClick={addBan} disabled={adding || !newName.trim()}>
          {adding ? 'Adding…' : 'Add ban'}
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-neutral-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-neutral-400">No active bans.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs font-semibold uppercase text-neutral-500">
              <th className="py-2 pr-4">Target</th>
              <th className="py-2 pr-4">Scope</th>
              <th className="py-2 pr-4">Added</th>
              <th className="py-2"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {items.map(ban => (
              <tr key={ban.id}>
                <td className="py-2 pr-4 font-mono text-neutral-800">{ban.name}</td>
                <td className="py-2 pr-4">
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                    {ban.scope}
                  </span>
                </td>
                <td className="py-2 pr-4 text-neutral-500">
                  {ban.created_at ? new Date(ban.created_at).toLocaleString() : '—'}
                </td>
                <td className="py-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeBan(ban.id)}
                    disabled={removing === ban.id}
                    className="text-red-600 hover:text-red-700"
                  >
                    {removing === ban.id ? 'Removing…' : 'Remove'}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Audit Log tab
// ---------------------------------------------------------------------------

function AuditLogTab() {
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState('');
  const [filterTenant, setFilterTenant] = useState('');
  const [offset, setOffset] = useState(0);
  const LIMIT = 25;

  const load = useCallback(() => {
    setLoading(true);
    listAuditEventsApi({
      event_type: filterType || undefined,
      tenant_id: filterTenant || undefined,
      limit: LIMIT,
      offset,
    })
      .then(r => { setItems(r.items); setTotal(r.total); setError(null); })
      .catch((e: ApiError) => setError(e.detail ?? 'Failed to load audit events'))
      .finally(() => setLoading(false));
  }, [filterType, filterTenant, offset]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

  function applyFilters() {
    setOffset(0);
    load();
  }

  return (
    <div>
      {error && <ErrorBanner error={error} className="mb-3" />}
      <div className="mb-4 flex flex-wrap items-end gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-600">Event type</label>
          <input
            type="text"
            placeholder="e.g. auth.login"
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && applyFilters()}
            className="rounded border border-neutral-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-600">Tenant ID</label>
          <input
            type="text"
            placeholder="UUID"
            value={filterTenant}
            onChange={e => setFilterTenant(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && applyFilters()}
            className="w-64 rounded border border-neutral-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>
        <Button onClick={applyFilters} size="sm">Filter</Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => { setFilterType(''); setFilterTenant(''); setOffset(0); }}
        >
          Clear
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-neutral-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-neutral-400">No audit events found.</p>
      ) : (
        <>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs font-semibold uppercase text-neutral-500">
                <th className="py-2 pr-3">Timestamp</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Tenant</th>
                <th className="py-2">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y font-mono text-xs">
              {items.map(evt => (
                <tr key={evt.id}>
                  <td className="py-1.5 pr-3 text-neutral-500 whitespace-nowrap">
                    {new Date(evt.timestamp).toLocaleString()}
                  </td>
                  <td className="py-1.5 pr-3">
                    <span className="rounded bg-neutral-100 px-1.5 py-0.5">{evt.event_type}</span>
                  </td>
                  <td className="py-1.5 pr-3 text-neutral-500">
                    {evt.tenant_id.slice(0, 8)}&hellip;
                  </td>
                  <td className="max-w-xs truncate py-1.5 text-neutral-600">
                    {JSON.stringify(evt.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 flex items-center justify-between text-sm text-neutral-500">
            <span>
              {offset + 1}&ndash;{Math.min(offset + LIMIT, total)} of {total}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="ghost"
                disabled={offset === 0}
                onClick={() => setOffset(o => Math.max(0, o - LIMIT))}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={offset + LIMIT >= total}
                onClick={() => setOffset(o => o + LIMIT)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page shell
// ---------------------------------------------------------------------------

export function OperatorDashboardPage() {
  const [tab, setTab] = useState<Tab>('rate-limits');

  const tabs: { id: Tab; label: string }[] = [
    { id: 'rate-limits', label: 'Rate Limits' },
    { id: 'ban-filters', label: 'Ban Filters' },
    { id: 'audit-log',   label: 'Audit Log'   },
  ];

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-neutral-900">Operator Dashboard</h1>
      <p className="mb-6 text-sm text-neutral-500">
        Rate-limit management, ban-filter control, and audit event log.
      </p>

      {/* Tab bar */}
      <div className="mb-6 flex gap-1 border-b border-neutral-200">
        {tabs.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={[
              'px-4 py-2 text-sm font-medium transition-colors',
              tab === t.id
                ? 'border-b-2 border-primary-600 text-primary-700'
                : 'text-neutral-500 hover:text-neutral-800',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'rate-limits' && <RateLimitsTab />}
      {tab === 'ban-filters' && <BanFiltersTab />}
      {tab === 'audit-log'   && <AuditLogTab />}
    </div>
  );
}
