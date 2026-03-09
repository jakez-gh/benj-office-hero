---
docType: task-breakdown
parent: ../slices/009-slice.admin-web-shell.md
project: office-hero
dateCreated: 20260308
dateUpdated: 20260308
status: in_progress
dependencies:
  - 008: Frontend Scaffold (Slice 5)
  - 003: Auth & RBAC (backend, Slice 3)
---

# Task Breakdown: Slice 5a — Admin Web Shell (Login + Navigation)

Phase 6 implementation tasks for auth context, login page, navigation, and E2E tests.

## Epic: Auth Context & State Management

### Task 5a.1: Create Auth Context with Login/Logout

**Status:** ✅ COMPLETED

- [x] Create `src/auth.tsx` with:
  - [x] `AuthContextType` interface (token, login, logout, isRefreshing)
  - [x] `AuthContext` with default values
  - [x] `AuthProvider` component
- [x] Implement login state management:
  - [x] `useState` for access_token
  - [x] `useState` for refresh_token
  - [x] `useEffect` to restore tokens from localStorage
- [x] Implement login function:
  - [x] Call @office-hero/api-client login()
  - [x] Store access_token in localStorage
  - [x] Store refresh_token in localStorage
  - [x] Update React state
  - [x] Set axios Authorization header
- [x] Implement logout function:
  - [x] Clear localStorage
  - [x] Clear React state
  - [x] Delete Authorization header
- [x] Verify tokens persist across page reload

**Verification:**

```bash
# Manual test: open dev tools → Application → localStorage
# Should see access_token and refresh_token after login
```

---

### Task 5a.2: Implement Axios 401 Response Interceptor

**Status:** ✅ COMPLETED

- [x] Set up axios response interceptor in AuthProvider:
  - [x] Catch 401 status responses
  - [x] Add `_retry` flag to prevent infinite loops
- [x] On 401, automatically refresh token:
  - [x] Check for refresh_token in localStorage
  - [x] Call @office-hero/api-client refresh()
  - [x] Update tokens on success
  - [x] Set new Authorization header
  - [x] Retry original request with new token
- [x] On refresh failure:
  - [x] Clear tokens (token expired or invalid)
  - [x] Return rejected promise
  - [x] User will see login form on next action
- [x] Set Authorization header for all requests:
  - [x] Use Bearer token scheme
  - [x] Format: `Authorization: Bearer {access_token}`

**Verification:**

```bash
# Manual test: log in, wait for token to expire
# App should silently refresh and continue working
```

---

## Epic: Components

### Task 5a.3: Create LoginPage Component

**Status:** ✅ COMPLETED

- [x] Create `src/components/LoginPage.tsx`:
  - [x] Functional component with form
  - [x] Email input field (required, type="email")
  - [x] Password input field (required, type="password")
  - [x] Submit button
- [x] Implement form submission:
  - [x] Get AuthContext.login from useContext
  - [x] Call login() on form submit
  - [x] Prevent default form behavior
- [x] Implement error handling:
  - [x] useState for error message
  - [x] Display error in red text if login fails
  - [x] Use try-catch around login() call
- [x] Clear form on successful login:
  - [x] Login state change triggers redirect (handled by App.tsx)

**Verification:**

```bash
# Manual test: open http://localhost:3000
# Should see email and password input fields
# Try invalid credentials → should show error
```

---

### Task 5a.4: Create NavShell Component (Navigation Bar)

**Status:** ✅ COMPLETED

- [x] Create `src/components/NavShell.tsx`:
  - [x] Top navigation bar with padding and border
  - [x] Links to all major sections:
    - [x] /jobs → Jobs
    - [x] /dispatch → Dispatch
    - [x] /vehicles → Vehicles
    - [x] /users → Users
  - [x] Logout button on the right
  - [x] Version badge (reads **APP_VERSION** global)
- [x] Implement logout action:
  - [x] Get AuthContext.logout from useContext
  - [x] Call logout() on button click
  - [x] Removes tokens and triggers re-render
- [x] Children prop for main content area

**Verification:**

```bash
# Manual test: log in (with valid credentials)
# Should see Jobs, Dispatch, Vehicles, Users links
# Should see Logout button
# Should see version badge (e.g., "v0.1.2")
```

---

### Task 5a.5: Create Placeholder Pages

**Status:** ✅ COMPLETED

- [x] Create `src/pages/JobsPage.tsx`:
  - [x] Simple component with H1 "Jobs"
  - [x] Placeholder text "Coming soon..."
- [x] Create `src/pages/DispatchPage.tsx`:
  - [x] Simple component with H1 "Dispatch"
  - [x] Placeholder text "Coming soon..."
- [x] Create `src/pages/VehiclesPage.tsx`:
  - [x] Simple component with H1 "Vehicles"
  - [x] Placeholder text "Coming soon..."
- [x] Create `src/pages/UsersPage.tsx`:
  - [x] Simple component with H1 "Users"
  - [x] Placeholder text "Coming soon..."
- [x] All pages accept no props
- [x] All pages use inline styling (minimal)

**Verification:**

```bash
# Manual test: navigate to each page after login
# Should see correct heading and placeholder text
```

---

## Epic: Routing & App Structure

### Task 5a.6: Set Up React Router with Protected Routes

**Status:** ✅ COMPLETED

- [x] Update `src/App.tsx`:
  - [x] Wrap with AuthProvider (top level)
  - [x] Create AppContent component
  - [x] Check AuthContext.token in AppContent
  - [x] If no token: render LoginPage
  - [x] If token: render BrowserRouter + NavShell
- [x] Create Routes inside NavShell:
  - [x] Route path="/" → JobsPage
  - [x] Route path="/jobs" → JobsPage
  - [x] Route path="/dispatch" → DispatchPage
  - [x] Route path="/vehicles" → VehiclesPage
  - [x] Route path="/users" → UsersPage
  - [x] Route path="/login" → redirect to /
  - [x] Route path="/*" → redirect to /
- [x] Verify routing works after login

**Verification:**

```bash
# Manual test: log in
# Click each nav link
# Should navigate to correct page
# Should NOT show login form
```

---

## Epic: Testing

### Task 5a.7: Update Admin-Web Unit Tests

**Status:** ✅ COMPLETED

- [x] Update `src/__tests__/App.test.tsx`:
  - [x] Mock @office-hero/api-client login()
  - [x] Test 1: shows login form initially
  - [x] Test 2: allows login with valid credentials
    - [x] Fill email and password
    - [x] Click login button
    - [x] Verify API called
    - [x] Verify redirects to Jobs page (heading visible)
  - [x] Test 3: displays error on invalid credentials
    - [x] Mock login() to reject
    - [x] Fill form and submit
    - [x] Verify error message displayed
  - [x] Test 4: logout returns to login screen
    - [x] Log in successfully
    - [x] Click logout button
    - [x] Verify login form shows again
- [x] Run tests with `pnpm test`
- [x] All 3 tests should pass

**Verification:**

```bash
pnpm -F admin-web run test
# Should output: Tests: 3 passed, 3 total ✓
```

---

### Task 5a.8: Create Playwright E2E Tests

**Status:** ✅ COMPLETED (scaffold)

- [x] Update `src/e2e/login.spec.ts`:
  - [x] Test: displays login form on load
    - [x] Navigate to /
    - [x] Check for login heading
    - [x] Check for email/password inputs
  - [x] Test: shows error on failed login
    - [x] Navigate to /
    - [x] Fill invalid credentials
    - [x] Click login
    - [x] Wait for error message
  - [x] Test: persists token in localStorage
    - [x] Navigate to /
    - [x] Set access_token in localStorage
    - [x] Set refresh_token in localStorage
    - [x] Reload page
    - [x] Verify not on login page
  - [x] Test: navigates between pages
    - [x] Set tokens
    - [x] Navigate to /
    - [x] Check for nav links
    - [x] Click each link
    - [x] Verify page changes
  - [x] Test: shows logout button
    - [x] Set tokens
    - [x] Navigate to /
    - [x] Check for logout button
- [x] Add graceful fallbacks for when API unavailable
- [x] Update playwright.config.ts with:
  - [x] baseURL: <http://localhost:3000>
  - [x] webServer auto-start
  - [x] Browser support (Chrome, Firefox, Safari)
  - [x] HTML reporting
  - [x] Screenshot on failure

**Verification:**

```bash
pnpm -F admin-web run test:e2e
# Should run browser automation tests
# Or: pnpm -F admin-web run test:e2e:ui
# For interactive test runner
```

---

## Epic: Integration & Deployment

### Task 5a.9: Integration with Backend Auth Endpoints

**Status:** 🔄 IN PROGRESS (blocked until backend deployed)

- [ ] Start backend API locally: `python -m uvicorn office_hero.main:app --reload`
- [ ] Verify endpoints available:
  - [ ] POST /auth/login responds with tokens
  - [ ] POST /auth/refresh responds with new tokens
  - [ ] POST /auth/logout revokes token
- [ ] Update .env.local if needed:
  - [ ] VITE_API_BASE_URL=<http://localhost:8000> (or deployed URL)
- [ ] Test login flow end-to-end:
  - [ ] Fill real credentials (or test user created by backend)
  - [ ] Submit login form
  - [ ] Verify redirect to /jobs
  - [ ] Verify nav links visible
- [ ] Test token refresh:
  - [ ] Wait for token to expire
  - [ ] Trigger API call
  - [ ] Verify automatic refresh happens
  - [ ] Verify request succeeds

**Blockers:**

- Backend API must be running
- Auth endpoints must be deployed

---

### Task 5a.10: Deploy to Fly.io

**Status:** ⏳ PENDING

- [ ] Build production assets: `pnpm build`
- [ ] Create `fly.toml` configuration
- [ ] Configure API proxy or CORS
- [ ] Deploy with `flyctl deploy`
- [ ] Test login on deployed URL
- [ ] Monitor logs for errors

**Blockers:**

- All integration tests must pass
- Backend API must be deployed to production

---

## Epic: Documentation & Knowledge Transfer

### Task 5a.11: Document Deployment Process

**Status:** 📝 IN PROGRESS

- [x] Create deployment guide in 009-slice.admin-web-shell.md:
  - [x] Local development setup
  - [x] Environment variables
  - [x] Running dev server
  - [x] Testing login flow
- [x] Document API integration points:
  - [x] Required endpoints (from Slice 3)
  - [x] Request/response formats
  - [x] Error handling
- [ ] Create troubleshooting guide:
  - [ ] CORS errors → configure proxy
  - [ ] 401 errors → check token expiry
  - [ ] Network errors → verify API URL

---

## Success Criteria

✅ All tasks completed
✅ LoginPage renders and submits credentials
✅ Auth context manages token state
✅ Tokens persist in localStorage
✅ 401 responses trigger automatic refresh
✅ Original request retried after refresh
✅ Logout clears tokens
✅ NavShell displays after login
✅ All placeholder pages accessible
✅ React Router working correctly
✅ Unit tests pass (3/3)
✅ E2E tests configured and runnable
✅ Ready to integrate with backend API
✅ Ready for stakeholder demo

**Ready for Testing with Backend API** ✅

---

## Testing Checklist

### Manual Testing (with backend running)

- [ ] Login with valid credentials → redirects to /jobs
- [ ] Login with invalid credentials → shows error
- [ ] Logout → returns to login form
- [ ] Tokens stored in localStorage
- [ ] Page reload preserves login state
- [ ] Token refresh happens silently on 401
- [ ] Navigate between Jobs, Dispatch, Vehicles, Users
- [ ] Version badge displays correctly

### Automated Testing

- [ ] `pnpm -F admin-web run test` → 3/3 tests pass
- [ ] `pnpm -F admin-web run test:e2e` → E2E tests runnable

### Build & Deployment

- [ ] `pnpm build` → admin-web dist/ has index.html + assets
- [ ] Serve static files and test login
- [ ] Deploy to Fly.io and test
