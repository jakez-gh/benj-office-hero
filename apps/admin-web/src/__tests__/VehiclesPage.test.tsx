import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

const mockListVehicles = jest.fn();
const mockClient = {
  interceptors: { response: { use: jest.fn().mockReturnValue(1), eject: jest.fn() } },
  defaults: { headers: { common: {} } },
};
jest.mock('@office-hero/api-client', () => ({
  listVehicles: mockListVehicles,
  client: mockClient,
}));

import { VehiclesPage } from '../pages/VehiclesPage';

describe('VehiclesPage', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('shows loading state initially', () => {
    mockListVehicles.mockReturnValue(new Promise(() => {}));
    render(<VehiclesPage />);
    expect(screen.getByText('Loading vehicles…')).toBeInTheDocument();
  });

  it('renders vehicle data in a table on success', async () => {
    mockListVehicles.mockResolvedValue([
      { id: 'v-1', name: 'Truck Alpha', license_plate: 'ABC-123', status: 'active' },
      { id: 'v-2', make: 'Ford', model: 'Transit', license_plate: 'XYZ-789', status: 'maintenance' },
    ]);

    render(<VehiclesPage />);

    await waitFor(() => {
      expect(screen.getByText('Live vehicles: 2')).toBeInTheDocument();
    });

    expect(screen.getByText('v-1')).toBeInTheDocument();
    expect(screen.getByText('Truck Alpha')).toBeInTheDocument();
    expect(screen.getByText('ABC-123')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
    // Falls back to make + model when name is absent
    expect(screen.getByText('Ford Transit')).toBeInTheDocument();
  });

  it('shows dash for vehicle with no name, make, or model', async () => {
    mockListVehicles.mockResolvedValue([
      { id: 'v-3', license_plate: 'ZZZ-000', status: 'idle' },
    ]);

    render(<VehiclesPage />);

    await waitFor(() => {
      expect(screen.getByText('Live vehicles: 1')).toBeInTheDocument();
    });

    // Vehicle column shows '—' when no name/make/model
    const cells = screen.getAllByRole('cell');
    const vehicleCell = cells[1]; // second cell is the Vehicle column
    expect(vehicleCell).toHaveTextContent('—');
  });

  it('shows empty message when no vehicles exist', async () => {
    mockListVehicles.mockResolvedValue([]);

    render(<VehiclesPage />);

    await waitFor(() => {
      expect(screen.getByText('No vehicles found.')).toBeInTheDocument();
    });
  });

  it('displays error message on API failure', async () => {
    mockListVehicles.mockRejectedValue(new Error('Failed to load vehicles (500)'));

    render(<VehiclesPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Failed to load vehicles (500)');
  });

  it('handles non-Error thrown values', async () => {
    mockListVehicles.mockRejectedValue('connection refused');

    render(<VehiclesPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('connection refused');
  });
});
