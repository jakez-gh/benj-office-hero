import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockListRoutesApi = jest.fn();
const mockResequenceRouteApi = jest.fn();
const mockStartRouteApi = jest.fn();
const mockCancelRouteApi = jest.fn();
const mockListVehicles = jest.fn();

jest.mock('../api', () => ({
  listRoutesApi: (...args: unknown[]) => mockListRoutesApi(...args),
  resequenceRouteApi: (...args: unknown[]) => mockResequenceRouteApi(...args),
  startRouteApi: (...args: unknown[]) => mockStartRouteApi(...args),
  cancelRouteApi: (...args: unknown[]) => mockCancelRouteApi(...args),
}));

jest.mock('@office-hero/api-client', () => ({
  listVehicles: (...args: unknown[]) => mockListVehicles(...args),
}));

import { RoutesPage } from '../pages/RoutesPage';

const buildStop = (overrides: Record<string, unknown> = {}) => ({
  id: 'stop-1',
  route_id: 'route-1',
  job_id: 'job-1',
  sequence_index: 0,
  status: 'pending',
  planned_eta: null,
  actual_arrived_at: null,
  actual_completed_at: null,
  planned_distance_from_prev_m: 0,
  planned_duration_from_prev_s: 0,
  ...overrides,
});

const buildRoute = (overrides: Record<string, unknown> = {}) => ({
  id: 'route-1',
  tenant_id: 'tenant-1',
  vehicle_id: 'veh-1',
  vehicle_crew_id: 'crew-1',
  work_date: '2026-06-12',
  status: 'committed',
  committed_at: '2026-06-12T08:00:00Z',
  started_at: null,
  completed_at: null,
  cancelled_at: null,
  cancel_reason: null,
  total_distance_m: 12000,
  total_duration_s: 900,
  option_kind_applied: 'suggested',
  notes: null,
  stops: [
    buildStop(),
    buildStop({ id: 'stop-2', job_id: 'job-2', sequence_index: 1 }),
  ],
  ...overrides,
});

describe('RoutesPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockListVehicles.mockResolvedValue([
      { id: 'veh-1', name: 'Van #1', license_plate: 'ABC-123' },
    ]);
  });

  it('renders route cards with vehicle name, status, and ordered stops', async () => {
    mockListRoutesApi.mockResolvedValue({ items: [buildRoute()], total: 1 });

    render(<RoutesPage />);

    await waitFor(() => {
      expect(screen.getByTestId('route-card')).toBeInTheDocument();
    });
    expect(screen.getByText('Van #1')).toBeInTheDocument();
    expect(screen.getByText('Committed')).toBeInTheDocument();
    expect(screen.getAllByTestId('route-stop')).toHaveLength(2);
  });

  it('shows empty state when no routes for the date', async () => {
    mockListRoutesApi.mockResolvedValue({ items: [], total: 0 });

    render(<RoutesPage />);

    await waitFor(() => {
      expect(screen.getByText(/No routes for this date/i)).toBeInTheDocument();
    });
  });

  it('reorders stops locally and saves via resequence API', async () => {
    mockListRoutesApi.mockResolvedValue({ items: [buildRoute()], total: 1 });
    mockResequenceRouteApi.mockResolvedValue(
      buildRoute({
        stops: [
          buildStop({ id: 'stop-2', job_id: 'job-2', sequence_index: 0 }),
          buildStop({ id: 'stop-1', job_id: 'job-1', sequence_index: 1 }),
        ],
      }),
    );

    render(<RoutesPage />);
    await waitFor(() => screen.getByTestId('route-card'));

    fireEvent.click(screen.getByRole('button', { name: /Move stop 1 down/i }));
    fireEvent.click(screen.getByRole('button', { name: /Save new order/i }));

    await waitFor(() => {
      expect(mockResequenceRouteApi).toHaveBeenCalledWith('route-1', ['job-2', 'job-1']);
    });
  });

  it('starts a committed route', async () => {
    mockListRoutesApi.mockResolvedValue({ items: [buildRoute()], total: 1 });
    mockStartRouteApi.mockResolvedValue(buildRoute({ status: 'in_progress' }));

    render(<RoutesPage />);
    await waitFor(() => screen.getByTestId('route-card'));

    fireEvent.click(screen.getByRole('button', { name: /Start route/i }));

    await waitFor(() => {
      expect(mockStartRouteApi).toHaveBeenCalledWith('route-1');
      expect(screen.getByText('In Progress')).toBeInTheDocument();
    });
  });

  it('cancels a route with a reason', async () => {
    mockListRoutesApi.mockResolvedValue({ items: [buildRoute()], total: 1 });
    mockCancelRouteApi.mockResolvedValue(
      buildRoute({ status: 'cancelled', cancel_reason: 'Tech sick' }),
    );

    render(<RoutesPage />);
    await waitFor(() => screen.getByTestId('route-card'));

    fireEvent.click(screen.getByRole('button', { name: /^Cancel$/i }));
    fireEvent.change(screen.getByLabelText(/Reason/i), { target: { value: 'Tech sick' } });
    fireEvent.click(screen.getByRole('button', { name: /Cancel route/i }));

    await waitFor(() => {
      expect(mockCancelRouteApi).toHaveBeenCalledWith('route-1', 'Tech sick');
      expect(screen.getByText('Cancelled')).toBeInTheDocument();
    });
  });

  it('shows error alert on load failure', async () => {
    mockListRoutesApi.mockRejectedValue({ status: 500, detail: 'boom' });

    render(<RoutesPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('boom');
  });
});
