import '@testing-library/jest-dom';

// provide the version variable used by NavShell
// eslint-disable-next-line @typescript-eslint/no-explicit-any
// declare global for TypeScript
// eslint-disable-next-line @typescript-eslint/no-unused-vars
declare var global: any;
global.__APP_VERSION__ = 'test';
