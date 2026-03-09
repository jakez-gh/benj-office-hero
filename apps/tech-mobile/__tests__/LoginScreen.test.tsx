import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
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
});
