import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { jest } from '@jest/globals';
import LoginScreen from '../LoginScreen';
import * as api from '@office-hero/api-client';

jest.mock('@office-hero/api-client');

describe('LoginScreen', () => {
  it('renders username and password inputs and a login button', () => {
    const onLogin = jest.fn();
    const { getByPlaceholderText, getByText } = render(<LoginScreen onLogin={onLogin} />);
    expect(getByPlaceholderText('Username')).toBeTruthy();
    expect(getByPlaceholderText('Password')).toBeTruthy();
    expect(getByText('Log in')).toBeTruthy();
  });

  it('calls api.login and invokes onLogin on success', async () => {
    const fakeLogin = jest.spyOn(api, 'login').mockResolvedValue({ token: 'tok' });
    const onLogin = jest.fn();

    const { getByPlaceholderText, getByText } = render(
      <LoginScreen onLogin={onLogin} />
    );

    fireEvent.changeText(getByPlaceholderText('Username'), 'user');
    fireEvent.changeText(getByPlaceholderText('Password'), 'pass');
    fireEvent.press(getByText('Log in'));

    await waitFor(() => expect(fakeLogin).toHaveBeenCalled());
    expect(onLogin).toHaveBeenCalledWith('tok');
  });

  it('shows alert on login failure (Error instance)', async () => {
    jest.spyOn(api, 'login').mockRejectedValue(new Error('Network error'));
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const onLogin = jest.fn();

    const { getByPlaceholderText, getByText } = render(
      <LoginScreen onLogin={onLogin} />
    );

    fireEvent.changeText(getByPlaceholderText('Username'), 'user');
    fireEvent.changeText(getByPlaceholderText('Password'), 'pass');
    fireEvent.press(getByText('Log in'));

    await waitFor(() =>
      expect(alertSpy).toHaveBeenCalledWith('Login failed', 'Network error')
    );
    expect(onLogin).not.toHaveBeenCalled();

    alertSpy.mockRestore();
  });

  it('shows string representation when error is not an Error instance', async () => {
    jest.spyOn(api, 'login').mockRejectedValue('unexpected string error');
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const onLogin = jest.fn();

    const { getByPlaceholderText, getByText } = render(
      <LoginScreen onLogin={onLogin} />
    );

    fireEvent.changeText(getByPlaceholderText('Username'), 'user');
    fireEvent.changeText(getByPlaceholderText('Password'), 'pass');
    fireEvent.press(getByText('Log in'));

    await waitFor(() =>
      expect(alertSpy).toHaveBeenCalledWith('Login failed', 'unexpected string error')
    );

    alertSpy.mockRestore();
  });
});
