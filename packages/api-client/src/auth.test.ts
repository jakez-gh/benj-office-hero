import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { login, LoginRequest, LoginResponse } from './auth';

// Mock axios
vi.mock('./index', () => ({
  client: {
    post: vi.fn()
  }
}));

import { client } from './index';

describe('auth module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('login', () => {
    it('should send login credentials to /auth/login endpoint', async () => {
      const credentials: LoginRequest = {
        email: 'user@example.com',
        password: 'password123'
      };

      const mockResponse: LoginResponse = {
        access_token: 'access_token_value',
        refresh_token: 'refresh_token_value',
        token_type: 'bearer'
      };

      (client.post as any).mockResolvedValueOnce({ data: mockResponse });

      const result = await login(credentials);

      expect(client.post).toHaveBeenCalledWith('/auth/login', credentials);
      expect(result).toEqual(mockResponse);
      expect(result.token_type).toBe('bearer');
    });

    it('should handle login errors', async () => {
      const credentials: LoginRequest = {
        email: 'user@example.com',
        password: 'wrongpassword'
      };

      const error = new Error('Unauthorized');
      (client.post as any).mockRejectedValueOnce(error);

      await expect(login(credentials)).rejects.toThrow('Unauthorized');
    });

    it('should return tokens with correct types', async () => {
      const credentials: LoginRequest = {
        email: 'admin@example.com',
        password: 'adminpass'
      };

      const mockResponse: LoginResponse = {
        access_token: 'abc123',
        refresh_token: 'xyz789',
        token_type: 'bearer'
      };

      (client.post as any).mockResolvedValueOnce({ data: mockResponse });

      const result = await login(credentials);

      expect(typeof result.access_token).toBe('string');
      expect(typeof result.refresh_token).toBe('string');
      expect(result.token_type).toBe('bearer');
    });
  });

  describe('LoginRequest interface', () => {
    it('should accept email and password fields', () => {
      const request: LoginRequest = {
        email: 'test@example.com',
        password: 'pass'
      };

      expect(request.email).toBeDefined();
      expect(request.password).toBeDefined();
    });
  });

  describe('LoginResponse interface', () => {
    it('should contain access_token, refresh_token, and token_type', () => {
      const response: LoginResponse = {
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer'
      };

      expect(response.access_token).toBeDefined();
      expect(response.refresh_token).toBeDefined();
      expect(response.token_type).toBe('bearer');
    });
  });
});
