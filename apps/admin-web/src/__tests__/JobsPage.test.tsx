import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockListJobsApi = jest.fn();
const mockCreateJobApi = jest.fn();

jest.mock('../api', () => ({
  listJobsApi: (...args: unknown[]) => mockListJobsApi(...args),
  createJobApi: (...args: unknown[]) => mockCreateJobApi(...args),
}));

import { JobsPage } from '../pages/JobsPage';

const buildJob = (overrides: Record<string, unknown> = {}) => ({
  id: 'job-1',
  title: 'Fix leaking pipe',
  status: 'pending',
  priority: 50,
  scheduled_for: null,
  customer_id: 'cust-1',
  location_id: 'loc-1',
  industry: 'plumbing',
  service_type: 'Drain cleaning',
  ...overrides,
});

const emptyResponse = { items: [], total: 0, limit: 50, offset: 0 };

describe('JobsPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('shows loading skeletons initially', () => {
    mockListJobsApi.mockReturnValue(new Promise(() => {}));
    render(<JobsPage />);
    expect(document.querySelectorAll('[class*="animate-pulse"]').length).toBeGreaterThan(0);
  });

  it('renders job rows on success', async () => {
    mockListJobsApi.mockResolvedValue({
      items: [
        buildJob({ id: 'job-1', title: 'Fix leaking pipe' }),
        buildJob({ id: 'job-2', title: 'Replace boiler', status: 'scheduled' }),
      ],
      total: 2,
      limit: 50,
      offset: 0,
    });

    render(<JobsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('job-row')).toHaveLength(2);
    });

    expect(screen.getByText('Fix leaking pipe')).toBeInTheDocument();
    expect(screen.getByText('Replace boiler')).toBeInTheDocument();
    expect(screen.getAllByText('Pending').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Scheduled').length).toBeGreaterThan(0);
  });

  it('shows empty state when no jobs', async () => {
    mockListJobsApi.mockResolvedValue(emptyResponse);

    render(<JobsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No jobs found/i)).toBeInTheDocument();
    });
  });

  it('shows error alert on load failure', async () => {
    mockListJobsApi.mockRejectedValue({ status: 500, detail: 'server exploded' });

    render(<JobsPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('server exploded');
  });

  it('opens create modal when New job button clicked', async () => {
    mockListJobsApi.mockResolvedValue(emptyResponse);
    render(<JobsPage />);

    await waitFor(() => screen.getByText(/No jobs found/i));

    fireEvent.click(screen.getByRole('button', { name: /New job/i }));
    expect(screen.getByText('New Job')).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
  });

  it('creates a job and adds it to the list', async () => {
    mockListJobsApi.mockResolvedValue(emptyResponse);
    const newJob = buildJob({ id: 'job-new', title: 'Emergency call' });
    mockCreateJobApi.mockResolvedValue(newJob);

    render(<JobsPage />);
    await waitFor(() => screen.getByText(/No jobs found/i));

    fireEvent.click(screen.getByRole('button', { name: /New job/i }));

    fireEvent.change(screen.getByLabelText(/Title/i), {
      target: { value: 'Emergency call' },
    });
    fireEvent.change(screen.getAllByPlaceholderText('UUID')[0], {
      target: { value: 'cust-1' },
    });
    fireEvent.change(screen.getAllByPlaceholderText('UUID')[1], {
      target: { value: 'loc-1' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Create job/i }));

    await waitFor(() => {
      expect(mockCreateJobApi).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Emergency call', customer_id: 'cust-1' })
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Emergency call')).toBeInTheDocument();
    });
  });

  it('shows error in modal on create failure', async () => {
    mockListJobsApi.mockResolvedValue(emptyResponse);
    mockCreateJobApi.mockRejectedValue({ status: 422, detail: 'invalid customer' });

    render(<JobsPage />);
    await waitFor(() => screen.getByText(/No jobs found/i));

    fireEvent.click(screen.getByRole('button', { name: /New job/i }));
    fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: 'Test' } });
    fireEvent.change(screen.getAllByPlaceholderText('UUID')[0], { target: { value: 'cust-x' } });
    fireEvent.change(screen.getAllByPlaceholderText('UUID')[1], { target: { value: 'loc-x' } });
    fireEvent.click(screen.getByRole('button', { name: /Create job/i }));

    await waitFor(() => {
      expect(screen.getByText('invalid customer')).toBeInTheDocument();
    });
  });
});
