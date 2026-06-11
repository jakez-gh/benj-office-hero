import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { AuthContext } from '../auth';
import { Button } from './ui/Button';

const navItems = [
  { to: '/jobs',      label: 'Jobs'      },
  { to: '/dispatch',  label: 'Dispatch'  },
  { to: '/vehicles',  label: 'Vehicles'  },
  { to: '/users',     label: 'Users'     },
  { to: '/customers', label: 'Customers' },
];

export const NavShell: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { logout } = useContext(AuthContext);

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="sticky top-0 z-30 flex h-14 items-center border-b border-gray-200 bg-white px-4 shadow-sm">
        {/* Wordmark */}
        <span className="mr-8 text-lg font-bold tracking-tight text-primary-600">
          Office Hero
        </span>

        {/* Nav links */}
        <nav className="flex flex-1 items-center gap-1">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900',
                ].join(' ')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Version + logout */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-neutral-400">v{__APP_VERSION__}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl p-6">{children}</main>
    </div>
  );
};
