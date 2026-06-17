import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import * as api from '../api';

// ── Helpers ──────────────────────────────────────────────────────────────────

const VEHICLE_ID = 'veh-001';
const WORK_DATE = '2026-06-17';

function makeJob(overrides: Partial<api.JobSummary> = {}): api.JobSummary {
  return {
    id: 'job-001',
    title: 'Fix boiler',
    status: 'scheduled',
    service_type: 'Plumbing',
    scheduled_for: '2026-06-17T09:00:00Z',
    priority: 50,
    customer_id: 'cust-aaaa-bbbb-cccc',
    location_id: 'loc-aaaa-bbbb-cccc',
    estimated_duration_min: 60,
    ...overrides,
  };
}

// ── Stubs ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.spyOn(api, 'getToken').mockReturnValue(null);
  vi.spyOn(api, 'setToken').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Login view ────────────────────────────────────────────────────────────────

describe('LoginView', () => {
  it('renders sign-in form when no token', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /office hero/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls loginApi and transitions to loading on success', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'loginApi').mockResolvedValue({ access_token: 'tok-123', token_type: 'bearer' });
    vi.spyOn(api, 'myCrewTodayApi').mockReturnValue(new Promise(() => {})); // hang

    render(<App />);
    await user.type(screen.getByLabelText(/email/i), 'tech@example.com');
    await user.type(screen.getByLabelText(/password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(api.loginApi).toHaveBeenCalledWith('tech@example.com', 'secret');
    expect(api.setToken).toHaveBeenCalledWith('tok-123');
    await waitFor(() => expect(screen.getByText(/loading/i)).toBeInTheDocument());
  });

  it('shows error message when login fails', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'loginApi').mockRejectedValue(new api.ApiError(401, 'Invalid credentials'));

    render(<App />);
    await user.type(screen.getByLabelText(/email/i), 'bad@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /sign in/i })).not.toBeDisabled();
  });

  it('disables button while submitting', async () => {
    const user = userEvent.setup();
    let resolve: (v: api.LoginResponse) => void;
    vi.spyOn(api, 'loginApi').mockReturnValue(new Promise(r => { resolve = r; }));

    render(<App />);
    await user.type(screen.getByLabelText(/email/i), 'tech@example.com');
    await user.type(screen.getByLabelText(/password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
    resolve!({ access_token: 'tok', token_type: 'bearer' });
  });
});

// ── Today view ────────────────────────────────────────────────────────────────

describe('TodayView', () => {
  beforeEach(() => {
    vi.spyOn(api, 'getToken').mockReturnValue('existing-token');
    vi.spyOn(api, 'myCrewTodayApi').mockResolvedValue({
      crew_id: 'crew-1',
      vehicle_id: VEHICLE_ID,
      work_date: WORK_DATE,
    });
  });

  it('shows job list after loading', async () => {
    vi.spyOn(api, 'listJobsApi').mockResolvedValue({
      items: [makeJob({ title: 'Fix boiler' }), makeJob({ id: 'job-002', title: 'Service AC' })],
      total: 2,
    });

    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    expect(screen.getByText('Service AC')).toBeInTheDocument();
  });

  it('shows empty state when no jobs', async () => {
    vi.spyOn(api, 'listJobsApi').mockResolvedValue({ items: [], total: 0 });

    render(<App />);
    await waitFor(() => expect(screen.getByText(/no jobs assigned today/i)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /enter a job/i })).toBeInTheDocument();
  });

  it('shows error state when list fetch fails', async () => {
    vi.spyOn(api, 'listJobsApi').mockRejectedValue(new api.ApiError(503, 'Service unavailable'));

    render(<App />);
    await waitFor(() => expect(screen.getByText(/service unavailable/i)).toBeInTheDocument());
  });

  it('shows no-crew state when 404 on myCrewToday', async () => {
    vi.spyOn(api, 'getToken').mockReturnValue('existing-token');
    vi.spyOn(api, 'myCrewTodayApi').mockRejectedValue(new api.ApiError(404, 'No crew'));

    render(<App />);
    await waitFor(() =>
      expect(screen.getByText(/no vehicle assignment found/i)).toBeInTheDocument()
    );
  });

  it('redirects to login on 401 from myCrewToday', async () => {
    vi.spyOn(api, 'getToken').mockReturnValue('stale-token');
    vi.spyOn(api, 'myCrewTodayApi').mockRejectedValue(new api.ApiError(401, 'Expired'));

    render(<App />);
    await waitFor(() => expect(screen.getByLabelText(/email/i)).toBeInTheDocument());
    expect(api.setToken).toHaveBeenCalledWith(null);
  });
});

// ── Job detail view ───────────────────────────────────────────────────────────

describe('JobDetailView', () => {
  beforeEach(() => {
    vi.spyOn(api, 'getToken').mockReturnValue('tok');
    vi.spyOn(api, 'myCrewTodayApi').mockResolvedValue({
      crew_id: 'c',
      vehicle_id: VEHICLE_ID,
      work_date: WORK_DATE,
    });
    vi.spyOn(api, 'listJobsApi').mockResolvedValue({
      items: [makeJob()],
      total: 1,
    });
  });

  it('navigates to job detail on card click', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    await user.click(screen.getByText('Fix boiler'));
    expect(screen.getByRole('heading', { name: /job details/i })).toBeInTheDocument();
    expect(screen.getByText('Fix boiler')).toBeInTheDocument();
    expect(screen.getByText('Plumbing')).toBeInTheDocument();
  });

  it('shows "mark in progress" for scheduled job', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    await user.click(screen.getByText('Fix boiler'));
    expect(screen.getByRole('button', { name: /mark in progress/i })).toBeInTheDocument();
  });

  it('calls startJobApi and updates status', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'startJobApi').mockResolvedValue(makeJob({ status: 'in_progress' }));

    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    await user.click(screen.getByText('Fix boiler'));
    await user.click(screen.getByRole('button', { name: /mark in progress/i }));

    expect(api.startJobApi).toHaveBeenCalledWith('job-001');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /mark complete/i })).toBeInTheDocument()
    );
  });

  it('shows "mark complete" for in_progress job', async () => {
    vi.spyOn(api, 'listJobsApi').mockResolvedValue({
      items: [makeJob({ status: 'in_progress' })],
      total: 1,
    });
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    await user.click(screen.getByText('Fix boiler'));
    expect(screen.getByRole('button', { name: /mark complete/i })).toBeInTheDocument();
  });

  it('calls completeJobApi when marking complete', async () => {
    vi.spyOn(api, 'listJobsApi').mockResolvedValue({
      items: [makeJob({ status: 'in_progress' })],
      total: 1,
    });
    vi.spyOn(api, 'completeJobApi').mockResolvedValue(makeJob({ status: 'completed' }));
    const user = userEvent.setup();

    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    await user.click(screen.getByText('Fix boiler'));
    await user.click(screen.getByRole('button', { name: /mark complete/i }));

    expect(api.completeJobApi).toHaveBeenCalledWith('job-001');
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /mark complete/i })).not.toBeInTheDocument()
    );
  });

  it('shows error when start fails', async () => {
    vi.spyOn(api, 'startJobApi').mockRejectedValue(new api.ApiError(409, 'Job already started'));
    const user = userEvent.setup();

    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    await user.click(screen.getByText('Fix boiler'));
    await user.click(screen.getByRole('button', { name: /mark in progress/i }));

    await waitFor(() => expect(screen.getByText(/job already started/i)).toBeInTheDocument());
  });

  it('navigates back to list', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText('Fix boiler')).toBeInTheDocument());
    await user.click(screen.getByText('Fix boiler'));
    await user.click(screen.getByRole('button', { name: /back/i }));
    expect(screen.getByRole('heading', { name: /my jobs today/i })).toBeInTheDocument();
  });
});

// ── New job view ──────────────────────────────────────────────────────────────

describe('NewJobView', () => {
  beforeEach(() => {
    vi.spyOn(api, 'getToken').mockReturnValue('tok');
    vi.spyOn(api, 'myCrewTodayApi').mockResolvedValue({
      crew_id: 'c',
      vehicle_id: VEHICLE_ID,
      work_date: WORK_DATE,
    });
    vi.spyOn(api, 'listJobsApi').mockResolvedValue({ items: [], total: 0 });
  });

  it('opens new job form via empty-state button', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByRole('button', { name: /enter a job/i })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /enter a job/i }));
    expect(screen.getByRole('heading', { name: /new job/i })).toBeInTheDocument();
  });

  it('submits form and returns to list on success', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'createJobApi').mockResolvedValue(makeJob({ title: 'Inspect pipes' }));
    vi.spyOn(api, 'listJobsApi')
      .mockResolvedValueOnce({ items: [], total: 0 })
      .mockResolvedValueOnce({ items: [makeJob({ title: 'Inspect pipes' })], total: 1 });

    render(<App />);
    await waitFor(() => expect(screen.getByRole('button', { name: /enter a job/i })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /enter a job/i }));

    await user.type(screen.getByLabelText(/job title/i), 'Inspect pipes');
    await user.type(screen.getByLabelText(/customer id/i), 'cust-0001');
    await user.type(screen.getByLabelText(/location id/i), 'loc-0001');
    await user.click(screen.getByRole('button', { name: /create job/i }));

    expect(api.createJobApi).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Inspect pipes', customer_id: 'cust-0001' })
    );
    await waitFor(() => expect(screen.getByText('Inspect pipes')).toBeInTheDocument());
  });

  it('shows error when job creation fails', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'createJobApi').mockRejectedValue(new api.ApiError(422, 'Validation error'));

    render(<App />);
    await waitFor(() => expect(screen.getByRole('button', { name: /enter a job/i })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /enter a job/i }));
    await user.type(screen.getByLabelText(/job title/i), 'Bad job');
    await user.type(screen.getByLabelText(/customer id/i), 'x');
    await user.type(screen.getByLabelText(/location id/i), 'y');
    await user.click(screen.getByRole('button', { name: /create job/i }));

    await waitFor(() => expect(screen.getByText(/validation error/i)).toBeInTheDocument());
  });
});
