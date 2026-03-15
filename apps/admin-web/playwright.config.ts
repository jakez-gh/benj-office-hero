import { defineConfig, devices } from '@playwright/test';

const managedBaseUrl = process.env.PLAYWRIGHT_BASE_URL;
const skipWebServer = process.env.SKIP_PLAYWRIGHT_WEBSERVER === '1';
const defaultBaseUrl = 'http://127.0.0.1:3000';
const baseURL = managedBaseUrl ?? defaultBaseUrl;

export default defineConfig({
  testDir: './src/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure' // Record video on test failures
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        video: process.env.RECORD_VIDEO ? 'on' : 'retain-on-failure'
      }
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        video: process.env.RECORD_VIDEO ? 'on' : 'retain-on-failure'
      }
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        video: process.env.RECORD_VIDEO ? 'on' : 'retain-on-failure'
      }
    }
  ],

  webServer: skipWebServer
    ? undefined
    : {
        command: 'pnpm run dev -- --host 127.0.0.1 --port 3000 --strictPort',
        url: defaultBaseUrl,
        reuseExistingServer: !process.env.CI
      }
});
