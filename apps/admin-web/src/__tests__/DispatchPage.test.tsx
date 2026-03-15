/**
 * DispatchPage tests — TDD for the dispatch-job-via-saga workflow.
 *
 * Covers:
 *  1. Renders dispatch form with inputs and button
 *  2. Dispatching calls createSaga and shows live status
 *  3. Error handling when dispatch fails
 *  4. History table populates after dispatch
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DispatchPage } from '../pages/DispatchPage';

// Mock the api module
vi.mock('../api', () => ({
  createSaga: vi.fn(),
}));

// Mock the useSagaStatus hook
vi.mock('../hooks/useSagaStatus', () => ({
  useSagaStatus: vi.fn(() => ({ saga: null, loading: false, error: null, refresh: vi.fn() })),
}));

import { createSaga } from '../api';
import { useSagaStatus } from '../hooks/useSagaStatus';

const mockCreateSaga = vi.mocked(createSaga);
const mockUseSagaStatus = vi.mocked(useSagaStatus);

describe('DispatchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSagaStatus.mockReturnValue({ saga: null, loading: false, error: null, refresh: vi.fn() });
  });

  it('renders dispatch form', () => {
    render(<DispatchPage />);
    expect(screen.getByTestId('dispatch-page')).toBeInTheDocument();
    expect(screen.getByTestId('dispatch-button')).toBeInTheDocument();
    expect(screen.getByTestId('job-id-input')).toBeInTheDocument();
    expect(screen.getByTestId('technician-id-input')).toBeInTheDocument();
  });

  it('dispatch button triggers createSaga', async () => {
    mockCreateSaga.mockResolvedValueOnce({
      saga_id: 'saga-abc-123',
      saga_type: 'dispatch_job',
      status: 'running',
      current_step: 0,
      context: { job_id: 'j1', technician_id: 't1' },
      last_error: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: null,
    });

    render(<DispatchPage />);

    fireEvent.change(screen.getByTestId('job-id-input'), {
      target: { value: 'job-42' },
    });
    fireEvent.change(screen.getByTestId('technician-id-input'), {
      target: { value: 'tech-7' },
    });
    fireEvent.click(screen.getByTestId('dispatch-button'));

    await waitFor(() => {
      expect(mockCreateSaga).toHaveBeenCalledWith({
        saga_type: 'dispatch_job',
        context: { job_id: 'job-42', technician_id: 'tech-7' },
      });
    });
  });

  it('shows error on dispatch failure', async () => {
    mockCreateSaga.mockRejectedValueOnce({ detail: 'Saga engine down' });

    render(<DispatchPage />);
    fireEvent.click(screen.getByTestId('dispatch-button'));

    await waitFor(() => {
      expect(screen.getByTestId('dispatch-error')).toHaveTextContent('Saga engine down');
    });
  });

  it('shows history table after successful dispatch', async () => {
    mockCreateSaga.mockResolvedValueOnce({
      saga_id: 'saga-abc-123',
      saga_type: 'dispatch_job',
      status: 'running',
      current_step: 0,
      context: {},
      last_error: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: null,
    });

    render(<DispatchPage />);
    fireEvent.click(screen.getByTestId('dispatch-button'));

    await waitFor(() => {
      expect(screen.getByTestId('dispatch-history')).toBeInTheDocument();
    });
  });

  it('shows live saga status when useSagaStatus returns data', () => {
    mockUseSagaStatus.mockReturnValue({
      saga: {
        saga_id: 'saga-live',
        saga_type: 'dispatch_job',
        status: 'running',
        current_step: 1,
        context: {},
        last_error: null,
        created_at: null,
        updated_at: null,
      },
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    render(<DispatchPage />);
    expect(screen.getByTestId('live-saga-status')).toBeInTheDocument();
  });
});
