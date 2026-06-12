import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { jest } from '@jest/globals';
import RouteScreen from '../RouteScreen';
import * as api from '@office-hero/api-client';
import type { Route } from '@office-hero/types';

// Full manual mock — `requireActual` evaluates the api-client's module-scope
// base-URL detection, which crashes in the RN jest environment. The mocked
// RateLimitError preserves `instanceof` semantics (component and test share
// this class via the mocked module).
jest.mock('@office-hero/api-client', () => {
  class RateLimitError extends Error {
    retryAfter: number;
    constructor(retryAfter: number, message?: string) {
      super(message ?? `Rate limited. Retry after ${retryAfter}s.`);
      this.name = 'RateLimitError';
      this.retryAfter = retryAfter;
    }
  }
  return {
    __esModule: true,
    RateLimitError,
    getDailyRoute: jest.fn(),
    acknowledgeStop: jest.fn(),
  };
});
jest.mock('../LocationService', () => ({
  startLocationTracking: jest.fn(),
}));

describe('RouteScreen', () => {
  const sampleRoute: Route = {
    id: 'route1',
    date: '2026-03-08',
    vehicleId: 'veh1',
    stops: [
      { id: 'stop1', address: '123 Main', latitude: 0, longitude: 0, acknowledged: false },
    ],
  };

  it('fetches and displays stops and starts location tracking', async () => {
    jest.spyOn(api, 'getDailyRoute').mockResolvedValue(sampleRoute);
    const nav = { navigate: jest.fn() };
    const { getByText } = render(<RouteScreen token="tok" navigation={nav} />);
    await waitFor(() => expect(getByText('123 Main')).toBeTruthy());
    const locSvc = require('../LocationService');
    expect(locSvc.startLocationTracking).toHaveBeenCalledWith('tok', 'veh1');
  });

  it('acknowledges stop when button pressed', async () => {
    jest.spyOn(api, 'getDailyRoute').mockResolvedValue(sampleRoute);
    const ackSpy = jest.spyOn(api, 'acknowledgeStop').mockResolvedValue({ success: true });
    const nav = { navigate: jest.fn() };
    const { getByText } = render(<RouteScreen token="tok" navigation={nav} />);
    await waitFor(() => getByText('123 Main'));
    fireEvent.press(getByText('Acknowledge'));
    await waitFor(() => expect(ackSpy).toHaveBeenCalledWith('tok', 'stop1'));
  });

  it('navigates to job entry when New Job pressed', async () => {
    jest.spyOn(api, 'getDailyRoute').mockResolvedValue(sampleRoute);
    const nav = { navigate: jest.fn() };
    const { getByText } = render(<RouteScreen token="tok" navigation={nav} />);
    await waitFor(() => getByText("Today's Stops"));
    fireEvent.press(getByText('New Job'));
    expect(nav.navigate).toHaveBeenCalledWith('JobEntry');
  });
});
