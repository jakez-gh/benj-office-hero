import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockCreateSaga = jest.fn();
const mockGetSagaState = jest.fn();

jest.mock('../api', () => ({
  createSaga: (...args: unknown[]) => mockCreateSaga(...args),
  getSagaState: (...args: unknown[]) => mockGetSagaState(...args),
}));

import { DispatchPage } from '../pages/DispatchPage';

describe('DispatchPage', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.resetAllMocks();
  });

  afterEach(() => {
    act(() => {
      jest.runOnlyPendingTimers();
    });
    jest.useRealTimers();
  });

  const fillForm = (): void => {
    fireEvent.change(screen.getByLabelText(/Tenant ID/i), {
      target: { value: 'tenant-1' },
    });
    fireEvent.change(screen.getByLabelText(/Job ID/i), {
      target: { value: 'job-1' },
    });
    fireEvent.change(screen.getByLabelText(/Technician ID/i), {
      target: { value: 'tech-1' },
    });
  };

  it('renders the dispatch form', () => {
    render(<DispatchPage />);

    expect(screen.getByRole('heading', { name: /Dispatch/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Dispatch Job/i })).toBeInTheDocument();
  });

  it('submits the form and shows the saga status badge', async () => {
    mockCreateSaga.mockResolvedValue({
      saga_id: 'saga-1',
      saga_type: 'dispatch_job',
      status: 'running',
      current_step: 0,
      context: { tenant_id: 'tenant-1' },
      last_error: null,
      created_at: null,
      updated_at: null,
    });
    mockGetSagaState.mockResolvedValue({
      saga_id: 'saga-1',
      saga_type: 'dispatch_job',
      status: 'done',
      current_step: 1,
      context: { tenant_id: 'tenant-1' },
      last_error: null,
      created_at: null,
      updated_at: null,
    });

    render(<DispatchPage />);
    fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Dispatch Job/i }));

    await waitFor(() => {
      expect(mockCreateSaga).toHaveBeenCalledWith({
        saga_type: 'dispatch_job',
        context: {
          tenant_id: 'tenant-1',
          job_id: 'job-1',
          technician_id: 'tech-1',
        },
      });
    });

    // Saga status badge should appear (status text appears in the badge).
    await waitFor(() => {
      expect(screen.getByTestId('saga-status-badge')).toBeInTheDocument();
    });
  });

  it('shows an error when createSaga fails', async () => {
    mockCreateSaga.mockRejectedValue({ status: 500, detail: 'boom' });

    render(<DispatchPage />);
    fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Dispatch Job/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('boom');
  });
});
