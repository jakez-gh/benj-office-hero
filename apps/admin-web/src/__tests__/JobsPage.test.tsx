import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

const mockListJobs = jest.fn();
const mockClient = {
  interceptors: { response: { use: jest.fn().mockReturnValue(1), eject: jest.fn() } },
  defaults: { headers: { common: {} } },
};
jest.mock('@office-hero/api-client', () => ({
  listJobs: mockListJobs,
  client: mockClient,
}));

import { JobsPage } from '../pages/JobsPage';

describe('JobsPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('shows loading state initially', () => {
    mockListJobs.mockReturnValue(new Promise(() => {}));
    render(<JobsPage />);
    expect(screen.getByText('Loading jobs…')).toBeInTheDocument();
  });

  it('renders job data in a table on success', async () => {
    mockListJobs.mockResolvedValue([
      { id: 'j-1', customer_name: 'Acme Corp', address: '123 Main St', status: 'pending' },
      { id: 'j-2', customer: 'Beta Inc', address: '456 Oak Ave', status: 'complete' },
    ]);

    render(<JobsPage />);

    await waitFor(() => {
      expect(screen.getByText('Live jobs: 2')).toBeInTheDocument();
    });

    expect(screen.getByText('j-1')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
    // Falls back to 'customer' when 'customer_name' is missing
    expect(screen.getByText('Beta Inc')).toBeInTheDocument();
  });

  it('shows empty message when no jobs exist', async () => {
    mockListJobs.mockResolvedValue([]);

    render(<JobsPage />);

    await waitFor(() => {
      expect(screen.getByText('No jobs found.')).toBeInTheDocument();
    });
  });

  it('displays error message on API failure', async () => {
    mockListJobs.mockRejectedValue(new Error('Failed to load jobs (500)'));

    render(<JobsPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Failed to load jobs (500)');
  });

  it('handles non-Error thrown values', async () => {
    mockListJobs.mockRejectedValue('timeout');

    render(<JobsPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('timeout');
  });
});
