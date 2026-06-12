# Playwright Notes

## What Is Playwright?

Playwright is a browser automation framework for testing and interacting with web apps in Chromium, Firefox, and WebKit. It can run in headed mode for visibility or headless mode for speed.

### Why Use Playwright?

- **Cross-browser support**: Tests run on Chromium, Firefox, and WebKit with a single API.
- **Auto-waiting**: Automatically waits for elements to be ready, which reduces flaky tests.
- **Faster and more reliable**: Handles modern web apps and dynamic content well.
- **Built-in parallel execution**: Runs tests concurrently for faster execution.
- **Powerful debugging tools**: Trace Viewer, screenshots, videos, and network logs help diagnose failures quickly.
- **Supports multiple languages**: Works with JavaScript, TypeScript, Python, Java, and .NET.
- **End-to-end and API testing**: Can test both UI and backend APIs in the same framework.
- **Mobile and responsive testing**: Emulates mobile devices and different screen sizes.
- **Easy setup**: Needs minimal configuration compared to many alternatives.
- **Modern architecture**: Designed for SPAs and other complex web applications.

## The 5 Core Playwright Objects

### 1. Browser

The browser is the actual browser process launched by Playwright.

Example:

```js
const browser = await chromium.launch({ headless: true });
```

### 2. Browser Context

A browser context is an isolated browser session with its own cookies and storage.

Example:

```js
const context = await browser.newContext();
```

### 3. Page

A page is a browser tab where you load a website and interact with it.

Example:

```js
const page = await context.newPage();
await page.goto('https://example.com');
```

### 4. Locator

A locator is the preferred way to find elements on the page.

Example:

```js
await page.getByRole('button', { name: 'Submit' }).click();
```

### 5. Assertions

Assertions check whether the expected result is true.

Example:

```js
await expect(page).toHaveTitle(/Playwright/);
```

## - Debugging

### Recorder

Use Codegen to record browser actions and generate Playwright code.

Example:

```bash
npx playwright codegen https://www.zoho.com/people/login.html
```

### Player

Run the test normally to replay the script and see the automation flow.

Example:

```bash
npx playwright test tests/medium.spec.ts
```
```bash
npx playwright test tests/medium.spec.ts --headed
```

```bash
npx playwright test tests/medium.spec.ts --headed --project=chromium
```

### HTML Report

Open the HTML report after a test run to see results in a browser.

Example:

```bash
npx playwright test tests/medium.spec.ts
npx playwright show-report
```

![Screenshot 1](images/Screenshot%202026-06-09%20235403.png)

### Tracing

Use traces to inspect what happened during the test step by step.

Example:

```bash
npx playwright test tests/medium.spec.ts --trace on
```

Example:

```bash
npx playwright test --trace on
```

Open the trace viewer:

```bash
npx playwright show-trace test-results\medium-test-chromium\trace.zip
```

![Screenshot 2](images/Screenshot%202026-06-09%20235709.png)


### Screenshots

Playwright can capture screenshots during the test run for visual checks.

Example:

 use: {
 screenshot: 'only-on-failure',
 video: 'retain-on-failure',
 trace: 'on-first-retry',
},

```bash
npx playwright test tests/medium.spec.ts --project=chromium
```

Screenshot output:

```text
test-results\medium-test-chromium\screenshot.png
```

![Screenshot 3](images/Screenshot%202026-06-10%20000116.png)


### Video Recording

Playwright can save a video of the full browser session for debugging.

Example:

```bash
npx playwright test tests/medium.spec.ts --project=chromium
```

Typical output files:

```text
test-results
  └── medium-test-chromium
      ├── trace.zip
      ├── screenshot.png
      ├── video.webm
      └── error-context.md
```

### Playwright Inspector

Use debug mode to pause execution and inspect the page interactively.

Example:

```bash
npx playwright test tests/medium.spec.ts --debug --project=chromium
```

You can also pause inside the test:

```js
await page.pause();
```

![Screenshot 4](images/Screenshot%202026-06-10%20000252.png)




## Playwright Features

### Cross-browser support

Run the same test on Chromium, Firefox, and WebKit.

Example:

```bash
npx playwright test --project=chromium
```

### Headed and headless execution

Run with a visible browser for debugging or without UI for speed.

Example:

```bash
npx playwright test --headed
```

Example:

```bash
npx playwright test
```

### Auto-waiting

Playwright waits for elements to be ready before interacting with them.

Example:

```js
await page.getByRole('button', { name: 'Submit' }).click();
```

###  Locator

A **Locator** is a Playwright method used to find and interact with elements on a web page.

#### Examples

```javascript
await page.getByRole('button', { name: 'Submit' }).click();

await page.getByLabel('Email').fill('user@example.com');

await page.getByText('Login').click();
```

---

###  Selector

A **Selector** is a string pattern used to identify elements in the DOM.

#### Examples

##### CSS Selector

```javascript
await page.locator('#username').fill('user');
await page.locator('.submit-btn').click();
```

##### XPath Selector

```javascript
await page.locator('//button[text()="Submit"]').click();
```

---

#### Recommended Locator Priority

Use locators in the following order:

1. `getByRole()`
2. `getByLabel()`
3. `getByPlaceholder()`
4. `getByText()`
5. `getByAltText()`
6. `getByTitle()`
7. `getByTestId()`
8. CSS Selector
9. XPath Selector

- Page     -> Browser tab

- Locator  -> Find elements

- POM      -> Organize automation framework

### Assertions

Check whether the expected result is true.

Example:

```js
await expect(page).toHaveTitle(/Playwright/);
```

### Frames

Interact with content inside iframes.

Example:

```js
await page.frameLocator('iframe').getByRole('button', { name: 'Submit' }).click();
```

### Element handles

Work with a specific DOM element directly when needed.

Example:

```js
const button = await page.$('button');
```

### Downloads

Capture and verify files downloaded by the browser.

Example:

```js
const downloadPromise = page.waitForEvent('download');
```

### Events

Listen for browser or page events such as request, response, download, or popup.

Example:

```js
page.on('console', message => console.log(message.text()));
```

### Network

Inspect, wait for, or mock HTTP requests and responses.

Example:

```js
await page.waitForResponse('**/api/users');
```

### Navigation

Move through pages, routes, and browser history.

Example:

```js
await page.goto('https://example.com');
```

### Screenshots

Capture page or element images for verification and reporting.

Example:

```js
await page.screenshot({ path: 'home.png' });
```

### Touch events

Test touch-based interaction on mobile-like devices.

Example:

```js
await page.touchscreen.tap(100, 200);
```

### Multithreading / parallel execution

Run tests in parallel using multiple workers.

Example:

```ts
fullyParallel: true
```

### POM (Page Object Model)

Organize selectors and actions into reusable page classes.

Example:

```js
await loginPage.login('user1', 'secret');
```

### Clock

Control time in tests by mocking or advancing the clock.

Example:

```js
await page.clock.install();
```

### Trace Viewer

Open traces to inspect actions, screenshots, and timelines after a run.

Example:

```bash
npx playwright show-trace trace.zip
```

### Extensibility

Extend Playwright with fixtures, test hooks, plugins, and custom helpers.

Example:

```js
test.extend({ myFixture: async ({}, use) => { await use('value'); } })
```

### WebView2

Automate or test web content hosted inside a WebView2 app on Windows.

Example:

Launch the app and inspect the embedded browser content through Playwright integration.

### Tracing and debugging

Collect traces, screenshots, and videos to inspect failures.

Example:

```bash
npx playwright test --debug
```

### Test runner support

Organize tests with `test()` and reusable fixtures.

Example:

```js
test('my test', async ({ page }) => { ... })
```

### Device and browser emulation

Test different screen sizes, user agents, and device presets.

Example:

```ts
use: { ...devices['Desktop Chrome'] }
```

### Trace on failure retry

Capture a trace automatically when a test fails and retries.

Example:

```ts
trace: 'on-first-retry'
```



## Real-World Use Cases

- Login flow testing: verify a user can sign in and reach the dashboard.
	- Example: fill username, fill password, click login, check dashboard.
- E-commerce checkout: validate cart, coupon, payment, and order confirmation flows.
	- Example: add product, apply coupon, complete checkout.
- Form validation testing: check required fields, email validation, and error messages.
	- Example: submit an empty form and confirm validation text appears.
- Regression testing: re-run key user journeys after code changes to catch breaks.
	- Example: run the same smoke test after every deployment.
- Web scraping and data extraction: pull headings, paragraphs, or table data from a page.
	- Example: `const text = await page.locator('body').innerText();`
- Cross-browser compatibility testing: confirm the app works in all supported browsers.
	- Example: run the same test in Chromium, Firefox, and WebKit.
- UI smoke testing: quickly confirm the main screens load and major buttons work.
	- Example: open home page, click menu, verify the page changes.
- Accessibility checking: verify roles, labels, and headings are exposed correctly.
	- Example: `await page.getByRole('button', { name: 'Submit' }).click();`

## Common Commands

```bash
npx playwright test
npx playwright test --headed
npx playwright test --debug
npx playwright test --ui
```


### AST

Playwright Codegen can be thought of as:

```text
Playwright Codegen
      ↓
    TypeScript
      ↓
 JSON / JSONL
      ↓
 Database / API
      ↓
 TypeScript Generator
      ↓
 Playwright Execution
```

Or:

```text
Browser Actions
      ↓
  JSONL (source of truth)
      ↓
 Generate TypeScript when needed
```


## Short Summary

Playwright is mainly used for browser automation and testing. The first things to understand are the browser, context, page, locator, and assertions. After that, the key strengths are cross-browser support, auto-waiting, debugging tools, and real-world workflow coverage.
