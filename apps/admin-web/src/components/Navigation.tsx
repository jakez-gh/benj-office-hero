/**
 * Navigation — sidebar navigation for the admin shell.
 *
 * Links: Jobs, Dispatch, Vehicles, Users.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/jobs', label: '📋 Jobs' },
  { to: '/dispatch', label: '🚀 Dispatch' },
  { to: '/vehicles', label: '🚗 Vehicles' },
  { to: '/users', label: '👤 Users' },
];

const navStyle: React.CSSProperties = {
  width: '200px',
  background: '#1e293b',
  color: '#e2e8f0',
  padding: '1rem',
  minHeight: '100vh',
};

const linkStyle: React.CSSProperties = {
  display: 'block',
  padding: '0.5rem 0.75rem',
  margin: '0.25rem 0',
  borderRadius: '6px',
  textDecoration: 'none',
  color: '#e2e8f0',
};

const activeLinkStyle: React.CSSProperties = {
  ...linkStyle,
  background: '#3b82f6',
  color: '#fff',
};

export function Navigation() {
  return (
    <nav style={navStyle} data-testid="navigation">
      <h2 style={{ margin: '0 0 1rem', fontSize: '1.2rem' }}>⚡ Office Hero</h2>
      {navItems.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          style={({ isActive }) => (isActive ? activeLinkStyle : linkStyle)}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
