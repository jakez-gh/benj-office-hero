---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
dateUpdated: 20260308
status: in_progress
---

# Slice Design 008: Frontend Scaffold

This is the fifth *foundation* slice, establishing the monorepo structure for all client-side applications (web and mobile).
It creates the shared package infrastructure for API types and client code, and scaffolds three applications: admin-web,
tech-web, and tech-mobile.

This slice provides the structural foundation required by all subsequent frontend slices.

## Goals

* Initialize `pnpm` workspaces for shared packages and applications.
* Create `@office-hero/types` package with shared TypeScript interfaces (User, Job, Route, Vehicle, Tenant, AuthTokens).
* Create `@office-hero/api-client` package with axios-based HTTP client and auth functions (login, refresh, logout).
* Create `apps/admin-web` with Vite + React + TypeScript scaffold.
* Create `apps/tech-web` (lightweight technician web view) scaffold.
* Create `apps/tech-mobile` (React Native Expo) placeholder for full implementation in Slice 6.
* Configure ESLint, Prettier, and TypeScript across all workspaces.
* Set up GitHub Actions workflow for frontend CI/CD (install, lint, build, test).
* Establish baseline unit tests (Vitest for packages, Jest for apps).

## Structure

```text
frontend-root/
├── pnpm-workspace.yaml
├── package.json (root)
├── tsconfig.json
├── .eslintrc.js
├── .prettierrc
├── .github/workflows/frontend-ci.yml
│
├── packages/
│   ├── types/
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── index.ts        # User, Job, Route, Vehicle, Tenant, AuthTokens
│   │   │   └── index.test.ts   # smoke test
│   │   └── tsconfig.json
│   │
│   └── api-client/
│       ├── package.json
│       ├── src/
│       │   ├── index.ts        # axios client instance + exports
│       │   ├── auth.ts         # login, refresh, logout
│       │   └── auth.test.ts    # unit tests for auth module
│       ├── vitest.config.ts
│       └── tsconfig.json
│
├── apps/
│   ├── admin-web/
│   │   ├── package.json
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── playwright.config.ts
│   │   ├── src/
│   │   │   ├── main.tsx        # React entry point
│   │   │   ├── App.tsx         # main app component with routing
│   │   │   ├── auth.tsx        # Auth context + provider
│   │   │   ├── components/
│   │   │   │   ├── LoginPage.tsx
│   │   │   │   └── NavShell.tsx
│   │   │   ├── pages/
│   │   │   │   ├── JobsPage.tsx
│   │   │   │   ├── DispatchPage.tsx
│   │   │   │   ├── VehiclesPage.tsx
│   │   │   │   └── UsersPage.tsx
│   │   │   └── __tests__/
│   │   │       └── App.test.tsx
│   │   ├── src/e2e/
│   │   │   └── login.spec.ts
│   │   └── tsconfig.json
│   │
│   ├── tech-web/
│   │   ├── package.json
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── src/
│   │   │   └── main.tsx        # lightweight placeholder
│   │   └── tsconfig.json
│   │
│   └── tech-mobile/
│       ├── package.json
│       ├── app.json (Expo config)
│       ├── src/
│       │   ├── index.ts
│       │   └── App.tsx         # React Native placeholder
│       └── tsconfig.json
```

## Key Implementation Details

### Packages

#### `@office-hero/types`

* Defines all shared TypeScript interfaces used across frontend applications.
* Includes User, Job, Route, Vehicle, Tenant, and token-related types.
* Smoke tests verify types compile correctly (Vitest).

#### `@office-hero/api-client`

* Axios HTTP client instance configured with baseURL `/api`.
* Auth module with:
  * `login(credentials): Promise<LoginResponse>` — POST /auth/login
  * `refresh(refreshToken): Promise<LoginResponse>` — POST /auth/refresh
  * `logout(refreshToken): Promise<void>` — POST /auth/logout
* Interceptors configured (added in Slice 5a for 401 → refresh → retry logic).
* Unit tests (Vitest) cover auth functions, error handling, and interface contracts.

### Applications

#### `admin-web` (Vite + React)

* **Entry point:** `index.html` → `src/main.tsx`
* **Auth context:** `src/auth.tsx` manages login state and token persistence.
* **Routing:** React Router with protected layout (NavShell).
* **Pages:** Placeholder pages for Jobs, Dispatch, Vehicles, Users (all marked "Coming soon").
* **Tests:**
  * Jest unit tests for App component (login/logout flow, auth persistence).
  * Playwright E2E tests for login flow and navigation.

#### `tech-web`

* Minimal Vite + React scaffold for technician-facing web view.
* Placeholder for future implementation in feature slices.

#### `tech-mobile`

* React Native Expo placeholder (full implementation in Slice 6).
* Includes app.json with Android build config and expo-location plugin setup.
* Demonstrates theming and basic UI layout.

### CI/CD

GitHub Actions workflow (`.github/workflows/frontend-ci.yml`):

* **Install & Build job:** `pnpm install`, lint, build all apps/packages.
* **E2E job:** Runs Playwright tests (browser-based login flow validation).
* Triggers on pushes/PRs to all branches with path filters.

## Deliverables

### Completed

* [x] pnpm monorepo initialized with workspace configuration
* [x] `@office-hero/types` package with shared interfaces
* [x] `@office-hero/api-client` package with auth module
* [x] `apps/admin-web` with Vite + React + TypeScript
* [x] `apps/tech-web` scaffold
* [x] `apps/tech-mobile` Expo placeholder
* [x] ESLint + Prettier configured workspace-wide
* [x] Unit tests (Jest for admin-web, Vitest for packages)
* [x] Playwright E2E test scaffold for login flow
* [x] GitHub Actions frontend CI workflow
* [x] All builds passing (`pnpm build` succeeds)

### Testing Status

* ✅ `pnpm install` completes without errors
* ✅ `pnpm -r run build` succeeds for all packages/apps
* ✅ `pnpm -r run test` passes (admin-web Jest tests, Vitest setup ready)
* ✅ Playwright E2E tests runnable (requires running dev server)

## Notes

* The `/api` proxy in vite.config.ts points to `http://localhost:8000` (backend API).
  This will be configured per environment in later slices.
* Auth tokens are stored in localStorage (access_token, refresh_token).
  Production should consider secure cookie storage.
* The refresh retry interceptor logic is added in Slice 5a; this slice provides the
  foundation and base API client.
* Placeholder pages use inline styles; styling framework (Tailwind, CSS Modules, etc.)
  will be selected in Slice 5a.

## Success Criteria Met

✅ Monorepo structure in place and working
✅ Shared packages importable across apps
✅ All three app templates created and buildable
✅ TypeScript strict mode enabled across all projects
✅ ESLint + Prettier configured and passing
✅ Unit and E2E test infrastructure in place
✅ CI/CD pipeline configured and working
✅ Ready for Slice 5a (Auth & Admin Shell) implementation
