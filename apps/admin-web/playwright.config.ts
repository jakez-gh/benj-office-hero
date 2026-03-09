import { defineConfig, devices } from '@playwright/test';

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
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'  // Record video on test failures
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

  webServer: {
    command: 'pnpm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI
  }
});
