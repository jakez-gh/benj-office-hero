import { describe, it, expect } from 'vitest';
import { User } from './index';

describe('types module', () => {
  describe('User interface', () => {
    it('should have required properties', () => {
      const user: User = {
        id: '123',
        email: 'user@example.com',
        name: 'John Doe'
      };

      expect(user.id).toBeDefined();
      expect(user.email).toBeDefined();
      expect(user.name).toBeDefined();
    });

    it('should type check user objects', () => {
      const user: User = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User'
      };

      // Verify types are correct
      expect(typeof user.id).toBe('string');
      expect(typeof user.email).toBe('string');
      expect(typeof user.name).toBe('string');
    });
  });
});
