import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OnboardingChecklist } from '../components/OnboardingChecklist';
import * as apiClient from '@office-hero/api-client';
import * as adminApi from '../api';

jest.mock('@office-hero/api-client', () => ({
  listCustomers: jest.fn(),
  listVehicles: jest.fn(),
}));

jest.mock('../api', () => ({
  listJobsApi: jest.fn(),
}));

function emptyProgress() {
  (apiClient.listCustomers as jest.Mock).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  (apiClient.listVehicles as jest.Mock).mockResolvedValue([]);
  (adminApi.listJobsApi as jest.Mock).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
}

beforeEach(() => {
  localStorage.clear();
  emptyProgress();
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('OnboardingChecklist', () => {
  it('shows all four steps when no data exists', async () => {
    render(<OnboardingChecklist />);
    await waitFor(() => expect(screen.getByText(/getting started/i)).toBeInTheDocument());
    expect(screen.getByText(/add your first customer/i)).toBeInTheDocument();
    expect(screen.getByText(/add a vehicle/i)).toBeInTheDocument();
    expect(screen.getByText(/create a job/i)).toBeInTheDocument();
    expect(screen.getByText(/schedule and dispatch/i)).toBeInTheDocument();
  });

  it('marks customer step complete when customers exist', async () => {
    (apiClient.listCustomers as jest.Mock).mockResolvedValue({ items: [{ id: 'c1' }], total: 1, page: 1, page_size: 50 });
    render(<OnboardingChecklist />);
    await waitFor(() => expect(screen.getByText(/add your first customer/i)).toBeInTheDocument());
    const completed = screen.getAllByLabelText('Complete');
    expect(completed).toHaveLength(1);
  });

  it('auto-dismisses when a dispatched job exists', async () => {
    (apiClient.listCustomers as jest.Mock).mockResolvedValue({ items: [{ id: 'c1' }], total: 1, page: 1, page_size: 50 });
    (apiClient.listVehicles as jest.Mock).mockResolvedValue([{ id: 'v1' }]);
    (adminApi.listJobsApi as jest.Mock).mockResolvedValue({
      items: [{ id: 'j1', status: 'scheduled' }],
      total: 1,
      limit: 50,
      offset: 0,
    });

    render(<OnboardingChecklist />);
    await waitFor(() => expect(screen.queryByText(/getting started/i)).not.toBeInTheDocument());
    expect(localStorage.getItem('oh_onboarding_dismissed')).toBe('1');
  });

  it('does not render when already dismissed', () => {
    localStorage.setItem('oh_onboarding_dismissed', '1');
    render(<OnboardingChecklist />);
    expect(screen.queryByText(/getting started/i)).not.toBeInTheDocument();
  });

  it('hides when all three setup steps are complete', async () => {
    (apiClient.listCustomers as jest.Mock).mockResolvedValue({ items: [{ id: 'c1' }], total: 1, page: 1, page_size: 50 });
    (apiClient.listVehicles as jest.Mock).mockResolvedValue([{ id: 'v1' }]);
    (adminApi.listJobsApi as jest.Mock).mockResolvedValue({
      items: [{ id: 'j1', status: 'pending' }],
      total: 1,
      limit: 50,
      offset: 0,
    });

    render(<OnboardingChecklist />);
    await waitFor(() => expect(screen.queryByText(/getting started/i)).not.toBeInTheDocument());
  });

  it('dismiss button sets localStorage and hides widget', async () => {
    const user = userEvent.setup();
    render(<OnboardingChecklist />);
    await waitFor(() => expect(screen.getByText(/getting started/i)).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(screen.queryByText(/getting started/i)).not.toBeInTheDocument();
    expect(localStorage.getItem('oh_onboarding_dismissed')).toBe('1');
  });
});
