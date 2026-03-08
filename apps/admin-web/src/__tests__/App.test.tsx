
// mock API client before any component imports
const mockLogin = jest.fn();
jest.mock('@office-hero/api-client', () => ({
  login: mockLogin
}));

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as api from '@office-hero/api-client';

describe('Admin web authentication and navigation', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.resetAllMocks();
    mockLogin.mockClear();
  });

  test('shows login form initially and allows successful login', async () => {
    mockLogin.mockResolvedValue({
      access_token: 'fake-token',
      refresh_token: 'r',
      token_type: 'bearer'
    });

    render(<App />);

    // login form should appear
    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'me@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => expect(mockLogin).toHaveBeenCalled());

    // after login, admin panel welcome message should show
    await waitFor(() => {
      expect(screen.getByText(/welcome to admin panel/i)).toBeInTheDocument();
    });

    // nav links should exist
    expect(screen.getByRole('link', { name: /jobs/i })).toBeInTheDocument();
    // version should render
    expect(screen.getByText(/vtest/i)).toBeInTheDocument();
  });

  test('login failure displays error message', async () => {
    mockLogin.mockRejectedValue(new Error('unauthorized'));

    render(<App />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'bad@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'bad' } });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    // wait for login API to be called (async handler)
    await waitFor(() => expect(mockLogin).toHaveBeenCalled());

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/invalid credentials/i);

    // confirm login API was invoked with correct args
    expect(mockLogin).toHaveBeenCalledWith({ email: 'bad@example.com', password: 'bad' });
  });

  test('logout returns to login screen', async () => {
    mockLogin.mockResolvedValue({
      access_token: 'fake-token',
      refresh_token: 'r',
      token_type: 'bearer'
    });

    render(<App />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'me@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => screen.getByText(/welcome to admin panel/i));

    fireEvent.click(screen.getByRole('button', { name: /logout/i }));

    expect(await screen.findByRole('heading', { name: /login/i })).toBeInTheDocument();
  });
});
