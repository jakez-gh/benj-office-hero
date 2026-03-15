import fetch from 'cross-fetch';
import * as client from '../src/index';
import { RateLimitError } from '../src/index';
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

  // -----------------------------------------------------------------------
  // 429 Rate Limit Handling (Slice 4)
  // -----------------------------------------------------------------------

  it('login throws RateLimitError on 429 with Retry-After header', async () => {
    mockedFetch.mockResolvedValue({
      ok: false,
      status: 429,
      headers: { get: (h: string) => (h === 'Retry-After' ? '30' : null) },
      json: async () => ({ detail: 'Too many requests', retry_after: 30, request_id: null }),
    } as any);

    await expect(client.login({ username: 'u', password: 'p' })).rejects.toThrow(RateLimitError);

    try {
      await client.login({ username: 'u', password: 'p' });
    } catch (err) {
      expect(err).toBeInstanceOf(RateLimitError);
      expect((err as RateLimitError).retryAfter).toBe(30);
    }
  });

  it('getDailyRoute throws RateLimitError on 429', async () => {
    mockedFetch.mockResolvedValue({
      ok: false,
      status: 429,
      headers: { get: () => '60' },
      json: async () => ({ detail: 'Too many requests', retry_after: 60, request_id: null }),
    } as any);

    await expect(client.getDailyRoute('tok')).rejects.toThrow(RateLimitError);
  });

  it('createJob throws RateLimitError on 429', async () => {
    mockedFetch.mockResolvedValue({
      ok: false,
      status: 429,
      headers: { get: () => '45' },
      json: async () => ({ detail: 'Too many requests', retry_after: 45, request_id: null }),
    } as any);

    await expect(client.createJob('tok', { customerName: 'A', address: 'B' })).rejects.toThrow(RateLimitError);
  });

  it('non-429 errors still throw generic Error', async () => {
    mockedFetch.mockResolvedValue({
      ok: false,
      status: 500,
      headers: { get: () => null },
    } as any);

    await expect(client.login({ username: 'u', password: 'p' })).rejects.toThrow('login failed: 500');
  });

  // -----------------------------------------------------------------------
  // Audit Events (Slice 4)
  // -----------------------------------------------------------------------

  it('getAuditEvents fetches paginated audit events', async () => {
    const page = { items: [], total: 0, limit: 50, offset: 0 };
    mockedFetch.mockResolvedValue({ ok: true, json: async () => page } as any);
    const res = await client.getAuditEvents('tok');
    expect(res).toEqual(page);
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.stringContaining('/admin/audit-events'),
      expect.objectContaining({ headers: { Authorization: 'Bearer tok' } }),
    );
  });

  it('getAuditEvents passes query params', async () => {
    const page = { items: [], total: 0, limit: 10, offset: 5 };
    mockedFetch.mockResolvedValue({ ok: true, json: async () => page } as any);
    await client.getAuditEvents('tok', { limit: 10, offset: 5, event_type: 'auth.login' });
    const url = mockedFetch.mock.calls[0][0] as string;
    expect(url).toContain('limit=10');
    expect(url).toContain('offset=5');
    expect(url).toContain('event_type=auth.login');
  });
});
