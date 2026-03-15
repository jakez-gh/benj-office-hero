/**
 * JobsPage tests — TDD for dead-letter retry workflow.
 *
 * Covers:
 *  1. Renders empty state when no dead-letter events
 *  2. Renders table with dead-letter events
 *  3. Retry button calls retryDeadLetter and refreshes list
 *  4. Shows error when API fails
 *  5. View logs button shows saga detail panel
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { JobsPage } from '../pages/JobsPage';

vi.mock('../api', () => ({
  listDeadLetters: vi.fn(),
  retryDeadLetter: vi.fn(),
  getSagaLogs: vi.fn(),
}));

import { listDeadLetters, retryDeadLetter, getSagaLogs } from '../api';

const mockListDeadLetters = vi.mocked(listDeadLetters);
const mockRetryDeadLetter = vi.mocked(retryDeadLetter);
const mockGetSagaLogs = vi.mocked(getSagaLogs);

const SAMPLE_EVENTS = [
  {
    id: 'evt-111-aaa',
    tenant_id: 'tenant-1',
    event_type: 'saga.dispatch_job.step_failed',
    payload: { job_id: 'j1' },
    status: 'failed',
    attempt_count: 3,
    created_at: '2026-01-01T00:00:00Z',
    processed_at: null,
    dead_letter_reason: 'max retries exceeded',
  },
  {
    id: 'evt-222-bbb',
    tenant_id: 'tenant-1',
    event_type: 'saga.vehicle_assign.step_failed',
    payload: { vehicle_id: 'v1' },
    status: 'failed',
    attempt_count: 5,
    created_at: '2026-01-02T00:00:00Z',
    processed_at: null,
    dead_letter_reason: 'timeout',
  },
];

describe('JobsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty state when no dead-letter events', async () => {
    mockListDeadLetters.mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    render(<JobsPage />);
    await waitFor(() => {
      expect(screen.getByTestId('no-events')).toBeInTheDocument();
    });
  });

  it('renders table with dead-letter events', async () => {
    mockListDeadLetters.mockResolvedValue({
      items: SAMPLE_EVENTS,
      total: 2,
      limit: 50,
      offset: 0,
    });

    render(<JobsPage />);
    await waitFor(() => {
      expect(screen.getByTestId('dead-letter-table')).toBeInTheDocument();
    });
    // Both events rendered
    expect(screen.getByTestId('retry-evt-111-aaa')).toBeInTheDocument();
    expect(screen.getByTestId('retry-evt-222-bbb')).toBeInTheDocument();
  });

  it('retry button calls retryDeadLetter and refreshes', async () => {
    // First call returns 2 events, second call (after retry) returns 1
    mockListDeadLetters
      .mockResolvedValueOnce({
        items: SAMPLE_EVENTS,
        total: 2,
        limit: 50,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [SAMPLE_EVENTS[1]],
        total: 1,
        limit: 50,
        offset: 0,
      });

    mockRetryDeadLetter.mockResolvedValueOnce({
      id: 'evt-111-aaa',
      status: 'pending',
      message: 'Queued for retry',
    });

    render(<JobsPage />);
    await waitFor(() => {
      expect(screen.getByTestId('retry-evt-111-aaa')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('retry-evt-111-aaa'));

    await waitFor(() => {
      expect(mockRetryDeadLetter).toHaveBeenCalledWith('evt-111-aaa');
    });

    // List should have been refreshed
    await waitFor(() => {
      expect(mockListDeadLetters).toHaveBeenCalledTimes(2);
    });
  });

  it('shows error when list API fails', async () => {
    mockListDeadLetters.mockRejectedValue(new Error('Network error'));

    render(<JobsPage />);
    await waitFor(() => {
      expect(screen.getByTestId('jobs-error')).toHaveTextContent('Failed to load dead-letter events');
    });
  });

  it('view logs shows saga detail panel', async () => {
    mockListDeadLetters.mockResolvedValue({
      items: SAMPLE_EVENTS,
      total: 2,
      limit: 50,
      offset: 0,
    });

    mockGetSagaLogs.mockResolvedValueOnce({
      saga_id: 'evt-111-aaa',
      saga_type: 'dispatch_job',
      status: 'failed',
      current_step: 2,
      context: { job_id: 'j1' },
      last_error: 'Step failed',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:01:00Z',
    });

    render(<JobsPage />);
    await waitFor(() => {
      expect(screen.getByTestId('logs-evt-111-aaa')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('logs-evt-111-aaa'));

    await waitFor(() => {
      expect(screen.getByTestId('saga-logs-panel')).toBeInTheDocument();
    });
  });
});
