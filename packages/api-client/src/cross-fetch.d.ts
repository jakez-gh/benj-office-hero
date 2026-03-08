// provide a minimal ambient declaration for cross-fetch
// so that TypeScript can compile without installing @types

declare module 'cross-fetch' {
  const fetch: typeof globalThis.fetch;
  export default fetch;
}
