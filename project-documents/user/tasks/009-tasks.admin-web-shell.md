---
slice: admin-web-shell
project: office-hero
lld: user/slices/009-slice.admin-web-shell.md
dependencies: [1, 1a, 2, 3, 5]
projectState: Slices 1-5 complete (Python scaffold, database foundation, auth/RBAC, observability, frontend scaffold with pnpm workspace). Ready to implement login page and navigation shell with full auth flow end-to-end.
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slice 5a: Admin Web Shell** — delivering working login page + navigation shell demonstrating full auth flow end-to-end for early stakeholder visibility
- Current state: Frontend scaffold (Slice 5) ready; backend auth endpoints (Slice 3) available; can now build connected UI
- Deliverable: Functional admin web app with login page, protected routes, navigation shell, and full auth flow (including silent token refresh on 401)
- Next: Slice 8-10 (remaining frontend features) and Slice 6 (mobile) can reference this shell as pattern

---

## Task Breakdown

### Phase 1: Authentication Context & Hooks

- [ ] **Create src/contexts/AuthContext.tsx — useAuth hook**
  - [ ] Define `AuthContextType`:
    - `user: User | null`
    - `token: string | null`
    - `login(email: string, password: string): Promise\<void\>`
    - `refresh(): Promise\<void\>`
    - `logout(): Promise\<void\>`
    - `isLoading: boolean`
    - `error: string | null`
  - [ ] Create `AuthProvider` component:
    - Wraps app in `AuthContext.Provider`
    - Initializes state from localStorage (token, user)
    - Implements login: calls ApiClient.login, stores tokens + user, sets state
    - Implements refresh: calls ApiClient.refresh, updates access token
    - Implements logout: calls ApiClient.logout, clears state
  - [ ] Export `useAuth()` hook: returns context value
  - [ ] Success: Hook exports without errors; context has all required fields

- [ ] **Create automatic 401 → refresh → retry flow**
  - [ ] In ApiClient class (update from Slice 5):
    - Intercept fetch responses
    - If status === 401:
      - Call refresh() to get new access token
      - Retry original request with new token
      - If retry succeeds, return response
      - If retry fails (refresh token expired), redirect to login
    - Success: 401 response triggers silent refresh and request retry

- [ ] **Test auth context (unit tests)**
  - [ ] Create `src/contexts/__tests__/AuthContext.test.tsx`:
    - Test useAuth returns correct initial state (no token)
    - Test login sets user + tokens in state and localStorage
    - Test logout clears state and localStorage
    - Test refresh updates access token
  - [ ] Mock ApiClient calls
  - [ ] Success: `pnpm --filter admin-web run test` passes auth context tests

---

### Phase 2: Login Page Component

- [ ] **Create src/pages/LoginPage.tsx**
  - [ ] Form with fields:
    - Email (text input)
    - Password (password input)
    - Submit button
  - [ ] Behavior:
    - On submit: call `useAuth().login(email, password)`
    - Show loading state while request in progress
    - Show error message if login fails
    - On success: redirect to `/jobs` (main dashboard)
  - [ ] Styling: basic CSS (center form, simple layout)
  - [ ] Success: Component renders; form submits and calls login

- [ ] **Create src/pages/NotFoundPage.tsx (placeholder)**
  - [ ] Simple 404 page: "Page not found"
  - [ ] Link back to home (/)
  - [ ] Success: Renders without errors

- [ ] **Test login page (unit & integration tests)**
  - [ ] Create `src/pages/__tests__/LoginPage.test.tsx`:
    - Test form renders with email and password fields
    - Test submit calls useAuth().login with email/password
    - Test success redirects to /jobs
    - Test error displays error message
  - [ ] Success: `pnpm --filter admin-web run test` passes login page tests

---

### Phase 3: Route Protection & Navigation

- [ ] **Create src/components/ProtectedRoute.tsx**
  - [ ] Wrapper component that:
    - Checks `useAuth().token`
    - If no token, renders redirect to `/login`
    - If token exists, renders `<Outlet />` (react-router)
  - [ ] Success: Component renders correctly; redirects unauthenticated users

- [ ] **Set up React Router in src/App.tsx**
  - [ ] Create router with routes:
    - `/login` — LoginPage (unprotected)
    - `/` — ProtectedRoute wrapper with Outlet
      - All protected routes as children:
        - `/jobs` — JobsPage (placeholder, "Coming soon")
        - `/dispatch` — DispatchPage (placeholder)
        - `/vehicles` — VehiclesPage (placeholder)
        - `/users` — UsersPage (placeholder)
  - [ ] Use `BrowserRouter` + `Routes` + `Route` from react-router-dom
  - [ ] Success: Router setup complete; all routes accessible in browser

- [ ] **Create src/components/Navigation.tsx**
  - [ ] Conditional rendering:
    - If no user: show nothing (only on /login page)
    - If user logged in: show navigation with:
      - Sidebar or top nav with links: Home, Jobs, Dispatch, Vehicles, Users
      - User profile section (show logged-in email)
      - Logout button (calls useAuth().logout)
  - [ ] Styling: horizontal top nav or vertical sidebar (choose one style)
  - [ ] Success: Navigation renders when logged in; logout works

- [ ] **Create placeholder pages**
  - [ ] Create `src/pages/JobsPage.tsx`: "Coming soon — Jobs"
  - [ ] Create `src/pages/DispatchPage.tsx`: "Coming soon — Dispatch"
  - [ ] Create `src/pages/VehiclesPage.tsx`: "Coming soon — Vehicles"
  - [ ] Create `src/pages/UsersPage.tsx`: "Coming soon — Users"
  - [ ] Success: All pages render without errors

- [ ] **Test routing & navigation (unit & integration tests)**
  - [ ] Create `src/components/__tests__/ProtectedRoute.test.tsx`:
    - Test redirects to /login if no token
    - Test renders children if token exists
  - [ ] Create `src/components/__tests__/Navigation.test.tsx`:
    - Test Navigation not shown when logged out
    - Test Navigation shown when logged in
    - Test logout button calls useAuth().logout
  - [ ] Success: `pnpm --filter admin-web run test` passes routing tests

---

### Phase 4: API Client Configuration & Integration

- [ ] **Create src/api.ts — singleton API client**
  - [ ] Export singleton: `export const api = new ApiClient(process.env.VITE_API_BASE_URL || 'http://localhost:8000')`
  - [ ] Use this singleton in all components (instead of creating new instance each time)
  - [ ] Success: Module imports without errors; singleton is reusable

- [ ] **Update AuthContext to use singleton API client**
  - [ ] Import api from `src/api.ts`
  - [ ] In login/refresh/logout methods, use api instead of creating new instance
  - [ ] Success: AuthContext uses shared API client

- [ ] **Create .env.local for local development**
  - [ ] File content: `VITE_API_BASE_URL=http://localhost:8000`
  - [ ] This enables local testing against backend API
  - [ ] Success: Dev server reads env var; API calls hit localhost:8000

- [ ] **Test API integration (integration tests)**
  - [ ] Create `src/__tests__/api-integration.test.ts`:
    - Test ApiClient singleton is created with correct baseUrl
    - Test setTokens/getTokens work with api singleton
  - [ ] Success: Tests pass

---

### Phase 5: End-to-End Playwright Tests

- [ ] **Create tests/e2e/login.spec.ts — full login flow**
  - [ ] Test scenario:
    1. Navigate to <http://localhost:5173/login>
    2. Fill email field with test email (e.g., "<admin@example.com>")
    3. Fill password field with test password (e.g., "password123")
    4. Click submit button
    5. Wait for redirect to /jobs
    6. Assert URL is <http://localhost:5173/jobs>
    7. Assert navigation is visible (logged in)
  - [ ] Test error scenario:
    1. Fill with wrong password
    2. Assert error message displays
    3. Assert not redirected
  - [ ] Success: Tests pass against real app

- [ ] **Create tests/e2e/navigation.spec.ts**
  - [ ] Test scenario:
    1. Login (use login flow from above)
    2. Click "Jobs" in navigation
    3. Assert URL is /jobs
    4. Click "Dispatch"
    5. Assert URL is /dispatch
    6. Click logout
    7. Assert redirected to /login
  - [ ] Success: Navigation works; logout redirects correctly

- [ ] **Test protected routes (unit + integration)**
  - [ ] Create test for accessing /jobs without login:
    1. Navigate to /jobs without token
    2. Assert redirected to /login
  - [ ] Success: Protected routes block unauthenticated access

---

### Phase 6: Build, Test & Deployment Prep

- [ ] **Run full test suite**
  - [ ] Command: `pnpm --filter admin-web run test`
  - [ ] Success: All unit + integration tests pass
  - [ ] Command: `npx playwright test` (from root, or from apps/admin-web)
  - [ ] Success: All E2E tests pass

- [ ] **Verify app builds**
  - [ ] Command: `pnpm --filter admin-web run build`
  - [ ] Success: dist/ directory created with production bundle
  - [ ] Output should be < 500KB (gzipped)

- [ ] **Manual browser testing**
  - [ ] Start dev server: `pnpm --filter admin-web run dev`
  - [ ] Open <http://localhost:5173/login>
  - [ ] Test login with valid credentials (if backend is running)
    - If backend running: login should work end-to-end
    - If backend not running: mock responses in API client for testing
  - [ ] Verify navigation renders after login
  - [ ] Test logout
  - [ ] Success: App works end-to-end in browser

- [ ] **Test 401 → refresh → retry flow**
  - [ ] Mock an API endpoint that returns 401 on first call, 200 on second
  - [ ] Verify automatic refresh is triggered
  - [ ] Verify request is retried and succeeds
  - [ ] Success: Silent refresh flow works correctly

- [ ] **Prepare for deployment**
  - [ ] Ensure .env.local is NOT committed (add to .gitignore)
  - [ ] Create .env.example with template: `VITE_API_BASE_URL=http://localhost:8000`
  - [ ] Verify production env vars can be set via environment or build-time args
  - [ ] Success: App is deployable to Fly.io or similar PaaS

---

### Phase 7: Final Commit & Push

- [ ] **Final commit & push**
  - [ ] Commit: "Implement Slice 5a (Admin Web Shell): login page, navigation, auth context, protected routes, E2E tests"
  - [ ] Push to feature branch (e.g., `phase-6/slice-5a-implementation`)
  - [ ] Create PR with summary of end-to-end auth flow
  - [ ] Success: GitHub CI passes (install, build, test)

---

## Success Criteria (Phase 5 Complete)

- ✅ useAuth() context hook created with login/refresh/logout
- ✅ Automatic 401 → refresh → retry flow implemented
- ✅ LoginPage component renders form and submits credentials
- ✅ ProtectedRoute wrapper guards routes; redirects to /login if unauthenticated
- ✅ React Router setup with all protected routes
- ✅ Navigation component shows when logged in, hides when logged out
- ✅ Placeholder pages created (Jobs, Dispatch, Vehicles, Users)
- ✅ Singleton API client configured
- ✅ All unit + integration tests passing
- ✅ All Playwright E2E tests passing (login, navigation, logout, 401 flow)
- ✅ App builds successfully (dist/ created)
- ✅ Manual browser testing shows full auth flow working
- ✅ All changes committed and pushed
- ✅ Ready for Slice 8-10 (remaining admin features) and deployment to Fly.io
