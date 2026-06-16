import { test, type Page } from '@playwright/test';
import path from 'node:path';

/**
 * Generates documentation/verification screenshots for every admin-web route.
 *
 * Local: `pnpm --filter admin-web exec playwright test tests/screenshots.spec.ts`
 *        (writes to apps/admin-web/screenshots/)
 * CI:    same; workflow uploads as artifact, and on main also commits the
 *        diff to docs/screenshots/admin-web/ so the rendered docs stay current.
 *
 * Auth is bypassed by seeding localStorage before each navigation. The screen-
 * shots show the page shells; data-driven content shows error/empty states
 * because no backend runs alongside (this is intentional — we want the UI
 * shell visible regardless of API state).
 */

const VIEWPORTS = {
  desktop: { width: 1280, height: 800 },
  mobile: { width: 375, height: 812 },
} as const;

const ROUTES: ReadonlyArray<{ name: string; path: string; auth: boolean }> = [
  { name: '01-login', path: '/', auth: false },
  { name: '02-jobs', path: '/jobs', auth: true },
  { name: '03-dispatch', path: '/dispatch', auth: true },
  { name: '04-vehicles', path: '/vehicles', auth: true },
  { name: '05-users', path: '/users', auth: true },
  { name: '06-customers', path: '/customers', auth: true },
  { name: '07-contracts', path: '/contracts', auth: true },
  { name: '08-routes', path: '/routes', auth: true },
];

const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR ?? 'screenshots';

async function seedAuth(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'ci-screenshot-token');
    localStorage.setItem('refresh_token', 'ci-screenshot-refresh');
    localStorage.setItem(
      'user',
      JSON.stringify({ id: '00000000-0000-0000-0000-000000000001', email: 'ci@officehero.dev', role: 'Operator' })
    );
  });
}

for (const [viewport, size] of Object.entries(VIEWPORTS)) {
  test.describe(`UI screenshots — ${viewport}`, () => {
    test.use({ viewport: size });

    for (const route of ROUTES) {
      test(`${route.name} (${route.path})`, async ({ page }) => {
        if (route.auth) await seedAuth(page);
        // Determinism: no backend runs during capture, but a slow connection
        // refusal can land before OR after the screenshot, racing skeleton vs
        // error states. Abort ALL fetch/xhr (any origin — direct :8000 calls
        // and same-origin axios paths alike) so every page settles to the
        // same state every run; documents/scripts/styles still load.
        await page.route('**/*', (r) => {
          const type = r.request().resourceType();
          if (type === 'fetch' || type === 'xhr') {
            void r.abort('connectionrefused');
          } else {
            void r.continue();
          }
        });
        await page.goto(route.path, { waitUntil: 'load' });
        // Determinism: freeze CSS animation (skeleton pulse) and hide the
        // per-commit version label, or back-to-back captures differ and the
        // pre-push hook would refresh screenshots on every single push.
        await page.addStyleTag({
          content: `
            *, *::before, *::after {
              animation: none !important;
              transition: none !important;
              caret-color: transparent !important;
            }
            [data-testid="app-version"] { visibility: hidden !important; }
          `,
        });
        // Outlast the pages' 300ms search debounce and Vite dynamic-import
        // chunk loading so the post-load re-render can't race the capture.
        await page.waitForTimeout(300);
        // For authenticated pages every API call is aborted above, so the page
        // will always end up in an error state. Wait for the error banner to
        // appear before capturing — this eliminates the skeleton-vs-error race
        // on slow machines without needing a fixed wall-clock timeout.
        if (route.auth) {
          await page.waitForSelector('[role="alert"]', {
            state: 'visible',
            timeout: 4000,
          }).catch(() => {
            // Page settled without an alert (e.g. Dispatch shows inline errors).
            // Fall through and capture whatever is rendered.
          });
        }
        await page.screenshot({
          path: path.join(SCREENSHOT_DIR, viewport, `${route.name}.png`),
          fullPage: true,
          animations: 'disabled',
        });
      });
    }
  });
}
