import React, { useContext } from 'react';
import { AuthContext } from '../auth';

export const NavShell: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { logout } = useContext(AuthContext);

  return (
    <div>
      <nav style={{ padding: '1rem', borderBottom: '1px solid #ccc' }}>
        <a href="/jobs">Jobs</a> |{' '}
        <a href="/dispatch">Dispatch</a> |{' '}
        <a href="/vehicles">Vehicles</a> |{' '}
        <a href="/users">Users</a> |{' '}
        <button onClick={logout}>Logout</button>
        <span style={{ float: 'right', fontSize: '0.8rem', opacity: 0.6 }}>
          v{__APP_VERSION__}
        </span>
      </nav>
      <main style={{ padding: '1rem' }}>{children}</main>
    </div>
  );
};
