---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: not_started
---

# Slice Design 009: Admin web shell (login + navigation stub)

This is an early-GUI-visibility foundation slice. It delivers a working login page connected
to the real `POST /auth/login` API and a top-level navigation shell with placeholder pages.
This demonstrates the full auth flow end-to-end and provides stakeholders a visual sign of progress.

It corresponds to slice 5a in the slice plan.

## Goals

* Create a React Context-based auth hook `useAuth()` in `apps/admin-web/src/hooks/useAuth.tsx`:
  * Stores `{ user: User | null, token: string | null }`
  * Methods: `login(email, password)`, `logout()`
  * Automatically handles 401 responses with silent refresh
  * Persists refresh token in an httpOnly cookie (if using BFF) or memory (if direct API calls)
  * On login, stores access_token in memory, refresh_token in cookie or secure storage
  * On 401, calls `POST /auth/refresh`, stores new access_token, retries original request
  * On refresh failure (401 on refresh endpoint), clears auth state and redirects to login
* Create login page component `apps/admin-web/src/pages/LoginPage.tsx`:
  * Form with email + password inputs
  * Submit button; disabled during loading
  * Error display (e.g. "Invalid credentials")
  * On success, redirect to `/jobs` (or `/dashboard`)
  * No persistent state; form clears on logout
* Create protected route wrapper `ProtectedRoute.tsx`:
  * Checks `useAuth().token`; if null, redirects to `/login`
  * Otherwise renders child component
* Set up React Router in `apps/admin-web/src/App.tsx`:
  * Routes:
    * `/login` → LoginPage (unprotected)
    * `/` → redirect to `/jobs`
    * `/jobs` → `<Jobs />` placeholder (protected)
    * `/dispatch` → `<Dispatch />` placeholder (protected)
    * `/vehicles` → `<Vehicles />` placeholder (protected)
    * `/users` → `<Users />` placeholder (protected)
  * All placeholder pages display section name + "Coming soon in next slice"
* Create navigation component `apps/admin-web/src/components/Navigation.tsx`:
  * Sidebar or top nav with links to: Jobs, Dispatch, Vehicles, Users
  * User menu with logout button
  * Only visible when logged in
* API configuration: `apps/admin-web/src/api.ts`:
  * Instantiate `ApiClient` with `API_BASE_URL` from env (`import.meta.env.VITE_API_BASE_URL`)
  * Export singleton for use throughout app
  * Default to `http://localhost:8000` in dev, environment override in prod
* Environment config: `apps/admin-web/.env.example`:
  * `VITE_API_BASE_URL=http://localhost:8000`
* Playwright E2E test `apps/admin-web/e2e/auth.spec.ts`:
  * Start test server (or use `http://localhost:3000` if running `pnpm dev`)
  * Navigate to `/login`
  * Fill email + password form
  * Click login button
  * Assert redirect to `/jobs` page
  * Assert navigation menu visible
  * Click logout
  * Assert redirect to `/login`
* Vitest unit test `apps/admin-web/src/hooks/__tests__/useAuth.test.ts`:
  * Mock `ApiClient`
  * Test `login()` sets token + user
  * Test `logout()` clears token + user
  * Test 401 response triggers refresh → retry
  * Test failed refresh clears auth state
* Build and run locally:
  * `pnpm install` (from repo root installs all workspaces)
  * `pnpm --filter admin-web dev` (runs Vite dev server on `http://localhost:5173`)
  * Backend must be running on `http://localhost:8000`
  * Navigate to login, enter test credentials, verify redirect to jobs page

## Structure

```text
apps/admin-web/
├── src/
│   ├── App.tsx              # Router setup + layout
│   ├── main.tsx             # entry point
│   ├── api.ts               # ApiClient singleton
│   ├── hooks/
│   │   ├── useAuth.tsx      # Auth context + hook
│   │   └── __tests__/
│   │       └── useAuth.test.ts
│   ├── components/
│   │   ├── Navigation.tsx    # Nav sidebar/top nav
│   │   ├── ProtectedRoute.tsx # Route guard
│   │   └── __tests__/
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── JobsPage.tsx     # Placeholder
│   │   ├── DispatchPage.tsx # Placeholder
│   │   ├── VehiclesPage.tsx # Placeholder
│   │   └── UsersPage.tsx    # Placeholder
│   └── env.d.ts
├── e2e/
│   └── auth.spec.ts         # Playwright tests
├── vite.config.ts
├── tsconfig.json
├── package.json
├── .env.example
├── .prettierrc.json
├── .eslintrc.json
└── index.html
```

## Failing Test Outline

```typescript
// Playwright E2E test
import { test, expect } from '@playwright/test'

test('Login flow: fill form → submit → redirect to /jobs', async ({ page }) => {
  await page.goto('http://localhost:5173/login')

  // Fill form
  await page.fill('input[name="email"]', 'admin@tenant1.com')
  await page.fill('input[name="password"]', 'testpassword')

  // Submit
  await page.click('button:has-text("Login")')

  // Assert redirect to /jobs
  await expect(page).toHaveURL(/\/jobs/)

  // Assert navigation menu visible
  await expect(page.locator('nav')).toBeVisible()
})

test('Logout flow: click logout → redirect to /login', async ({ page }) => {
  // Precondition: already logged in (from test setup or previous test)
  await page.click('button:has-text("Logout")')

  await expect(page).toHaveURL(/\/login/)
})

// Vitest unit test
import { renderHook, act } from '@testing-library/react'
import { useAuth } from '../useAuth'
import { ApiClient } from '../../api'
import { vi } from 'vitest'

vi.mock('../../api')

describe('useAuth', () => {
  it('should login and store token', async () => {
    const { result } = renderHook(() => useAuth())

    act(() => {
      result.current.login('test@example.com', 'password')
    })

    // Mock returns tokens
    expect(result.current.token).toBeDefined()
    expect(result.current.user).toBeDefined()
  })

  it('should handle 401 with automatic refresh', async () => {
    // Mock: first API call returns 401, refresh returns new token, retry succeeds
    const { result } = renderHook(() => useAuth())

    // Trigger a request that gets 401
    // Hook should auto-refresh and retry
    expect(result.current.token).toBeDefined() // new token after refresh
  })
})
```

## Dependencies

Depends on slices 3 (Auth & RBAC — JWT endpoints) and 5 (Frontend scaffold — pnpm workspace + TypeScript).

Slice 6 (Mobile scaffold) does NOT depend on this; it has its own navigation and auth flow.

## Effort

Estimate: 2/5. Most work is React component plumbing: useContext/useReducer for auth state,
React Router setup, Playwright test infrastructure. The API integration is straightforward
(use ApiClient from slice 5). Main concern: ensuring automatic token refresh works correctly
and test coverage is comprehensive (login success/failure, logout, 401 handling, navigation).

---

Once this design is approved, the implementation starts with the failing Playwright test
(login form fill and redirect). By the end of this slice, stakeholders can see a working
login + navigation shell connected to the real backend API. This is the first time a human
can visually interact with the system.
