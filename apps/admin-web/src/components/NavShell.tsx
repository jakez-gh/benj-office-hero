import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { AuthContext } from '../auth';
import { Button } from './ui/Button';
import { PageProgressBar } from './ui/PageProgressBar';
import { OnboardingChecklist } from './OnboardingChecklist';

const navItems = [
  { to: '/jobs',      label: 'Jobs'      },
  { to: '/contracts', label: 'Contracts' },
  { to: '/routes',    label: 'Routes'    },
  { to: '/dispatch',  label: 'Dispatch'  },
  { to: '/vehicles',  label: 'Vehicles'  },
  { to: '/users',     label: 'Users'     },
  { to: '/customers', label: 'Customers' },
];

export const NavShell: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { logout } = useContext(AuthContext);

  return (
    <div className="min-h-screen bg-neutral-50">
      <PageProgressBar />
      <header className="sticky top-0 z-30 border-b border-gray-200 bg-white shadow-sm">
        <div className="flex h-14 items-center gap-3 px-4">
          {/* Wordmark */}
          <span className="shrink-0 whitespace-nowrap text-lg font-bold tracking-tight text-primary-600">
            Office Hero
          </span>

          {/* Nav links — scroll horizontally on narrow screens instead of
              overflowing the page (7 items don't fit at 375px). The gradient
              mask on the right edge signals that more items are scrollable. */}
          <div className="relative flex min-w-0 flex-1">
            <nav className="flex flex-1 items-center gap-1 overflow-x-auto whitespace-nowrap [scrollbar-width:none]">
              {navItems.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    [
                      'shrink-0 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
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
            {/* Right-edge fade — pointer-events:none so it doesn't block clicks */}
            <div className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-white to-transparent" />
          </div>

          {/* Version + logout */}
          <div className="flex shrink-0 items-center gap-3">
            <span data-testid="app-version" className="hidden text-xs text-neutral-400 sm:inline">
              v{__APP_VERSION__}
            </span>
            <Button variant="ghost" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <OnboardingChecklist />
      <main className="mx-auto max-w-6xl p-4 sm:p-6">{children}</main>
    </div>
  );
};
