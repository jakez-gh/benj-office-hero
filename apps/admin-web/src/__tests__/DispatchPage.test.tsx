import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

const mockListRoutes = jest.fn();
const mockClient = {
  interceptors: { response: { use: jest.fn().mockReturnValue(1), eject: jest.fn() } },
  defaults: { headers: { common: {} } },
};
jest.mock('@office-hero/api-client', () => ({
  listRoutes: mockListRoutes,
  client: mockClient,
}));

import { DispatchPage } from '../pages/DispatchPage';

describe('DispatchPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('shows loading state initially', () => {
    mockListRoutes.mockReturnValue(new Promise(() => {})); // never resolves
    render(<DispatchPage />);
    expect(screen.getByText('Loading routes…')).toBeInTheDocument();
  });

  it('renders route data in a table on success', async () => {
    mockListRoutes.mockResolvedValue([
      { id: 'r-1', vehicle_id: 'v-10', technician_id: 't-5', status: 'active' },
      { id: 'r-2', vehicle_id: 'v-11', technician_id: 't-6', status: 'complete' },
    ]);

    render(<DispatchPage />);

    await waitFor(() => {
      expect(screen.getByText('Live routes: 2')).toBeInTheDocument();
    });

    expect(screen.getByText('r-1')).toBeInTheDocument();
    expect(screen.getByText('v-10')).toBeInTheDocument();
    expect(screen.getByText('t-5')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
    expect(screen.getByText('r-2')).toBeInTheDocument();
  });

  it('shows empty message when no routes exist', async () => {
    mockListRoutes.mockResolvedValue([]);

    render(<DispatchPage />);

    await waitFor(() => {
      expect(screen.getByText('No dispatch routes found.')).toBeInTheDocument();
    });
  });

  it('displays error message on API failure', async () => {
    mockListRoutes.mockRejectedValue(new Error('Failed to load routes (500)'));

    render(<DispatchPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Failed to load routes (500)');
  });

  it('handles non-Error thrown values', async () => {
    mockListRoutes.mockRejectedValue('network timeout');

    render(<DispatchPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('network timeout');
  });
});
