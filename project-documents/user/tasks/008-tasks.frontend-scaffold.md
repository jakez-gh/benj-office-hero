---
docType: task-breakdown
parent: ../slices/008-slice.frontend-scaffold.md
project: office-hero
dateCreated: 20260308
dateUpdated: 20260308
status: in_progress
---

# Task Breakdown: Slice 5 — Frontend Scaffold

Phase 6 implementation tasks for pnpm monorepo, shared packages, and app scaffolds.

## Epic: Monorepo Setup & Infrastructure

### Task 5.1: Initialize pnpm Workspaces

**Status:** ✅ COMPLETED

- [x] Create `pnpm-workspace.yaml` with packages/*and apps/* globs
- [x] Create root `package.json` with workspace scripts (dev, build, lint, format)
- [x] Configure `tsconfig.json` (base configuration for all projects)
- [x] Add `.eslintrc.js` (workspace-wide ESLint rules)
- [x] Add `.prettierrc` (shared formatting rules)
- [x] Verify `pnpm install` completes without errors

**Verification:**

```bash
pnpm install
pnpm lint
```

---

### Task 5.2: Create `@office-hero/types` Package

**Status:** ✅ COMPLETED

- [x] Create `packages/types/` directory structure
- [x] Create `package.json` with TypeScript build script
- [x] Create `tsconfig.json` extending root config
- [x] Define shared interfaces in `src/index.ts`:
  - [x] `User` (id, email, name)
  - [x] `Job` (skeleton for future work)
  - [x] `Route` (skeleton)
  - [x] `Vehicle` (skeleton)
  - [x] `Tenant` (skeleton)
  - [x] `AuthTokens` (access_token, refresh_token, token_type)
- [x] Create smoke test (`src/index.test.ts`) with Vitest
- [x] Verify `pnpm -r -F @office-hero/types run build` succeeds

**Verification:**

```bash
pnpm -F @office-hero/types run build
pnpm -F @office-hero/types run test
```

---

### Task 5.3: Create `@office-hero/api-client` Package

**Status:** ✅ COMPLETED

- [x] Create `packages/api-client/` directory structure
- [x] Create `package.json` with axios dependency
- [x] Create `tsconfig.json`
- [x] Create `src/index.ts` with axios client instance:
  - [x] baseURL: `/api`
  - [x] Default headers setup
  - [x] Re-export auth module
- [x] Create `src/auth.ts` module:
  - [x] `LoginRequest` interface (email, password)
  - [x] `LoginResponse` interface (access_token, refresh_token, token_type)
  - [x] `RefreshRequest` interface (refresh_token)
  - [x] `login()` function → POST /auth/login
  - [x] `refresh()` function → POST /auth/refresh
  - [x] `logout()` function → POST /auth/logout
- [x] Create unit tests with Vitest:
  - [x] Mock axios client
  - [x] Test login() with mocked response
  - [x] Test error handling
  - [x] Test interface contracts
- [x] Create `vitest.config.ts`
- [x] Verify `pnpm -F @office-hero/api-client run test` passes

**Verification:**

```bash
pnpm -F @office-hero/api-client run build
pnpm -F @office-hero/api-client run test
```

---

## Epic: Web Applications

### Task 5.4: Create `apps/admin-web` Scaffold

**Status:** ✅ COMPLETED

- [x] Create `apps/admin-web/` directory structure
- [x] Create `package.json` with:
  - [x] React, React-DOM, React Router dependencies
  - [x] Vite, TypeScript, ESLint, Prettier devDeps
  - [x] Jest for unit testing
  - [x] Playwright for E2E testing
  - [x] @office-hero/types and @office-hero/api-client as workspace deps
- [x] Create `index.html` with root div and script entry
- [x] Create `src/main.tsx` React entry point
- [x] Create `src/App.tsx`:
  - [x] AuthProvider wrapper
  - [x] BrowserRouter with Routes
  - [x] LoginPage for unauthenticated state
  - [x] NavShell + placeholder pages for authenticated state
- [x] Create `tsconfig.json` with strict mode
- [x] Create `vite.config.ts`:
  - [x] React plugin
  - [x] API proxy to <http://localhost:8000>
  - [x] Version define from package.json
  - [x] Port 3000
- [x] Create `jest.config.js` for unit tests
- [x] Verify `pnpm -F admin-web run build` succeeds

**Verification:**

```bash
pnpm -F admin-web run build
pnpm -F admin-web run dev  # opens http://localhost:3000
```

---

### Task 5.5: Create `apps/tech-web` Scaffold

**Status:** ✅ COMPLETED

- [x] Create `apps/tech-web/` directory structure
- [x] Create minimal `package.json` (no auth required initially)
- [x] Create `index.html`
- [x] Create `src/main.tsx` with placeholder component
- [x] Create `tsconfig.json`
- [x] Create `vite.config.ts` (port 3001 to avoid conflicts)
- [x] Verify `pnpm -F tech-web run build` succeeds

**Verification:**

```bash
pnpm -F tech-web run build
```

---

### Task 5.6: Create `apps/tech-mobile` Placeholder

**Status:** ✅ COMPLETED

- [x] Create `apps/tech-mobile/` directory structure
- [x] Create `package.json` with Expo and React Native dependencies
- [x] Create `app.json` with Expo configuration:
  - [x] Android build config
  - [x] expo-location plugin setup
  - [x] Splash screen and icon placeholders
- [x] Create `src/App.tsx` with React Native placeholder UI
- [x] Create `tsconfig.json` for React Native
- [x] Create placeholder pages (to be expanded in Slice 6)
- [x] Verify workspace picks up new app

**Verification:**

```bash
pnpm install  # should include tech-mobile
```

---

## Epic: Testing Infrastructure

### Task 5.7: Set Up Unit Testing (Vitest)

**Status:** ✅ COMPLETED

- [x] Add Vitest to `@office-hero/types` devDeps
- [x] Add Vitest to `@office-hero/api-client` devDeps
- [x] Create `packages/types/vitest.config.ts`
- [x] Create `packages/api-client/vitest.config.ts`
- [x] Create `packages/types/src/index.test.ts` (smoke test)
- [x] Create `packages/api-client/src/auth.test.ts` (auth module tests)
- [x] Update test scripts in package.json files
- [x] Verify `pnpm -F @office-hero/types run test` passes
- [x] Verify `pnpm -F @office-hero/api-client run test` passes

**Verification:**

```bash
pnpm -r run test
```

---

### Task 5.8: Set Up Admin-Web Unit Testing (Jest)

**Status:** ✅ COMPLETED

- [x] Add Jest and @testing-library/react to admin-web devDeps
- [x] Create `jest.config.js` with jsdom environment
- [x] Create `src/setupTests.ts` for test environment
- [x] Create `src/__tests__/App.test.tsx` with basic smoke test
- [x] Test login form rendering
- [x] Verify `pnpm -F admin-web run test` passes

**Verification:**

```bash
pnpm -F admin-web run test
```

---

### Task 5.9: Set Up E2E Testing (Playwright)

**Status:** ✅ COMPLETED (scaffold only)

- [x] Add @playwright/test to admin-web devDeps
- [x] Create `playwright.config.ts` with:
  - [x] baseURL: <http://localhost:3000>
  - [x] Chrome, Firefox, Safari browser support
  - [x] HTML reporter
  - [x] Dev server auto-start
- [x] Create `src/e2e/login.spec.ts` with placeholder tests:
  - [x] Login form display test
  - [x] Invalid credentials error test
  - [x] Token persistence test
  - [x] Navigation visibility test
  - [x] Logout button test
- [x] Add test:e2e and test:e2e:ui npm scripts
- [x] Verify playwright config loads without errors

**Verification:**

```bash
pnpm -F admin-web run test:e2e --help  # should show Playwright help
```

---

## Epic: CI/CD Pipeline

### Task 5.10: Set Up GitHub Actions Workflow

**Status:** ✅ COMPLETED

- [x] Create `.github/workflows/frontend-ci.yml` with:
  - [x] Trigger on push/PR to all branches
  - [x] Path filters for frontend files only
  - [x] Node.js setup (v20)
  - [x] pnpm setup with caching
  - [x] Install step
  - [x] Lint step (`pnpm lint`)
  - [x] Build step (`pnpm build`)
  - [x] Test step (`pnpm test`)
- [x] Add E2E job (requires browser installation)
- [x] Add artifact upload for Playwright reports
- [x] Verify workflow file syntax

**Verification:**

```bash
pnpm lint
pnpm build
pnpm test
```

---

## Epic: Build & Configuration

### Task 5.11: Verify All Builds Succeed

**Status:** ✅ COMPLETED

- [x] Run `pnpm install` → no errors
- [x] Run `pnpm lint` → passes (ESLint + Prettier)
- [x] Run `pnpm build` → all apps and packages build
- [x] Run `pnpm test` → unit tests pass
- [x] Verify output files in `apps/admin-web/dist/`
- [x] Verify output files in `apps/tech-web/dist/`

**Final Verification:**

```bash
pnpm install
pnpm lint
pnpm build
pnpm test
```

---

## Remaining Work (Post-Slice 5)

### Future Tasks (Slice 5a)

- Create LoginPage component (interactive, connected to API)
- Create NavShell component (navigation bar)
- Implement Auth context (useState, localStorage)
- Set up axios interceptors for 401 → refresh → retry
- Create placeholder pages (Jobs, Dispatch, Vehicles, Users)
- Write E2E tests (login flow integration)
- Deploy to Fly.io

### Future Tasks (Slices 7+)

- Expand @office-hero/types with full domain models
- Add form validation (Zod, React Hook Form)
- Implement styling framework (Tailwind, CSS Modules)
- Add loading states and error boundaries
- Implement real data fetching and caching
- Add responsive design for mobile
- Implement role-based access control (RBAC) UI

---

## Success Criteria

✅ All tasks completed
✅ pnpm install succeeds
✅ pnpm build succeeds
✅ pnpm test passes
✅ ESLint/Prettier configured and passing
✅ TypeScript strict mode enabled
✅ All three apps scaffolded and buildable
✅ Shared packages importable across apps
✅ Unit and E2E test infrastructure in place
✅ CI/CD workflow configured and ready

**Ready for Phase 6 (Slice 5a Implementation)** ✅
