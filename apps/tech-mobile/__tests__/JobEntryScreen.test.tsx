import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { jest } from '@jest/globals';
import JobEntryScreen from '../JobEntryScreen';
import * as api from '@office-hero/api-client';

// Partial mock: stub the network functions but keep error classes real.
// (Pick exports individually — spreading the module evaluates every lazy
// getter, which breaks on browser-only initialisation code.)
jest.mock('@office-hero/api-client', () => {
  const actual = jest.requireActual('@office-hero/api-client') as Record<string, unknown>;
  return {
    __esModule: true,
    RateLimitError: actual.RateLimitError,
    createJob: jest.fn(),
  };
});

describe('JobEntryScreen', () => {
  it('renders inputs and create button', () => {
    const { getByPlaceholderText, getByText } = render(<JobEntryScreen token="tok" />);
    expect(getByPlaceholderText('Customer Name')).toBeTruthy();
    expect(getByPlaceholderText('Address')).toBeTruthy();
    expect(getByText('Create Job')).toBeTruthy();
  });

  it('calls createJob with form data', async () => {
    const spy = jest.spyOn(api, 'createJob').mockResolvedValue({ jobId: 'j1' });
    const onCreated = jest.fn();
    const { getByPlaceholderText, getByText } = render(
      <JobEntryScreen token="tok" onCreated={onCreated} />
    );

    fireEvent.changeText(getByPlaceholderText('Customer Name'), 'Alice');
    fireEvent.changeText(getByPlaceholderText('Address'), '1 Road');
    fireEvent.press(getByText('Create Job'));

    await waitFor(() => expect(spy).toHaveBeenCalledWith('tok', expect.objectContaining({ customerName: 'Alice' })));
    expect(onCreated).toHaveBeenCalledWith('j1');
  });
});
