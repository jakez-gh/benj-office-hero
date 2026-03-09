import fetch from 'cross-fetch';
import * as client from '../src/index';
import type { Route } from '@office-hero/types';

jest.mock('cross-fetch', () => jest.fn());
const mockedFetch = fetch as jest.MockedFunction<typeof fetch>;

describe('api-client', () => {
  beforeEach(() => {
    mockedFetch.mockReset();
    process.env.OFFICE_HERO_API_URL = 'http://test';
  });

  it('login posts credentials', async () => {
    mockedFetch.mockResolvedValue({ ok: true, json: async () => ({ token: 't' }) } as any);
    const res = await client.login({ username: 'u', password: 'p' });
    expect(mockedFetch).toHaveBeenCalledWith('http://test/login', expect.any(Object));
    expect(res.token).toBe('t');
  });

  it('getDailyRoute fetches and parses route', async () => {
    const sample: Route = { id: 'r', date: 'd', stops: [] };
    mockedFetch.mockResolvedValue({ ok: true, json: async () => sample } as any);
    const res = await client.getDailyRoute('tok');
    expect(res).toEqual(sample);
  });

  it('createJob posts job data and returns id', async () => {
    const job = { customerName: 'Alice', address: '1 Road' };
    mockedFetch.mockResolvedValue({ ok: true, json: async () => ({ jobId: 'j1' }) } as any);
    const res = await client.createJob('tok', job);
    expect(mockedFetch).toHaveBeenCalledWith('http://test/jobs', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify(job),
    }));
    expect(res.jobId).toBe('j1');
  });
});
