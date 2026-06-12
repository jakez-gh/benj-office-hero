import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockListContractsApi = jest.fn();
const mockCreateContractApi = jest.fn();
const mockPauseContractApi = jest.fn();
const mockResumeContractApi = jest.fn();
const mockEndContractApi = jest.fn();
const mockGenerateContractJobsApi = jest.fn();
const mockListCustomers = jest.fn();
const mockListLocations = jest.fn();

jest.mock('../api', () => ({
  listContractsApi: (...args: unknown[]) => mockListContractsApi(...args),
  createContractApi: (...args: unknown[]) => mockCreateContractApi(...args),
  pauseContractApi: (...args: unknown[]) => mockPauseContractApi(...args),
  resumeContractApi: (...args: unknown[]) => mockResumeContractApi(...args),
  endContractApi: (...args: unknown[]) => mockEndContractApi(...args),
  generateContractJobsApi: (...args: unknown[]) => mockGenerateContractJobsApi(...args),
}));

jest.mock('@office-hero/api-client', () => ({
  listCustomers: (...args: unknown[]) => mockListCustomers(...args),
  listLocations: (...args: unknown[]) => mockListLocations(...args),
}));

import { ContractsPage } from '../pages/ContractsPage';

const customersResponse = {
  items: [{ id: 'cust-1', name: 'Acme Corp' }],
  total: 1,
  page: 1,
  page_size: 100,
};

const locationsResponse = {
  items: [{ id: 'loc-1', label: 'HQ', formatted_address: '123 Main St' }],
  total: 1,
  page: 1,
  page_size: 100,
};

const buildContract = (overrides: Record<string, unknown> = {}) => ({
  id: 'contract-1',
  title: 'Quarterly pest plan',
  status: 'active',
  frequency: 'quarterly',
  next_due: '2026-09-01',
  end_date: null,
  customer_id: 'cust-1',
  location_id: 'loc-1',
  industry: 'pest_control',
  service_type: 'Pest inspection',
  priority: 50,
  ...overrides,
});

const emptyResponse = { items: [], total: 0, limit: 50, offset: 0 };

describe('ContractsPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockListCustomers.mockResolvedValue(customersResponse);
    mockListLocations.mockResolvedValue(locationsResponse);
  });

  it('renders contract rows with status, frequency, and next visit', async () => {
    mockListContractsApi.mockResolvedValue({
      items: [
        buildContract(),
        buildContract({ id: 'contract-2', title: 'Monthly HVAC check', status: 'paused', frequency: 'monthly' }),
      ],
      total: 2,
      limit: 50,
      offset: 0,
    });

    render(<ContractsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('contract-row')).toHaveLength(2);
    });

    expect(screen.getByText('Quarterly pest plan')).toBeInTheDocument();
    expect(screen.getByText('Monthly HVAC check')).toBeInTheDocument();
    // Status labels also appear as filter <option>s — scope to badge counts.
    expect(screen.getAllByText('Active').length).toBeGreaterThan(1);
    expect(screen.getAllByText('Paused').length).toBeGreaterThan(1);
    expect(screen.getByText('Quarterly')).toBeInTheDocument();
    expect(screen.getByText('Monthly')).toBeInTheDocument();
  });

  it('shows empty state when no contracts', async () => {
    mockListContractsApi.mockResolvedValue(emptyResponse);

    render(<ContractsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No contracts found/i)).toBeInTheDocument();
    });
  });

  it('shows error alert on load failure', async () => {
    mockListContractsApi.mockRejectedValue({ status: 500, detail: 'server exploded' });

    render(<ContractsPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('server exploded');
  });

  it('creates a contract and adds it to the list', async () => {
    mockListContractsApi.mockResolvedValue(emptyResponse);
    mockCreateContractApi.mockResolvedValue({
      ...buildContract({ id: 'contract-new', title: 'New lawn plan' }),
      tenant_id: 'tenant-1',
      description: null,
      estimated_duration_min: 60,
      start_date: '2026-06-12',
      paused_at: null,
      ended_at: null,
      end_reason: null,
      created_at: '2026-06-12T00:00:00Z',
      updated_at: '2026-06-12T00:00:00Z',
    });

    render(<ContractsPage />);
    await waitFor(() => screen.getByText(/No contracts found/i));

    fireEvent.click(screen.getByRole('button', { name: /New contract/i }));

    fireEvent.change(screen.getByLabelText(/Title/i), {
      target: { value: 'New lawn plan' },
    });
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Acme Corp' })).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText(/Customer \*/i), {
      target: { value: 'cust-1' },
    });
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'HQ' })).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText(/Location \*/i), {
      target: { value: 'loc-1' },
    });
    fireEvent.change(screen.getByLabelText(/Frequency \*/i), {
      target: { value: 'monthly' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Create contract/i }));

    await waitFor(() => {
      expect(mockCreateContractApi).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'New lawn plan',
          customer_id: 'cust-1',
          frequency: 'monthly',
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText('New lawn plan')).toBeInTheDocument();
    });
  });

  it('pauses an active contract from the row action', async () => {
    mockListContractsApi.mockResolvedValue({
      items: [buildContract()],
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockPauseContractApi.mockResolvedValue({
      ...buildContract({ status: 'paused' }),
      tenant_id: 'tenant-1',
      description: null,
      estimated_duration_min: 60,
      start_date: '2026-06-01',
      paused_at: '2026-06-12T00:00:00Z',
      ended_at: null,
      end_reason: null,
      created_at: '2026-06-01T00:00:00Z',
      updated_at: '2026-06-12T00:00:00Z',
    });

    render(<ContractsPage />);
    await waitFor(() => screen.getAllByTestId('contract-row'));

    fireEvent.click(screen.getByRole('button', { name: /Pause/i }));

    await waitFor(() => {
      expect(mockPauseContractApi).toHaveBeenCalledWith('contract-1');
      // 'Paused' appears in the filter options too — badge makes it 2+.
      expect(screen.getAllByText('Paused').length).toBeGreaterThan(1);
    });
  });

  it('ends a contract via the end modal with a reason', async () => {
    mockListContractsApi.mockResolvedValue({
      items: [buildContract()],
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockEndContractApi.mockResolvedValue({
      ...buildContract({ status: 'ended' }),
      tenant_id: 'tenant-1',
      description: null,
      estimated_duration_min: 60,
      start_date: '2026-06-01',
      paused_at: null,
      ended_at: '2026-06-12T00:00:00Z',
      end_reason: 'Customer moved away',
      created_at: '2026-06-01T00:00:00Z',
      updated_at: '2026-06-12T00:00:00Z',
    });

    render(<ContractsPage />);
    await waitFor(() => screen.getAllByTestId('contract-row'));

    fireEvent.click(screen.getByRole('button', { name: /^End$/i }));
    fireEvent.change(screen.getByLabelText(/Reason/i), {
      target: { value: 'Customer moved away' },
    });
    fireEvent.click(screen.getByRole('button', { name: /End contract/i }));

    await waitFor(() => {
      expect(mockEndContractApi).toHaveBeenCalledWith('contract-1', 'Customer moved away');
      // 'Ended' appears in the filter options too — badge makes it 2+.
      expect(screen.getAllByText('Ended').length).toBeGreaterThan(1);
    });
  });

  it('generates due jobs and reports the count', async () => {
    mockListContractsApi.mockResolvedValue({
      items: [buildContract()],
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockGenerateContractJobsApi.mockResolvedValue({ generated: [{}, {}], count: 2 });

    render(<ContractsPage />);
    await waitFor(() => screen.getAllByTestId('contract-row'));

    fireEvent.click(screen.getByRole('button', { name: /Generate due jobs/i }));

    await waitFor(() => {
      expect(screen.getByText(/Created 2 jobs from due contracts/i)).toBeInTheDocument();
    });
  });
});
