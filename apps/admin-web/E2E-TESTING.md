# E2E Testing & Demo Recording Guide

## Quick Start

### Prerequisites

Ensure both servers are running:

```bash
# Terminal 1: Start backend
cd ../office-hero-backend-core
$env:DATABASE_URL='postgresql+asyncpg://postgres:pass@localhost:5432/test'
$env:JWT_PRIVATE_KEY='private'
$env:JWT_PUBLIC_KEY='public'
$env:JWT_ALGORITHM='RS256'
python -m uvicorn src.office_hero.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd office-hero-frontend
pnpm dev
```

## Running E2E Tests

### Option 1: Headless Test Run

```bash
# From office-hero-frontend root
pnpm test:e2e

# Or just admin-web
cd apps/admin-web
pnpm exec playwright test
```

**Output:**
- Test report: `apps/admin-web/playwright-report/index.html`
- Videos (on failure): `apps/admin-web/test-results/`
- JSON results: `apps/admin-web/test-results/results.json`

### Option 2: Interactive Mode

```bash
# Open Playwright Test UI
pnpm test:e2e:ui

# Or
cd apps/admin-web
pnpm exec playwright test --ui
```

This opens an interactive browser where you can:
- Run individual tests
- Step through code execution
- Inspect page elements
- View network requests

### Option 3: With Video Recording

```bash
# Records all tests (even passing ones)
pnpm test:e2e:record

# Or manually
cd apps/admin-web
RECORD_VIDEO=on pnpm exec playwright test --project=chromium
```

## Demo Recording Script

The demo recording script automatically:
1. Logs in with test user
2. Navigates through all pages
3. Tests hook rehydration (page reload)
4. Tests logout
5. Captures screenshots and videos

### Running the Demo

```bash
# From admin-web directory
pnpm demo

# Or from root
pnpm demo
```

**Output:**
- Video: `apps/admin-web/demo-recordings/demo-YYYY-MM-DD...webm`
- Screenshots: `apps/admin-web/demo-recordings/screenshots-YYYY-MM-DD.../`

### Viewing the Demo

```bash
# View recorded video
ffplay apps/admin-web/demo-recordings/demo-*.webm

# Convert WebM to MP4 for sharing
ffmpeg -i apps/admin-web/demo-recordings/demo-*.webm demo.mp4

# View screenshots
# Open in file explorer: apps/admin-web/demo-recordings/screenshots-*/
```

## Test Coverage

### Hook Rehydration Tests

The most important tests that verify proper hook design:

1. **localStorage Persistence Test**
   - Login → tokens saved to localStorage
   - Navigate page → tokens still accessible

2. **Page Reload Rehydration Test**
   - Login → navigate to /jobs
   - Reload page → still logged in (hooks restore from localStorage)
   - Same tokens exist in localStorage

3. **Logout Test**
   - Logout → localStorage cleared
   - Tokens removed from auth state
   - Redirect to login page

### Authentication Flow Tests

1. **Valid Credentials**
   - Email: test@example.com
   - Password: password123
   - Expected: Redirect to /jobs

2. **Invalid Credentials**
   - Any other email/password
   - Expected: Error message displayed

3. **Automatic Token Refresh**
   - Simulate expired token
   - Navigate to protected page
   - Expected: Automatic refresh, request succeeds

### Navigation Tests

All pages accessible when authenticated:
- /jobs
- /dispatch
- /vehicles
- /users

## CI/CD Integration

Tests run automatically via GitHub Actions:

```bash
# Simulate CI environment
CI=true pnpm test:e2e

# With specific project
pnpm exec playwright test --project=chromium --project=firefox
```

**GitHub workflow:** `.github/workflows/frontend-ci.yml`

Tests run on:
- Every push to main/develop branches
- Every pull request
- Manual trigger via GitHub Actions tab

## Troubleshooting

### Tests Not Running

```bash
# Check if backend is accessible
curl http://localhost:8000/health

# Check if frontend is running
curl http://localhost:3000

# Check pnpm is installed
pnpm --version

# Install dependencies if missing
pnpm install --frozen-lockfile
```

### Test Failures

```bash
# Run with debug mode
pnpm exec playwright test --debug

# Run specific test file
pnpm exec playwright test src/e2e/login.spec.ts

# Run specific test
pnpm exec playwright test -g "should successfully login"

# View trace
pnpm exec playwright show-trace trace.zip
```

### Video Not Generating

Video recording requires:
- Playwright browsers to be installed: `pnpm exec playwright install`
- Sufficient disk space
- Proper permissions in demo-recordings directory

```bash
# Reinstall browsers
pnpm exec playwright install chromium

# Check recordings directory
ls -la apps/admin-web/demo-recordings/
```

## Performance Benchmarks

Expected test execution times:

| Test | Duration | Notes |
|------|----------|-------|
| Login form display | ~500ms | Quick DOM check |
| Failed login | ~1500ms | Waits for API error |
| Successful login | ~2000ms | Includes redirect |
| Page reload | ~2000ms | Includes network wait |
| Navigation | ~1000ms | Per page change |
| **Total Suite** | **~12s** | All tests sequentially |

## Recording Specifications

### Video Quality

- **Resolution:** 1280x720 (720p)
- **Format:** WebM (VP9 codec)
- **Frame Rate:** 30fps
- **Bitrate:** Variable (optimized for clarity)

### Screenshot Quality

- **Format:** PNG
- **Compression:** Lossless
- **DPI:** 96
- **Timing:** After critical interactions

## Sample Test Output

```
$ pnpm test:e2e

> admin-web@0.1.0 test:e2e
> playwright test

Running 9 tests using 1 worker

  ✓ Admin Web - Login & Auth Flow › should display login form on initial load (487ms)
  ✓ Admin Web - Login & Auth Flow › should show error message on failed login (1523ms)
  ✓ Admin Web - Login & Auth Flow › should successfully login with valid credentials (1892ms)
  ✓ Admin Web - Login & Auth Flow › should persist tokens in localStorage after login (2105ms)
  ✓ Admin Web - Login & Auth Flow › should restore session from localStorage (hook rehydration) (2456ms)
  ✓ Admin Web - Login & Auth Flow › should navigate between authenticated pages (4821ms)
  ✓ Admin Web - Login & Auth Flow › should logout and clear session (1987ms)
  ✓ Admin Web - Login & Auth Flow › should display version badge in nav (1456ms)
  ✓ Admin Web - Login & Auth Flow › should handle 401 errors with automatic refresh (2145ms)

9 passed (21.8s)

To open last HTML report run:
  npx playwright show-report
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Frontend CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: pnpm install --frozen-lockfile
      - run: pnpm test              # Jest unit tests
      - run: pnpm test:e2e          # Playwright E2E tests
      - uses: actions/upload-artifact@v3  # Save artifacts on failure
```

### Local Simulation

```bash
# Run tests as they would in CI
CI=true pnpm test
CI=true pnpm test:e2e
```

## Best Practices

### Writing New Tests

1. **Use semantic locators**
   ```typescript
   // ✓ Good
   page.getByRole('button', { name: /login/i })
   page.getByLabel(/email/i)

   // ✗ Avoid
   page.querySelector('#submit-btn')
   page.locator('[data-testid="email-input"]')
   ```

2. **Wait for state changes**
   ```typescript
   // ✓ Good
   await expect(page).toHaveURL('/jobs')
   await expect(page.getByRole('button')).toBeVisible()

   // ✗ Avoid
   await page.goto('/click-button')
   await new Promise(r => setTimeout(r, 1000))
   ```

3. **Test user journeys, not implementation**
   ```typescript
   // ✓ Good: User perspective
   await page.getByLabel(/email/).fill('test@example.com')
   await page.getByRole('button', { name: /login/ }).click()

   // ✗ Avoid: Implementation details
   await page.evaluate(() => {
     window.authStore.setEmail('test@example.com')
     window.authStore.submitLogin()
   })
   ```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Testing Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Tests](https://playwright.dev/docs/debug)
- [CI/CD Integration](https://playwright.dev/docs/ci)

---

**Last Updated:** March 9, 2026
**Status:** Production Ready ✅
