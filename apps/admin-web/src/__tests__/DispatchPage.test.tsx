import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const mockCreateSaga = jest.fn();
const mockGetSagaState = jest.fn();
const mockListJobsApi = jest.fn();
const mockListUsers = jest.fn();
const mockClient = {
  interceptors: { response: { use: jest.fn().mockReturnValue(1), eject: jest.fn() } },
  defaults: { headers: { common: {} } },
};

jest.mock('../api', () => ({
  createSaga: (...args: unknown[]) => mockCreateSaga(...args),
  getSagaState: (...args: unknown[]) => mockGetSagaState(...args),
  listJobsApi: (...args: unknown[]) => mockListJobsApi(...args),
}));

jest.mock('@office-hero/api-client', () => ({
  listUsers: (...args: unknown[]) => mockListUsers(...args),
  client: mockClient,
}));

import { DispatchPage } from '../pages/DispatchPage';

const JOBS = [
  {
    id: 'job-1', title: 'Fix boiler', status: 'pending',
    priority: 50, scheduled_for: null,
    customer_id: 'c1', location_id: 'l1',
    industry: 'plumbing', service_type: null,
  },
];

const TECHNICIANS = [
  { id: 'tech-1', email: 'alice@example.com', role: 'technician', status: 'active' },
];

describe('DispatchPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockListJobsApi.mockResolvedValue({ items: JOBS, total: 1, limit: 100, offset: 0 });
    mockListUsers.mockResolvedValue(TECHNICIANS);
    // useSagaStatus polls via getSagaState; return null by default
    mockGetSagaState.mockResolvedValue(null);
  });

  it('renders the dispatch heading', async () => {
    render(<DispatchPage />);
    expect(screen.getByRole('heading', { name: /Dispatch/i })).toBeInTheDocument();
    // Form renders after data loads
    await waitFor(() => expect(screen.getByRole('button', { name: /Dispatch Job/i })).toBeInTheDocument());
  });

  it('shows skeletons while loading', () => {
    mockListJobsApi.mockReturnValue(new Promise(() => {}));
    render(<DispatchPage />);
    // Dispatch button absent during load
    expect(screen.queryByRole('button', { name: /Dispatch Job/i })).not.toBeInTheDocument();
  });

  it('submits selected job and shows saga status badge', async () => {
    const user = userEvent.setup();
    mockCreateSaga.mockResolvedValue({
      saga_id: 'saga-1', saga_type: 'dispatch_job', status: 'running',
      current_step: 0, context: {}, last_error: null,
      created_at: null, updated_at: null,
    });

    render(<DispatchPage />);
    await waitFor(() => expect(screen.getByRole('button', { name: /Dispatch Job/i })).toBeInTheDocument());

    // Select the first job in the dropdown
    await user.selectOptions(screen.getByRole('listbox', { hidden: true }) || screen.getByLabelText(/Select job/i), 'job-1');

    await user.click(screen.getByRole('button', { name: /Dispatch Job/i }));

    await waitFor(() => expect(mockCreateSaga).toHaveBeenCalledWith(
      expect.objectContaining({
        saga_type: 'dispatch_job',
        context: expect.objectContaining({ job_id: 'job-1' }),
      }),
    ));

    await waitFor(() => expect(screen.getByTestId('saga-status-badge')).toBeInTheDocument());
  });

  it('shows an error when createSaga fails', async () => {
    const user = userEvent.setup();
    mockCreateSaga.mockRejectedValue({ status: 500, detail: 'Internal error' });

    render(<DispatchPage />);
    await waitFor(() => expect(screen.getByRole('button', { name: /Dispatch Job/i })).toBeInTheDocument());

    await user.selectOptions(screen.getByLabelText(/Select job/i), 'job-1');
    await user.click(screen.getByRole('button', { name: /Dispatch Job/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Internal error');
  });

  it('shows error state when jobs fail to load', async () => {
    mockListJobsApi.mockRejectedValue(new Error('Network error'));

    render(<DispatchPage />);
    await waitFor(() => expect(screen.getByText(/Could not load jobs/i)).toBeInTheDocument());
  });
});
