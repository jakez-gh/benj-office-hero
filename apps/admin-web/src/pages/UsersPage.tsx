import React, { useCallback, useEffect, useState } from 'react';
import { listUsers } from '@office-hero/api-client';
import type { AdminUser } from '@office-hero/api-client';
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

const ROLE_COLORS: Record<string, string> = {
  admin:        'bg-purple-100 text-purple-800',
  tenant_admin: 'bg-purple-100 text-purple-800',
  dispatcher:   'bg-blue-100 text-blue-800',
  technician:   'bg-teal-100 text-teal-800',
  tech:         'bg-teal-100 text-teal-800',
};

function RoleBadge({ role }: { role: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[role] ?? 'bg-neutral-100 text-neutral-600'}`}
    >
      {role}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const active = status === 'active';
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        active ? 'bg-green-100 text-green-800' : 'bg-neutral-100 text-neutral-500'
      }`}
    >
      {status}
    </span>
  );
}

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewHint, setShowNewHint] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await listUsers();
      setUsers(data);
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
        <h1 className="mb-6 text-2xl font-semibold text-neutral-900">Users</h1>
        <p className="sr-only">Loading users…</p>
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
          <h1 className="text-2xl font-semibold text-neutral-900">Users</h1>
          {!loading && !error && (
            <p className="mt-0.5 text-sm text-neutral-500">Live users: {users.length}</p>
          )}
        </div>
        <Button onClick={() => setShowNewHint(v => !v)}>New User</Button>
      </div>
      {showNewHint && (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          User creation is managed via the backend API. Contact your administrator to invite new users.
        </p>
      )}

      {error && <ErrorBanner error={error} />}

      {users.length === 0 && !loading && (
        <div className="rounded-lg border border-dashed border-neutral-300 py-12 text-center">
          <p className="text-neutral-500">
            {error ? 'Users could not be loaded.' : 'No users on record.'}
          </p>
        </div>
      )}

      {users.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User ID</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user, index) => (
              <TableRow key={user.id ?? `user-${String(index)}`}>
                <TableCell className="max-w-[10rem] truncate font-mono text-xs text-neutral-400">
                  {user.id}
                </TableCell>
                <TableCell className="font-medium">
                  {user.email ?? user.full_name ?? '—'}
                </TableCell>
                <TableCell>{user.role ? <RoleBadge role={user.role} /> : '—'}</TableCell>
                <TableCell>{user.status ? <StatusBadge status={user.status} /> : '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
};
