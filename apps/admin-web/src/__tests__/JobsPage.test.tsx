import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockListDeadLetters = jest.fn();
const mockRetryDeadLetter = jest.fn();

jest.mock('../api', () => ({
  listDeadLetters: (...args: unknown[]) => mockListDeadLetters(...args),
  retryDeadLetter: (...args: unknown[]) => mockRetryDeadLetter(...args),
}));

import { JobsPage } from '../pages/JobsPage';

const buildItem = (overrides: Record<string, unknown> = {}) => ({
  id: 'evt-1',
  tenant_id: 'tenant-1',
  event_type: 'dispatch_job',
  payload: {},
  status: 'dead',
  attempt_count: 3,
  created_at: null,
  processed_at: null,
  dead_letter_reason: 'max retries exceeded',
  ...overrides,
});

describe('JobsPage (dead-letter)', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('shows loading state initially', () => {
    mockListDeadLetters.mockReturnValue(new Promise(() => {}));
    render(<JobsPage />);
    expect(screen.getByText('Loading dead-letter events…')).toBeInTheDocument();
  });

  it('renders dead-letter events in a table on success', async () => {
    mockListDeadLetters.mockResolvedValue({
      items: [
        buildItem({ id: 'evt-1', event_type: 'dispatch_job' }),
        buildItem({ id: 'evt-2', event_type: 'sync_customer', attempt_count: 5 }),
      ],
      total: 2,
      limit: 50,
      offset: 0,
    });

    render(<JobsPage />);

    await waitFor(() => {
      const rows = screen.getAllByTestId('dead-letter-row');
      expect(rows).toHaveLength(2);
    });

    expect(screen.getByText('evt-1')).toBeInTheDocument();
    expect(screen.getByText('evt-2')).toBeInTheDocument();
    expect(screen.getByText('dispatch_job')).toBeInTheDocument();
    expect(screen.getByText('sync_customer')).toBeInTheDocument();
  });

  it('shows an empty message when no dead-letter events exist', async () => {
    mockListDeadLetters.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });

    render(<JobsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No dead-letter events/i)).toBeInTheDocument();
    });
  });

  it('retries a dead-letter and refreshes the list', async () => {
    mockListDeadLetters
      .mockResolvedValueOnce({ items: [buildItem()], total: 1, limit: 50, offset: 0 })
      .mockResolvedValueOnce({ items: [], total: 0, limit: 50, offset: 0 });
    mockRetryDeadLetter.mockResolvedValue({ id: 'evt-1', status: 'pending', message: 'ok' });

    render(<JobsPage />);

    const retryBtn = await screen.findByRole('button', { name: /Retry/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(mockRetryDeadLetter).toHaveBeenCalledWith('evt-1');
    });

    await waitFor(() => {
      expect(screen.getByText(/No dead-letter events/i)).toBeInTheDocument();
    });
  });

  it('shows an error when listDeadLetters fails', async () => {
    mockListDeadLetters.mockRejectedValue({ status: 500, detail: 'boom' });

    render(<JobsPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('boom');
  });

  it('shows an error when retry fails', async () => {
    mockListDeadLetters.mockResolvedValue({
      items: [buildItem()],
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockRetryDeadLetter.mockRejectedValue({ status: 400, detail: 'cannot retry' });

    render(<JobsPage />);

    const retryBtn = await screen.findByRole('button', { name: /Retry/i });
    fireEvent.click(retryBtn);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('cannot retry');
  });
});
