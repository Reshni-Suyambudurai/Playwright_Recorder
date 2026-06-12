## Project Structure

- [package.json](../package.json) sets up the Node project and lists the Playwright dependencies.
- [package-lock.json](../package-lock.json) locks the exact dependency versions used in the project.
- [.gitignore](../.gitignore) ignores generated Playwright output like reports, test results, and cache folders.
- [playwright.config.ts](../playwright.config.ts) is the main Playwright test configuration file.
- [example.js](../example.js) is a simple browser script that opens example.com, prints the page title, and closes the browser.
- [example2.js](../example2.js) is a scraping-style script that opens a Playwright demo page, collects paragraph text, prints a few results, and closes the browser.
- [tests/playwrightdev.spec.ts](../tests/playwrightdev.spec.ts) is a sample test file with two tests against playwright.dev.
- [tests/medium.spec.ts](../tests/medium.spec.ts) is a longer TodoMVC-style test that types, clicks, checks content, and verifies page state.
- [Hint/PlaywrightNotes.md](PlaywrightNotes.md) is currently empty.

## What `playwright.config.ts` Does

This file tells Playwright where the tests live, which browsers to run, and how to report results.

- `testDir: './tests'` means Playwright looks for tests inside the tests folder.
- `fullyParallel: true` lets tests run in parallel when possible.
- `forbidOnly: !!process.env.CI` helps prevent accidental `test.only` from reaching CI.
- `retries: process.env.CI ? 2 : 0` retries failed tests only in CI.
- `workers: process.env.CI ? 1 : undefined` keeps CI more stable by using one worker.
- `reporter: 'html'` creates an HTML test report.
- `use.trace: 'on-first-retry'` records a trace when a test fails and is retried.
- `projects` defines the browsers: Chromium, Firefox, and WebKit.

## How To Run The Files

### Plain JavaScript Files

- Run [example.js](../example.js): `node example.js`
- Run [example2.js](../example2.js): `node example2.js`

Note: these files have the browser mode hardcoded inside them.

- `example.js` runs headed because it sets `headless: false`.
- `example2.js` runs headless because it sets `headless: true`.

### Test Files

- Run all tests headless: `npx playwright test`
- Run all tests headed: `npx playwright test --headed`
- Run [tests/playwrightdev.spec.ts](../tests/playwrightdev.spec.ts) headless: `npx playwright test tests/playwrightdev.spec.ts`
- Run [tests/playwrightdev.spec.ts](../tests/playwrightdev.spec.ts) headed: `npx playwright test tests/playwrightdev.spec.ts --headed`
- Run [tests/medium.spec.ts](../tests/medium.spec.ts) headless on Chromium: `npx playwright test tests/medium.spec.ts --project=chromium`
- Run [tests/medium.spec.ts](../tests/medium.spec.ts) headed on Chromium: `npx playwright test tests/medium.spec.ts --headed --workers=1 --project=chromium`
- Open Playwright UI mode: `npx playwright test --ui`
- Run in debug mode: `npx playwright test tests/medium.spec.ts --debug`

## Quick File-by-File Summary

- [example.js](../example.js): opens a browser, visits a site, prints the title, and closes.
- [example2.js](../example2.js): visits a docs page and extracts paragraph text.
- [tests/playwrightdev.spec.ts](../tests/playwrightdev.spec.ts): checks the Playwright homepage and a navigation link.
- [tests/medium.spec.ts](../tests/medium.spec.ts): automates TodoMVC actions and assertions.
- [playwright.config.ts](../playwright.config.ts): controls test discovery, browsers, retries, traces, and reporting.
