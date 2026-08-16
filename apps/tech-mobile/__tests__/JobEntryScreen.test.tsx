import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { jest } from '@jest/globals';
import JobEntryScreen from '../JobEntryScreen';
import * as api from '@office-hero/api-client';

jest.mock('@office-hero/api-client');

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

  it('shows alert on job creation failure (Error instance)', async () => {
    jest.spyOn(api, 'createJob').mockRejectedValue(new Error('Server error'));
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const onCreated = jest.fn();

    const { getByPlaceholderText, getByText } = render(
      <JobEntryScreen token="tok" onCreated={onCreated} />
    );

    fireEvent.changeText(getByPlaceholderText('Customer Name'), 'Alice');
    fireEvent.changeText(getByPlaceholderText('Address'), '1 Road');
    fireEvent.press(getByText('Create Job'));

    await waitFor(() =>
      expect(alertSpy).toHaveBeenCalledWith('Error', 'Server error')
    );
    expect(onCreated).not.toHaveBeenCalled();

    alertSpy.mockRestore();
  });

  it('shows string representation when error is not an Error instance', async () => {
    jest.spyOn(api, 'createJob').mockRejectedValue('unexpected failure');
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const onCreated = jest.fn();

    const { getByPlaceholderText, getByText } = render(
      <JobEntryScreen token="tok" onCreated={onCreated} />
    );

    fireEvent.changeText(getByPlaceholderText('Customer Name'), 'Bob');
    fireEvent.changeText(getByPlaceholderText('Address'), '2 Lane');
    fireEvent.press(getByText('Create Job'));

    await waitFor(() =>
      expect(alertSpy).toHaveBeenCalledWith('Error', 'unexpected failure')
    );

    alertSpy.mockRestore();
  });

  it('shows validation alert when required fields are missing', async () => {
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);

    const { getByText } = render(<JobEntryScreen token="tok" />);
    fireEvent.press(getByText('Create Job'));

    await waitFor(() =>
      expect(alertSpy).toHaveBeenCalledWith('Required', 'Customer name and address are required')
    );

    alertSpy.mockRestore();
  });
});
