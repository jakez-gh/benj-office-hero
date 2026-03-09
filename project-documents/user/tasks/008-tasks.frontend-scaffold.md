---
slice: frontend-scaffold
project: office-hero
lld: user/slices/008-slice.frontend-scaffold.md
dependencies: [1, 1a]
projectState: Slices 1-2 complete (Python scaffold, database foundation). Ready to initialize frontend monorepo with shared packages and multiple React applications (web admin, tech web, tech mobile placeholder).
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slice 5: Frontend Scaffold** — initializing pnpm monorepo with shared TypeScript packages and three React applications
- Current state: Python backend foundation (Slices 1-2) ready; no frontend structure yet
- Deliverable: pnpm workspace with @office-hero/{types, api-client} packages and apps/{admin-web, tech-web, tech-mobile} scaffolds
- Next: Slice 5a (Admin Web Shell) will build the login page and navigation using these scaffolds; mobile agent handles full Slice 6

---

## Task Breakdown

### Phase 1: pnpm Workspace & Shared Packages Setup

- [ ] **Initialize pnpm workspace configuration**
  - [ ] Create `pnpm-workspace.yaml` at repo root defining workspaces:
    - `packages/*` — shared packages (types, api-client)
    - `apps/*` — applications (admin-web, tech-web, tech-mobile)
  - [ ] Success: `pnpm --version` shows pnpm is installed; `cat pnpm-workspace.yaml` shows correct structure

- [ ] **Create @office-hero/types package**
  - [ ] Create `packages/types/` directory structure:
    - `package.json` with name `@office-hero/types`, version 0.1.0, `main: dist/index.js`, `types: dist/index.d.ts`
    - `tsconfig.json` (extends root, if root exists; otherwise standalone)
    - `src/index.ts` exporting TypeScript types
  - [ ] Define types in `src/types/`:
    - `User` (id, email, role, permissions)
    - `Job` (id, tenant_id, customer, address, status, scheduled_at)
    - `Route` (id, technician_id, date, jobs[], total_distance)
    - `Vehicle` (id, tenant_id, make, model, year, license_plate)
    - `Tenant` (id, name, region)
    - `AuthTokens` (access_token, refresh_token)
  - [ ] Configure `tsconfig.json` with `declaration: true` to auto-generate `.d.ts` files
  - [ ] Success: `pnpm --filter @office-hero/types run build` compiles without errors; dist/index.d.ts exists

- [ ] **Create @office-hero/api-client package**
  - [ ] Create `packages/api-client/` directory structure:
    - `package.json` with name `@office-hero/api-client`, main/types pointing to dist
    - `tsconfig.json`
    - `src/index.ts` exporting ApiClient class
  - [ ] Implement `ApiClient` class:
    - Constructor: `new ApiClient(baseUrl: string = process.env.VITE_API_BASE_URL || 'http://localhost:8000')`
    - Methods:
      - `async login(email: string, password: string): Promise\<AuthTokens\>` — POST /auth/login
      - `async refresh(refreshToken: string): Promise\<AuthTokens\>` — POST /auth/refresh
      - `async logout(): Promise\<void\>` — POST /auth/logout
      - `setTokens(tokens: AuthTokens): void` — store in localStorage
      - `getAccessToken(): string | null` — retrieve from localStorage
      - `getRefreshToken(): string | null` — retrieve from localStorage
      - `clearTokens(): void` — remove from localStorage
    - HTTP request logic: use `fetch` API (built-in, no extra dependency)
    - Error handling: throw meaningful errors (e.g., `AuthError` on 401)
  - [ ] Success: `pnpm --filter @office-hero/api-client run build` compiles without errors

- [ ] **Test shared packages**
  - [ ] Create `packages/types/src/__tests__/types.test.ts` — smoke test that types are importable
  - [ ] Create `packages/api-client/src/__tests__/api-client.test.ts`:
    - Test ApiClient instantiation with default/custom baseUrl
    - Test setTokens/getTokens/clearTokens (localStorage simulation)
  - [ ] Success: `pnpm --filter @office-hero/types run test` and `pnpm --filter @office-hero/api-client run test` pass

---

### Phase 2: React Applications Scaffolds (Vite + TypeScript)

- [ ] **Create apps/admin-web scaffold**
  - [ ] Create `apps/admin-web/` with:
    - `package.json`: name admin-web, scripts (dev, build, test, preview), dependencies (react, react-dom, react-router-dom, vite)
    - `index.html` with `<div id="root"></div>` and `<script type="module" src="/src/main.tsx"></script>`
    - `src/main.tsx` — React entry point with ReactDOM.createRoot
    - `src/App.tsx` — placeholder App component
    - `src/index.css` — placeholder styles
    - `tsconfig.json` (React template)
    - `vite.config.ts` with React plugin
    - `.eslintrc.cjs` with React configuration
    - `.prettierrc` with consistent formatting rules
  - [ ] Success: `pnpm --filter admin-web run dev` starts dev server on <http://localhost:5173>; app loads without errors

- [ ] **Create apps/tech-web scaffold**
  - [ ] Create `apps/tech-web/` with same structure as admin-web
  - [ ] Tech-web is lightweight version for field technicians (will have fewer routes than admin-web)
  - [ ] Success: `pnpm --filter tech-web run dev` starts dev server without errors

- [ ] **Create apps/tech-mobile placeholder**
  - [ ] Create `apps/tech-mobile/` directory
  - [ ] Create `package.json` with name tech-mobile, React Native Expo dependencies placeholder
  - [ ] Create `app.json` with Expo configuration (will be fully implemented in Slice 6)
  - [ ] Note: Do NOT run `npx create-expo-app` yet (will be part of Slice 6 implementation)
  - [ ] Success: Directory exists, package.json valid

- [ ] **Test app scaffolds**
  - [ ] Create `apps/admin-web/src/__tests__/App.test.tsx` — smoke test App component renders
  - [ ] Create `apps/tech-web/src/__tests__/App.test.tsx` — same
  - [ ] Configure Vitest for both apps
  - [ ] Success: `pnpm --filter admin-web run test` and `pnpm --filter tech-web run test` pass

---

### Phase 3: Monorepo Build & CI Integration

- [ ] **Configure root package.json scripts for monorepo**
  - [ ] Add scripts to root `package.json`:
    - `pnpm install` — install all dependencies
    - `pnpm -r run build` — build all packages + apps
    - `pnpm -r run dev` — run dev servers (note: will run all simultaneously; user can Ctrl+C)
    - `pnpm -r run test` — test all packages + apps
  - [ ] Success: `pnpm install` completes; `pnpm -r run build` succeeds for all packages

- [ ] **Add CI/CD jobs to .github/workflows/ci.yml**
  - [ ] Add job `pnpm-install`: install dependencies
  - [ ] Add job `pnpm-build`: `pnpm -r run build` with coverage of all apps
  - [ ] Add job `pnpm-test`: `pnpm -r run test`
  - [ ] Success: GitHub Actions can run frontend build & test jobs

- [ ] **Verify workspace cross-package imports work**
  - [ ] In `apps/admin-web`, add import: `import { User } from '@office-hero/types'`
  - [ ] In `apps/admin-web`, add import: `import { ApiClient } from '@office-hero/api-client'`
  - [ ] Verify TypeScript resolves types correctly (no import errors)
  - [ ] Success: Build succeeds with all imports resolved

- [ ] **Test workspace integration**
  - [ ] Create `apps/admin-web/src/__tests__/integration.test.tsx`:
    - Test that @office-hero/types are importable
    - Test that @office-hero/api-client is importable
    - Test ApiClient instantiation with types
  - [ ] Success: `pnpm --filter admin-web run test` passes integration tests

---

### Phase 4: Documentation & Deployment Prep

- [ ] **Create FRONTEND.md documentation**
  - [ ] Document workspace structure (packages/ vs apps/)
  - [ ] Provide setup instructions (`pnpm install`, `pnpm -r run dev`)
  - [ ] Document per-app dev server URLs
  - [ ] Explain environment variables (VITE_API_BASE_URL for backend URL)
  - [ ] Success: FRONTEND.md is clear and useful for developers

- [ ] **Configure Playwright for E2E testing (root level)**
  - [ ] Create `playwright.config.ts` at repo root
  - [ ] Configure Playwright to test apps at localhost:5173 (admin-web) and localhost:5174 (tech-web)
  - [ ] Success: `npx playwright install` && `npx playwright test` can be run (may have no tests yet; that's okay)

- [ ] **Add deploy configuration (Fly.io)**
  - [ ] Create `fly.toml` (if not already present) for frontend app
  - [ ] Or create `apps/admin-web/fly.toml` for deploying to Fly.io
  - [ ] Configuration: build with `pnpm -r run build`, serve with simple HTTP server or FastAPI StaticFiles mount
  - [ ] Success: File exists and is valid TOML

- [ ] **Test full monorepo build**
  - [ ] Command: `pnpm install && pnpm -r run build`
  - [ ] Success: All packages and apps build successfully; dist/ directories exist with compiled output

---

### Phase 5: Final Integration & Verification

- [ ] **Verify all imports and exports**
  - [ ] Run TypeScript compiler: `pnpm -r run build`
  - [ ] Verify no TS errors in any package or app
  - [ ] Success: Build succeeds with zero errors

- [ ] **Run full test suite**
  - [ ] Command: `pnpm -r run test`
  - [ ] Success: All tests pass (types smoke test, api-client tests, app smoke tests)

- [ ] **Start dev servers and manual verification**
  - [ ] Start admin-web: `pnpm --filter admin-web run dev` (port 5173)
  - [ ] Open <http://localhost:5173> in browser
  - [ ] Verify page loads without errors
  - [ ] Check browser console for no TypeScript/React errors
  - [ ] Success: App renders cleanly

- [ ] **Verify environment variable support**
  - [ ] Test that `process.env.VITE_API_BASE_URL` is read by api-client
  - [ ] Create `.env.local` in each app with `VITE_API_BASE_URL=http://localhost:8000`
  - [ ] Restart dev server and verify ApiClient uses correct baseUrl
  - [ ] Success: Environment variables work

---

### Phase 6: Commit & Push

- [ ] **Final commit & push**
  - [ ] Commit: "Implement Slice 5 (Frontend Scaffold): pnpm monorepo, shared packages, Vite React apps"
  - [ ] Push to feature branch (e.g., `phase-6/slice-5-implementation`)
  - [ ] Create PR with summary
  - [ ] Success: GitHub CI passes (install, build, test)

---

## Success Criteria (Phase 5 Complete)

- ✅ pnpm-workspace.yaml configured correctly
- ✅ @office-hero/types package created with exported types
- ✅ @office-hero/api-client package created with ApiClient class
- ✅ apps/admin-web, apps/tech-web scaffolds created with Vite + React + TypeScript
- ✅ apps/tech-mobile placeholder created (full implementation in Slice 6)
- ✅ All packages build without errors
- ✅ Cross-package imports work (apps can import from packages)
- ✅ All tests passing (types smoke test, api-client tests, app tests)
- ✅ Dev servers start and render apps correctly
- ✅ CI/CD jobs configured for pnpm install/build/test
- ✅ Documentation (FRONTEND.md) created
- ✅ Environment variables (VITE_API_BASE_URL) supported
- ✅ All changes committed and pushed
- ✅ Ready for Phase 6 (Implementation) of Slice 5a (Admin Web Shell)
