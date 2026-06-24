import { defineConfig, devices } from '@playwright/test';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// import dotenv from 'dotenv';
// import path from 'path';
// dotenv.config({ path: path.resolve(__dirname, '.env') });

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests',

  /* Maximum time (ms) one test can run before it is marked as failed. */
  timeout: 120_000, //120 seconds = 2 minutes

  /* Maximum time (ms) for expect() assertions to wait before failing. */
  expect: {
    timeout: 10_000,
  },

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry failed tests — 2 retries on CI, 0 locally. */
  retries: process.env.CI ? 2 : 0,

  /* Limit parallel workers — 1 on CI to avoid resource contention, auto locally. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { open: 'on-failure' }],  // Opens HTML report automatically only when tests fail
    ['list'],                           // Prints a live result line per test in the terminal
  ],

  /* Shared settings for all projects below. */
  use: {
    /* Base URL — set this so tests can use page.goto('/path') instead of full URLs. */
    // baseURL: 'https://your-app.example.com',

    /* How long (ms) each action (click, fill, etc.) can take before timing out. */
   // actionTimeout: 60_000,

    /* How long (ms) page.goto() and page.waitForNavigation() can take. */
  //  navigationTimeout: 90_000,

    /* Capture screenshot on test failure for debugging. */
    screenshot: 'only-on-failure',

    /* Record video only when a test fails — saves disk space. */
    video: 'retain-on-failure',

    /* Collect a full Playwright trace on the first retry of a failed test. */
    trace: 'on-first-retry',

    /* Run browser in headed (visible) mode locally; headless on CI. */
    headless: !!process.env.CI,

    /* Ignore HTTPS certificate errors (useful for self-signed certs in dev/staging). */
    ignoreHTTPSErrors: true,

    /* Viewport size — matches a standard 1080p desktop screen. */
    viewport: { width: 1280, height: 720 },

    /* Locale and timezone for consistent date/number formatting across environments. */
    locale: 'en-US',
    timezoneId: 'Asia/Kolkata',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    /* Test against mobile viewports. */
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: { ...devices['iPhone 12'] },
    // },

    /* Test against branded browsers. */
    // {
    //   name: 'Microsoft Edge',
    //   use: { ...devices['Desktop Edge'], channel: 'msedge' },
    // },
    // {
    //   name: 'Google Chrome',
    //   use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    // },
  ],

  /* Run your local dev server before starting the tests */
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
