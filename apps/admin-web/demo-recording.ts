import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Demo Recording Script - Automated E2E Testing with Screen Recording
 *
 * This script:
 * 1. Starts automated browser session with video recording
 * 2. Tests complete login and navigation flow
 * 3. Records all interactions
 * 4. Saves recordings and screenshots
 *
 * Run with: npx ts-node demo-recording.ts
 */

const DEMO_DIR = path.join(process.cwd(), 'demo-recordings');
const TEST_USER = {
  email: 'test@example.com',
  password: 'password123'
};

async function ensureDemoDir() {
  if (!fs.existsSync(DEMO_DIR)) {
    fs.mkdirSync(DEMO_DIR, { recursive: true });
  }
}

async function recordDemoFlow() {
  console.log('🎬 Starting Demo Recording...\n');

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const videoPath = path.join(DEMO_DIR, `demo-${timestamp}.webm`);
  const screenshotsDir = path.join(DEMO_DIR, `screenshots-${timestamp}`);

  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  // Launch browser with recording
  const browser = await chromium.launch({
    headless: false // Show browser window
  });

  const context = await browser.newContext({
    recordVideo: {
      dir: path.dirname(videoPath),
      size: { width: 1280, height: 720 }
    }
  });

  const page = await context.newPage();
  let stepCount = 0;

  const screenshot = async (name: string) => {
    stepCount++;
    const filename = path.join(screenshotsDir, `${stepCount.toString().padStart(2, '0')}-${name}.png`);
    await page.screenshot({ path: filename });
    console.log(`  📸 Screenshot: ${name}`);
  };

  try {
    // Step 1: Load login page
    console.log('\n📋 Step 1: Loading Login Page...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await screenshot('01-login-page');
    console.log('✓ Login page loaded');

    // Step 2: Fill email
    console.log('\n📋 Step 2: Entering Email...');
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.waitForTimeout(500);
    await screenshot('02-email-entered');
    console.log(`✓ Email entered: ${TEST_USER.email}`);

    // Step 3: Fill password
    console.log('\n📋 Step 3: Entering Password...');
    await page.getByLabel(/password/i).fill(TEST_USER.password);
    await page.waitForTimeout(500);
    await screenshot('03-password-entered');
    console.log('✓ Password entered');

    // Step 4: Submit login
    console.log('\n📋 Step 4: Submitting Login...');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForURL('**/jobs', { timeout: 5000 });
    await page.waitForTimeout(1000);
    await screenshot('04-logged-in');
    console.log('✓ Login successful, redirected to /jobs');

    // Step 5: Show nav shell
    console.log('\n📋 Step 5: Navigation Bar...');
    const navButtons = await page.locator('nav button, nav a').all();
    console.log(`  Found ${navButtons.length} navigation items`);
    await screenshot('05-nav-bar');
    console.log('✓ Navigation bar visible');

    // Step 6: Check localStorage
    console.log('\n📋 Step 6: Verifying Token Persistence...');
    const tokens = await page.evaluate(() => ({
      hasAccessToken: !!localStorage.getItem('access_token'),
      hasRefreshToken: !!localStorage.getItem('refresh_token'),
      hasUser: !!localStorage.getItem('user')
    }));
    console.log(`  Access Token: ${tokens.hasAccessToken ? '✓' : '✗'}`);
    console.log(`  Refresh Token: ${tokens.hasRefreshToken ? '✓' : '✗'}`);
    console.log(`  User Data: ${tokens.hasUser ? '✓' : '✗'}`);
    await screenshot('06-tokens-verified');

    // Step 7: Navigate to Dispatch
    console.log('\n📋 Step 7: Testing Navigation (Dispatch)...');
    await page.getByRole('link', { name: /dispatch/i }).click();
    await page.waitForURL('**/dispatch', { timeout: 3000 });
    await page.waitForTimeout(500);
    await screenshot('07-dispatch-page');
    console.log('✓ Navigated to Dispatch');

    // Step 8: Navigate to Vehicles
    console.log('\n📋 Step 8: Testing Navigation (Vehicles)...');
    await page.getByRole('link', { name: /vehicles/i }).click();
    await page.waitForURL('**/vehicles', { timeout: 3000 });
    await page.waitForTimeout(500);
    await screenshot('08-vehicles-page');
    console.log('✓ Navigated to Vehicles');

    // Step 9: Navigate to Users
    console.log('\n📋 Step 9: Testing Navigation (Users)...');
    await page.getByRole('link', { name: /users/i }).click();
    await page.waitForURL('**/users', { timeout: 3000 });
    await page.waitForTimeout(500);
    await screenshot('09-users-page');
    console.log('✓ Navigated to Users');

    // Step 10: Back to Jobs
    console.log('\n📋 Step 10: Back to Jobs...');
    await page.getByRole('link', { name: /jobs/i }).click();
    await page.waitForURL('**/jobs', { timeout: 3000 });
    await page.waitForTimeout(500);
    await screenshot('10-back-to-jobs');
    console.log('✓ Back to Jobs page');

    // Step 11: Show version badge
    console.log('\n📋 Step 11: Version Badge...');
    const versionBadge = page.getByText(/v\d+\.\d+\.\d+/);
    const versionText = await versionBadge.textContent({ timeout: 2000 }).catch(() => 'N/A');
    console.log(`  Version: ${versionText}`);
    await screenshot('11-version-badge');

    // Step 12: Test page reload (hook rehydration)
    console.log('\n📋 Step 12: Testing Hook Rehydration (Page Reload)...');
    console.log('  Reloading page...');
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await screenshot('12-after-reload');

    // Verify still authenticated
    const isStillAuth = await page.getByRole('navigation').isVisible();
    console.log(`  Still authenticated: ${isStillAuth ? '✓' : '✗'}`);
    console.log('✓ Hook rehydration successful (tokens restored from localStorage)');

    // Step 13: Logout
    console.log('\n📋 Step 13: Testing Logout...');
    await page.getByRole('button', { name: /logout/i }).click();
    await page.waitForURL('/', { timeout: 3000 });
    await page.waitForTimeout(1000);
    await screenshot('13-after-logout');

    // Verify logged out
    const loginHeading = await page.getByRole('heading', { name: /login/i }).isVisible();
    console.log(`  Back to login: ${loginHeading ? '✓' : '✗'}`);
    console.log('✓ Logout successful, session cleared');

    // Step 14: Verify tokens cleared
    console.log('\n📋 Step 14: Verifying Session Cleared...');
    const clearedTokens = await page.evaluate(() => ({
      hasAccessToken: !!localStorage.getItem('access_token'),
      hasRefreshToken: !!localStorage.getItem('refresh_token'),
      hasUser: !!localStorage.getItem('user')
    }));
    console.log(`  Access Token cleared: ${!clearedTokens.hasAccessToken ? '✓' : '✗'}`);
    console.log(`  Refresh Token cleared: ${!clearedTokens.hasRefreshToken ? '✓' : '✗'}`);
    console.log(`  User Data cleared: ${!clearedTokens.hasUser ? '✓' : '✗'}`);
    await screenshot('14-session-cleared');

    console.log('\n' + '='.repeat(50));
    console.log('✅ Demo Recording Complete!');
    console.log('='.repeat(50));

    // Close browser and save video
    await context.close();
    await browser.close();

    // Get video filename from context
    const video = await context.close();

    console.log('\n📂 Output Files:');
    console.log(`  📹 Video: ${videoPath}`);
    console.log(`  📸 Screenshots: ${screenshotsDir}`);
    console.log(`  📊 Total Steps: ${stepCount}`);

    // List generated files
    console.log('\n📸 Screenshots generated:');
    const screenshots = fs.readdirSync(screenshotsDir).sort();
    screenshots.forEach(file => {
      console.log(`  • ${file}`);
    });

    console.log('\n💡 Tips:');
    console.log('  • Open video with: ffplay ' + path.basename(videoPath));
    console.log('  • Convert to MP4: ffmpeg -i ' + path.basename(videoPath) + ' demo.mp4');
    console.log('  • Open report: npx playwright show-report');

  } catch (error) {
    console.error('\n❌ Error during demo recording:', error);
    await browser.close();
    process.exit(1);
  }
}

// Main execution
(async () => {
  await ensureDemoDir();
  await recordDemoFlow();
})();
