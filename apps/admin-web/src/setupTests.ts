import '@testing-library/jest-dom';

// provide the version variable used by NavShell
(globalThis as Record<string, unknown>).__APP_VERSION__ = 'test';
