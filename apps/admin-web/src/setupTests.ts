import '@testing-library/jest-dom';

// provide the version variable used by NavShell
(globalThis as Record<string, unknown>).__APP_VERSION__ = 'test';
// dev-only routes (e.g. /_design) should be enabled in jsdom tests so they
// can be exercised; production builds replace this with the literal `false`.
(globalThis as Record<string, unknown>).__IS_DEV__ = true;
