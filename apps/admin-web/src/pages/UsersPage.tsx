import React, { useEffect, useState } from 'react';
import { listUsers } from '@office-hero/api-client';
import type { AdminUser } from '@office-hero/api-client';

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async (): Promise<void> => {
      setLoading(true);
      setError(null);

      try {
        const data = await listUsers();
        if (!cancelled) setUsers(data);
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

  if (loading) return <div><h1>Users</h1><p>Loading users…</p></div>;

  if (error) {
    return (
      <div>
        <h1>Users</h1>
        <p role="alert" style={{ color: '#b00020' }}>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Users</h1>
      <p style={{ marginBottom: '0.75rem' }}>Live users: {users.length}</p>

      {users.length === 0 ? (
        <p style={{ color: '#666' }}>No users found.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>User ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Email</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Role</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '0.5rem' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user, index) => (
              <tr key={user.id ?? `user-${String(index)}`}>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{user.id}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{user.email ?? user.full_name ?? '—'}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{user.role ?? '—'}</td>
                <td style={{ borderBottom: '1px solid #f0f0f0', padding: '0.5rem' }}>{user.status ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
