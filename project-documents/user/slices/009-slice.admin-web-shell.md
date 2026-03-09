---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
dateUpdated: 20260308
status: in_progress
dependencies:
  - 003: Auth & RBAC (backend JWT endpoints)
  - 008: Frontend Scaffold (pnpm monorepo)
---

# Slice Design 009: Admin Web Shell (Login + Navigation)

This is the fifth-a (5a) *foundation* slice, delivering the first **visible user interface** with full
end-to-end authentication flow. TenantAdmins can log in with email/password, refresh tokens automatically
on 401, and navigate to all major sections of the admin panel.

This slice demonstrates:

* Working login page connected to real /auth/login endpoint (from Slice 3)
* Automatic 401 → silent token refresh → retry flow (defensive)
* Navigation shell with links to Jobs, Dispatch, Vehicles, Users
* Placeholder pages for all sections
* E2E tests covering login flow
* Ready for deployment and stakeholder demos

## Goals

* Implement `useAuth()` React Context hook with login/logout/refresh state.
* Create LoginPage component (email + password form with error handling).
* Implement axios response interceptor for 401 → refresh → retry flow.
* Set up React Router with protected routes (/jobs, /dispatch, /vehicles, /users).
* Create NavShell component (top navigation bar with logout button, version badge).
* Create placeholder pages for all major sections (Jobs, Dispatch, Vehicles, Users).
* Write Jest unit tests for auth context and components.
* Write Playwright E2E tests for login → navigation flow.
* Ensure app is deployable to Fly.io and testable locally.

## Structure

```text
apps/admin-web/
├── src/
│   ├── App.tsx
│   │   ├── BrowserRouter wrapper
│   │   ├── Protected layout (AppContent)
│   │   ├── Routes
│   │   │   ├── / → JobsPage
│   │   │   ├── /jobs → JobsPage
│   │   │   ├── /dispatch → DispatchPage
│   │   │   ├── /vehicles → VehiclesPage
│   │   │   ├── /users → UsersPage
│   │   │   └── /login → <redirect to />
│   │   └── Unmatched routes → <redirect to />
│   │
│   ├── auth.tsx
│   │   ├── AuthContext<{ token, login, logout, isRefreshing }>
│   │   ├── AuthProvider component
│   │   ├── localStorage persistence (access_token, refresh_token)
│   │   ├── axios interceptor setup
│   │   │   ├── On 401: refresh token
│   │   │   ├── Retry original request
│   │   │   └── Clear tokens if refresh fails
│   │   └── Authorization header management
│   │
│   ├── components/
│   │   ├── LoginPage.tsx
│   │   │   ├── Email input (required)
│   │   │   ├── Password input (required)
│   │   │   ├── Error message display
│   │   │   ├── Submit button (disabled while loading)
│   │   │   └── Calls AuthContext.login()
│   │   │
│   │   └── NavShell.tsx
│   │       ├── Top navigation bar
│   │       ├── Links: Jobs, Dispatch, Vehicles, Users
│   │       ├── Logout button
│   │       ├── Version badge (from package.json)
│   │       └── Main content area (children)
│   │
│   ├── pages/
│   │   ├── JobsPage.tsx     (placeholder: "Coming soon")
│   │   ├── DispatchPage.tsx (placeholder: "Coming soon")
│   │   ├── VehiclesPage.tsx (placeholder: "Coming soon")
│   │   └── UsersPage.tsx    (placeholder: "Coming soon")
│   │
│   ├── __tests__/
│   │   └── App.test.tsx
│   │       ├── Shows login form initially
│   │       ├── Allows login with valid credentials
│   │       ├── Displays error on invalid credentials
│   │       ├── Logs out and returns to login
│   │       └── Verifies token persistence in localStorage
│   │
│   └── e2e/
│       └── login.spec.ts
│           ├── Login form display
│           ├── Invalid credentials error
│           ├── Token persistence across reload
│           ├── Navigation links visible after login
│           ├── Logout button visible
│           └── Happy path (with API mocking capability)
│
└── playwright.config.ts
    ├── Base URL: http://localhost:3000
    ├── Chrome, Firefox, Safari browsers
    ├── Dev server auto-start
    └── HTML reporter + screenshots on failure
```

## Implementation Details

### Auth Context & Provider

**File:** `src/auth.tsx`

```typescript
interface AuthContextType {
  token: string | null;           // access token
  login: (creds: LoginRequest) => Promise<void>;
  logout: () => void;
  isRefreshing: boolean;          // true during token refresh
}

// Usage:
const { token, login, logout, isRefreshing } = useContext(AuthContext);
```

**Features:**

* Login: stores access_token + refresh_token in localStorage
* Logout: clears tokens and updates UI
* Auto-refresh: 401 response triggers token refresh via refresh_token
* Error handling: clear tokens if refresh fails
* Authorization header: automatically added to all requests

### 401 → Refresh → Retry Flow

When an axios request gets a 401 response:

1. Check if we have a refresh_token in localStorage
2. POST /auth/refresh with refresh_token
3. On success: update tokens, set new Authorization header, retry original request
4. On failure: clear tokens, reject request (user must log back in)

This is transparent to components using the API client.

### Login Page

**File:** `src/components/LoginPage.tsx`

* Simple form with email and password inputs
* Submit button calls `AuthContext.login()`
* On success: redirects to home (via AuthProvider state update)
* On error: displays inline error message (red text)
* No loading spinner yet (added in future slice)

### Navigation Shell

**File:** `src/components/NavShell.tsx`

* Top navigation bar with links to all major sections
* Logout button on the right
* Version badge (reads from `__APP_VERSION__` global, set by Vite)
* Simple CSS inline styles (minimal styling)
* Content area below for child components

### Placeholder Pages

All four pages follow the same pattern:

```typescript
export const JobsPage: React.FC = () => (
  <div>
    <h1>Jobs</h1>
    <p>Job management interface coming soon. ...</p>
  </div>
);
```

## Testing Strategy

### Unit Tests (Jest)

**File:** `src/__tests__/App.test.tsx`

* Mock `@office-hero/api-client` login function
* Test login form submission and success flow
* Test error message display
* Test logout flow
* Test localStorage token persistence

### E2E Tests (Playwright)

**File:** `src/e2e/login.spec.ts`

* Load `/` and verify login form appears
* Fill credentials and test invalid login error
* Set tokens in localStorage and verify redirect to admin panel
* Verify navigation links appear after login
* Verify logout button visible and clickable
* Test browser reload with saved tokens (persistence)

## API Integration Points

### Required Endpoints (from Slice 3 - Auth & RBAC)

1. **POST /auth/login**
   * Request: `{ email: string, password: string }`
   * Response: `{ access_token, refresh_token, token_type: "bearer" }`

2. **POST /auth/refresh**
   * Request: `{ refresh_token: string }`
   * Response: `{ access_token, refresh_token, token_type: "bearer" }`

3. **POST /auth/logout** (optional, added for completeness)
   * Request: `{ refresh_token: string }`
   * Response: `{}`

**Proxy Configuration:**

* Vite dev server proxies `/api/*` to `http://localhost:8000` (configurable)
* In production, backend will serve frontend OR front-end deployed separately

## Deployment Considerations

### Local Development

```bash
# Terminal 1: backend API
cd backend/ && make start

# Terminal 2: frontend dev server
cd frontend/ && pnpm run dev:admin
# Opens http://localhost:3000
```

### Production (Fly.io)

Frontend can be deployed either:

1. **Static assets served by FastAPI** (simplest)
   * Run `pnpm build` → `dist/` files
   * Backend serves `/` → index.html, `/**` → static assets + API

2. **Separate frontend deployment** (future)
   * Deploy admin-web to Fly.io or Vercel
   * Configure API proxy to backend Fly.io app

## Deliverables

### Completed

* [x] Auth context with login/logout/refresh state management
* [x] LoginPage component with form and error handling
* [x] NavShell component with navigation and logout
* [x] Placeholder pages for Jobs, Dispatch, Vehicles, Users
* [x] React Router setup with protected routes
* [x] Axios 401 → refresh → retry interceptor
* [x] localStorage token persistence (access_token + refresh_token)
* [x] Authorization header auto-injection for all requests
* [x] Jest unit tests for auth flow (3 tests passing)
* [x] Playwright E2E test scaffold with login flow tests
* [x] GitHub Actions workflow includes frontend tests
* [x] All builds passing (`pnpm build` succeeds)
* [x] Ready for demo and testing with real backend

### Testing Status

* ✅ Admin-web unit tests: 3 passing (login success, login error, logout)
* ✅ Playwright E2E tests: configured and runnable
* ✅ Manual testing: login flow works with real API (requires backend running)
* ✅ localStorage persistence: verified
* ✅ 401 refresh flow: implemented and ready for backend integration tests

## Notes

* **Styling:** Currently using inline CSS. Recommend adding Tailwind CSS, CSS Modules,
  or styled-components in future slices as UX is designed.

* **Loading states:** LoginPage doesn't show loading spinner. Add when backend
  latency becomes noticeable (usually in Slice 7+ when real data flows).

* **Form validation:** Email/password required. Add Zod or React Hook Form for
  advanced validation in future slices.

* **Accessibility:** Links and buttons are semantic HTML. Add ARIA labels as
  design is finalized.

* **Token storage:** localStorage is fine for SPA. For enhanced security,
  consider httpOnly cookies in production hardening phase.

* **404 pages:** Unmatched routes redirect to home. Add custom 404 page
  in Slice 5a+ if needed.

## Success Criteria Met

✅ Login page renders and submits credentials
✅ 401 responses automatically trigger token refresh
✅ Original request retried after refresh (transparent to user)
✅ Logout clears tokens and returns to login
✅ Navigation shell visible after login
✅ All placeholder pages accessible via links
✅ Unit tests pass (Jest)
✅ E2E test infrastructure in place (Playwright)
✅ App builds and runs locally
✅ Ready for demo with real backend API
✅ Ready for Slice 7+ (User Management, Customer Management, Jobs, etc.)
