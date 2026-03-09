---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: not_started
---

# Slice Design 008: Frontend scaffold

This is the fifth foundation slice. It sets up a pnpm monorepo with shared packages
(types, API client) and three front-end applications (admin web, tech web, tech mobile).
It establishes the TypeScript configuration, ESLint, Prettier, and build infrastructure
for the frontend ecosystem.

It corresponds to slice 5 in the slice plan.

## Goals

* Initialize pnpm workspace at repo root:
  * Create `pnpm-workspace.yaml` with workspace roots: `packages/*`, `apps/*`
  * Create `pnpm-lock.yaml` via `pnpm install`
  * Each app/package has its own `package.json` and `tsconfig.json`
* Create `packages/types/` — shared TypeScript types package:
  * `package.json` with `name: "@office-hero/types"`, `version: "0.1.0"`
  * `src/index.ts` — export all types
  * Types mirroring API schemas: `User`, `Job`, `Route`, `Vehicle`, `Tenant`, `AuthTokens`
  * `tsconfig.json` configured for `declaration: true` (emit `.d.ts`)
* Create `packages/api-client/` — typed HTTP client:
  * `package.json` with `name: "@office-hero/api-client"`, depends on `@office-hero/types`
  * `src/client.ts` — `ApiClient` class:
    * `login(email, password)` → `Promise\<AuthTokens\>`
    * `refresh(refreshToken)` → `Promise\<AuthTokens\>`
    * `logout()` → `Promise\<void\>`
    * Stores access token in memory, refresh token in memory (not localStorage; state management delegate to React Context)
    * Handles 401 responses with automatic silent refresh (calls refresh, retries original request)
  * `src/index.ts` — export ApiClient, AuthTokens type
  * `tsconfig.json`
* Create `apps/admin-web/` — Vite + React + TypeScript React SPA:
  * `vite.config.ts` — basic Vite config, React plugin, alias `@` → `src/`
  * `package.json` — `name: "admin-web"`, deps: `react`, `react-dom`, `react-router-dom`, `@office-hero/api-client`, `@office-hero/types`
  * `index.html` — loads `src/main.tsx`
  * `src/main.tsx` — ReactDOM.createRoot, render `<App />`
  * `src/App.tsx` — shell (will be filled in slice 5a)
  * `src/env.d.ts` — Vite client type definitions
  * `.eslintrc.json` — eslint-config-react recommended
  * `.prettierrc.json` — basic prettier config (2 spaces, single quote)
  * `tsconfig.json` — target ES2020, moduleResolution: bundler
* Create `apps/tech-web/` — same as admin-web, but lighter intent:
  * Vite + React + TypeScript, same setup
  * `src/App.tsx` — placeholder (for field technician web view)
* Create `apps/tech-mobile/` — React Native Expo placeholder:
  * `package.json` — `name: "tech-mobile"`, includes `expo`, `react-native`, `@office-hero/api-client`, `@office-hero/types`
  * `app.json` — Expo config with `name: "Office Hero"`, `slug: "office-hero"`, `android.package: "com.officehero.tech"`
  * `App.tsx` — placeholder; see Slice 6 for real implementation
  * Note: Do NOT run `npx create-expo-app` yet; just set up the directory structure and package.json
* Update `.github/workflows/ci.yml` to add frontend job:
  * `pnpm install` (installs all workspaces)
  * `pnpm -r run build` (builds all packages and apps)
  * `pnpm -r run test` (runs all test suites — will skip if no tests yet)
* Create `tests/` directory (or `apps/*/tests/` and `packages/*/tests/`):
  * `packages/api-client/tests/client.test.ts` — Vitest unit tests for login/refresh/logout
  * `packages/types/tests/types.test.ts` — smoke test: import all types, no errors
  * `apps/admin-web/e2e/` — Playwright config (no tests yet)
* Add `scripts/setup-frontend.sh` — convenience script:
  * `pnpm install`
  * `pnpm -r run build`

## Structure

```text
pnpm-workspace.yaml

packages/
├── types/
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts
│       ├── user.ts
│       ├── job.ts
│       ├── route.ts
│       ├── vehicle.ts
│       ├── tenant.ts
│       └── auth.ts
├── api-client/
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts
│       └── client.ts

apps/
├── admin-web/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .eslintrc.json
│   ├── .prettierrc.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       └── env.d.ts
├── tech-web/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .eslintrc.json
│   ├── .prettierrc.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       └── env.d.ts
└── tech-mobile/
    ├── package.json
    ├── app.json
    └── App.tsx
```

## Failing Tests Outline

```typescript
// packages/api-client/tests/client.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ApiClient } from '../src/client'

describe('ApiClient', () => {
  let client: ApiClient

  beforeEach(() => {
    client = new ApiClient('http://localhost:8000')
  })

  it('should login and return tokens', async () => {
    // Mock fetch to return tokens
    const tokens = await client.login('test@example.com', 'password')
    expect(tokens.access_token).toBeDefined()
    expect(tokens.refresh_token).toBeDefined()
  })

  it('should refresh tokens', async () => {
    const newTokens = await client.refresh('old-refresh-token')
    expect(newTokens.access_token).toBeDefined()
  })

  it('should handle 401 by auto-refreshing', async () => {
    // Setup: first call returns 401, second returns 200
    // Client should auto-refresh and retry
    const result = await client.get('/some-endpoint')
    expect(result).toBeDefined()
  })
})

// packages/types/tests/types.test.ts
import { describe, it, expect } from 'vitest'
import * as types from '../src/index'

describe('Types', () => {
  it('should export all types without errors', () => {
    expect(types.User).toBeDefined()
    expect(types.Job).toBeDefined()
    expect(types.AuthTokens).toBeDefined()
  })
})
```

## Dependencies

Depends on slice 1 (Python scaffold) only. Does not require slices 2–3 code; only their
existence ensures the API they will provide.

Slices 3 and 4 must be complete before testing the admin-web app in slice 5a.

## Effort

Estimate: 2/5. Most work is initialization: setting up pnpm workspaces, creating TypeScript
configs, and scaffolding apps. The API client is straightforward HTTP + token management.
Main concern: ensuring all build chains work together (pnpm linking, TypeScript, Vite, Playwright).

---

Once this design is approved, implementation proceeds with pnpm setup, then creating each
package/app directory, then integrating into CI. By the end, `pnpm run build` from the repo
root compiles all TypeScript and bundles all apps ready for deployment or static hosting.
