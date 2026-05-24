import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

const mockListUsers = jest.fn();
const mockClient = {
  interceptors: { response: { use: jest.fn().mockReturnValue(1), eject: jest.fn() } },
  defaults: { headers: { common: {} } },
};
jest.mock('@office-hero/api-client', () => ({
  listUsers: mockListUsers,
  client: mockClient,
}));

import { UsersPage } from '../pages/UsersPage';

describe('UsersPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('shows loading state initially', () => {
    mockListUsers.mockReturnValue(new Promise(() => {}));
    render(<UsersPage />);
    expect(screen.getByText('Loading users…')).toBeInTheDocument();
  });

  it('renders user data in a table on success', async () => {
    mockListUsers.mockResolvedValue([
      { id: 'u-1', email: 'alice@example.com', role: 'admin', status: 'active' },
      { id: 'u-2', full_name: 'Bob Smith', role: 'tech', status: 'inactive' },
    ]);

    render(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText('Live users: 2')).toBeInTheDocument();
    });

    expect(screen.getByText('u-1')).toBeInTheDocument();
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
    // Falls back to full_name when email is missing
    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
  });

  it('shows empty message when no users exist', async () => {
    mockListUsers.mockResolvedValue([]);

    render(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText('No users found.')).toBeInTheDocument();
    });
  });

  it('displays error message on API failure', async () => {
    mockListUsers.mockRejectedValue(new Error('Failed to load users (403)'));

    render(<UsersPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Failed to load users (403)');
  });

  it('handles non-Error thrown values', async () => {
    mockListUsers.mockRejectedValue(42);

    render(<UsersPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('42');
  });
});
