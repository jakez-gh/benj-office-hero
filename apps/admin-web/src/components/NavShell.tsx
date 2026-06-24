import React, { useContext, useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { AuthContext } from '../auth';
import { Button } from './ui/Button';
import { PageProgressBar } from './ui/PageProgressBar';
import { OnboardingChecklist } from './OnboardingChecklist';

const BASE_NAV = [
  { to: '/jobs',      label: 'Jobs'      },
  { to: '/contracts', label: 'Contracts' },
  { to: '/routes',    label: 'Routes'    },
  { to: '/dispatch',  label: 'Dispatch'  },
  { to: '/vehicles',  label: 'Vehicles'  },
  { to: '/users',     label: 'Users'     },
  { to: '/customers', label: 'Customers' },
];

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
    isActive
      ? 'bg-primary-50 text-primary-700'
      : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900',
  ].join(' ');

export const NavShell: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { logout, user } = useContext(AuthContext);
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const navItems = user?.role === 'operator'
    ? [...BASE_NAV, { to: '/tenants', label: 'Tenants' }, { to: '/operator', label: 'Operator' }]
    : BASE_NAV;

  // Close drawer on route change
  useEffect(() => { setDrawerOpen(false); }, [location.pathname]);

  // Prevent body scroll when drawer is open
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [drawerOpen]);

  return (
    <div className="min-h-screen bg-neutral-50">
      <PageProgressBar />
      <header className="sticky top-0 z-30 border-b border-gray-200 bg-white shadow-sm">
        <div className="flex h-14 items-center gap-3 px-4">
          {/* Hamburger — mobile only */}
          <button
            type="button"
            className="shrink-0 rounded-md p-1.5 text-neutral-600 hover:bg-neutral-100 md:hidden"
            aria-label="Open navigation menu"
            aria-expanded={drawerOpen ? 'true' : 'false'}
            onClick={() => setDrawerOpen(true)}
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Wordmark */}
          <span className="shrink-0 whitespace-nowrap text-lg font-bold tracking-tight text-primary-600">
            Office Hero
          </span>

          {/* Desktop nav — hidden below md */}
          <nav className="hidden flex-1 items-center gap-1 md:flex">
            {navItems.map(({ to, label }) => (
              <NavLink key={to} to={to} className={navLinkClass}>
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Version + logout */}
          <div className="ml-auto flex shrink-0 items-center gap-3">
            <span data-testid="app-version" className="hidden text-xs text-neutral-400 sm:inline">
              v{__APP_VERSION__}
            </span>
            <Button variant="ghost" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      {/* Mobile drawer overlay */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          aria-hidden="true"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* Mobile drawer panel */}
      <div
        className={[
          'fixed inset-y-0 left-0 z-50 w-64 transform bg-white shadow-xl transition-transform duration-200 md:hidden',
          drawerOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
        aria-label="Navigation drawer"
      >
        <div className="flex h-14 items-center justify-between border-b border-gray-200 px-4">
          <span className="text-lg font-bold tracking-tight text-primary-600">Office Hero</span>
          <button
            type="button"
            className="rounded-md p-1.5 text-neutral-600 hover:bg-neutral-100"
            aria-label="Close navigation menu"
            onClick={() => setDrawerOpen(false)}
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {navItems.map(({ to, label }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              [
                'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900',
              ].join(' ')
            }>
              {label}
            </NavLink>
          ))}
          <div className="mt-2 border-t border-neutral-200 pt-2">
            <button
              type="button"
              onClick={logout}
              className="w-full rounded-md px-3 py-2 text-left text-sm font-medium text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
            >
              Sign out
            </button>
          </div>
        </nav>
      </div>

      <OnboardingChecklist />
      <main className="mx-auto max-w-6xl p-4 sm:p-6">{children}</main>
    </div>
  );
};
