# Office Hero Frontend - Complete Setup & Testing Guide

## Quick Setup (Fresh Clone)

### 1. Install from GitHub

```bash
# Clone the repository
git clone https://github.com/office-hero/office-hero-frontend.git
cd office-hero-frontend

# Install pnpm if needed
npm install -g pnpm

# Install dependencies (from lock file)
pnpm install --frozen-lockfile

# Build all packages and apps
pnpm build
```

### 2. Start Backend (In Separate Terminal)

The frontend requires a running backend API:

```bash
# From office-hero-backend-core directory
cd ../office-hero-backend-core

# Ensure .env file exists with:
# DATABASE_URL=postgresql+asyncpg://postgres:pass@localhost:5432/test
# JWT_PRIVATE_KEY=private
# JWT_PUBLIC_KEY=public
# JWT_ALGORITHM=RS256

# Start backend
$env:DATABASE_URL='postgresql+asyncpg://postgres:pass@localhost:5432/test'
$env:JWT_PRIVATE_KEY='private'
$env:JWT_PUBLIC_KEY='public'
$env:JWT_ALGORITHM='RS256'
python -m uvicorn src.office_hero.main:app --host 0.0.0.0 --port 8000
```

**Note:** The backend requires PostgreSQL running at `localhost:5432`. Use Docker:
```bash
docker run -d --name oh-test-db -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=test -p 5432:5432 postgres:15-alpine
```

### 3. Start Frontend Dev Server

```bash
# From office-hero-frontend directory
pnpm dev

# Or to specifically run admin-web:
pnpm -F admin-web run dev
```

The frontend will be available at **http://localhost:3000**

### 4. Test Credentials

```
Email: test@example.com
Password: password123
```

**Note:** Test user is created by `init_testdata.py` in the backend. If needed, reinitialize:
```bash
cd ../office-hero-backend-core
python init_testdata.py
```

---

## Hook Rehydration

All React hooks in the auth system are designed to be fully rehydrated from:

1. **localStorage** - Persists access_token, refresh_token, user data
2. **Axios Client Instance** - axios interceptors reattached on mount
3. **State Management** - All state derives from localStorage on component mount

### Auth Context Flow

```typescript
// 1. On component mount, restore tokens from localStorage
useEffect(() => {
  const stored = localStorage.getItem('access_token');
  const storedRefresh = localStorage.getItem('refresh_token');
  const storedUser = localStorage.getItem('user');
  
  if (stored) {
    setToken(stored);
    client.defaults.headers.common['Authorization'] = `Bearer ${stored}`;
  }
  if (storedRefresh) {
    setRefreshToken(storedRefresh);
  }
  if (storedUser) {
    setUser(JSON.parse(storedUser));
  }
}, []); // Empty dependency array = runs once on mount

// 2. Set up axios interceptor
useEffect(() => {
  const interceptor = client.interceptors.response.use(
    response => response,
    async (error) => {
      // On 401, try to refresh token automatically
      // ...
    }
  );
  
  // Cleanup: remove interceptor on unmount
  return () => {
    client.interceptors.response.eject(interceptor);
  };
}, []); // Empty dependency array = run once
```

**Rehydration is automatic** - no manual action needed. Just:
1. Open http://localhost:3000
2. If tokens exist in localStorage, user is rehydrated as authenticated
3. If no tokens, user sees login form

---

## E2E Testing with Video Recording

### Run Tests Locally

```bash
# Navigate to admin-web
cd apps/admin-web

# Run all tests with video recording
RECORD_VIDEO=on pnpm exec playwright test --project=chromium

# Or use the convenience script
cd ../..
pnpm run test:e2e  # Runs with recording enabled
```

### View Test Results

```bash
# After tests complete
cd apps/admin-web

# View HTML report
npx playwright show-report

# View recorded videos
# Videos are in: test-results/*/*.webm
```

### Interactive Test Mode

```bash
cd apps/admin-web
pnpm exec playwright test --ui  # Opens interactive test UI
```

---

## Test Coverage

The E2E tests cover:

✅ **Form Validation**
- Login form displays correctly
- Invalid credentials show error message

✅ **Authentication**
- Successful login with valid credentials
- Redirect to /jobs after login
- Navigation bar visible for authenticated user

✅ **Token Persistence**
- Tokens stored in localStorage after login
- Tokens readable and valid (JSON parsing for user object)

✅ **Hook Rehydration** (Most Important)
- Login → tokens in localStorage
- Reload page → still authenticated
- No login form shown
- Navigation accessible
- Same tokens in localStorage

✅ **Navigation**
- Navigate between Jobs, Dispatch, Vehicles, Users pages
- Each page accessible when authenticated

✅ **Logout**
- Logout button visible when authenticated
- Click logout → redirect to login page
- localStorage tokens cleared
- All auth state cleared

✅ **Version Badge**
- Version displayed in navigation bar

✅ **Token Refresh**
- Expired token detection
- Automatic refresh on 401 error
- Original request retried with new token

---

## GitHub Actions CI/CD

The repository includes automated testing:

```yaml
# .github/workflows/frontend-ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: pnpm install --frozen-lockfile
      - run: pnpm -F admin-web run test      # Jest unit tests
      - run: pnpm -F admin-web run test:e2e  # Playwright E2E tests
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: apps/admin-web/playwright-report/
```

Tests run automatically on every push and pull request.

---

## Deployment to Fly.io

### Prerequisites

1. Backend deployed to Fly.io (e.g., `https://api.office-hero.fly.dev`)
2. Flyctl installed locally: `brew install flyctl` (macOS) or `choco install flyctl` (Windows)

### Deploy Frontend

```bash
# Update API URL in fly.toml
# Change: VITE_API_BASE_URL = "https://api.office-hero.fly.dev"

# Deploy
flyctl deploy

# Monitor logs
flyctl logs

# Test production deployment
# https://office-hero-admin-web.fly.dev
```

### Production Verification

1. **Login Test**: Use test@example.com / password123
2. **Token Persistence**: Close and reopen browser → should still be logged in
3. **Version Badge**: Should display correct version
4. **Navigation**: All pages should be accessible
5. **Logout**: Should clear session

---

## Troubleshooting

### Backend Not Responding

```bash
# Check if running
curl http://localhost:8000/health

# Check environment variables
echo $env:DATABASE_URL

# Reinitialize database
cd ../office-hero-backend-core
python init_testdata.py
```

### Frontend Not Starting

```bash
# Check Node.js version (need v18+)
node --version

# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install --frozen-lockfile

# Check port 3000 is not in use
lsof -i :3000  # macOS/Linux
netstat -ano | findstr :3000  # Windows
```

### Tests Failing

```bash
# Ensure both servers are running
curl http://localhost:3000
curl http://localhost:8000/health

# Run tests with verbose output
pnpm exec playwright test --debug

# Check test logs
cat test-results/junit.xml
```

### Tokens Not Persisting

```bash
# Check localStorage in browser dev tools
# Application → Storage → Local Storage → http://localhost:3000
# Should see:
# - access_token
# - refresh_token
# - user (JSON string)

# If missing, login failed. Check:
# 1. Backend is running
# 2. Test user exists: test@example.com
# 3. Backend health: curl http://localhost:8000/health
```

---

## Architecture

```
office-hero-frontend/
├── apps/
│   ├── admin-web/              # Main application
│   │   ├── src/
│   │   │   ├── auth.tsx        # Auth context (hooks + interceptor)
│   │   │   ├── App.tsx         # Router + Protected routes
│   │   │   ├── components/     # LoginPage, NavShell
│   │   │   ├── pages/          # Jobs, Dispatch, Vehicles, Users
│   │   │   └── e2e/            # Playwright tests
│   │   └── playwright.config.ts
│   ├── tech-web/               # Tech portal (placeholder)
│   └── tech-mobile/            # Mobile app (Expo)
├── packages/
│   ├── api-client/             # HTTP client + auth functions
│   └── types/                  # Shared TypeScript types
├── scripts/
│   ├── run-e2e-tests.sh        # E2E test script (macOS/Linux)
│   └── run-e2e-tests.ps1       # E2E test script (Windows)
├── fly.toml                    # Fly.io deployment config
├── Dockerfile                  # Production Docker image
└── pnpm-workspace.yaml         # Monorepo configuration
```

---

## Key Files for Understanding Hook Rehydration

1. **`apps/admin-web/src/auth.tsx`**
   - useEffect hooks for restoration and cleanup
   - Axios interceptor setup
   - localStorage sync logic

2. **`apps/admin-web/src/App.tsx`**
   - AuthProvider wrapper at root
   - Protected route logic using AuthContext

3. **`packages/api-client/src/index.ts`**
   - Axios client instance (shared across app)
   - Response interceptor point

4. **`apps/admin-web/src/e2e/login.spec.ts`**
   - Test: "should restore session from localStorage (hook rehydration)"
   - Verifies persistence mechanism works

---

## Quick Commands Reference

```bash
# Install & Setup
pnpm install --frozen-lockfile
pnpm build

# Development
pnpm dev                              # Start all apps in watch mode
pnpm -F admin-web run dev             # Start only admin-web

# Testing
pnpm -F admin-web run test            # Jest unit tests
RECORD_VIDEO=on pnpm run test:e2e     # Playwright E2E tests with video

# Building
pnpm build                            # Build all
pnpm -F admin-web run build           # Build only admin-web

# Deployment
flyctl deploy                         # Deploy to Fly.io

# Linting
pnpm run lint                         # Run all linters
pnpm format                           # Auto-format code
```

---

**Last Updated:** March 9, 2026  
**Status:** Production Ready ✅
