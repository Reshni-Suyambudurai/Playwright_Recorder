# Issues Faced in Playwright Automation

---

# Issue 1 — Sensitive Data Not Masked (ID-Based Selectors)

## Problem Example (Zoho)

```javascript
await page.getByRole('textbox', { name: 'Enter your email, phone, or' }).press('Enter');
await page.getByRole('button', { name: 'Next' }).click();

await page.locator('#i0118').fill('demopass@123');
await page.locator('#i0118').press('Enter');
```

The password value (`demopass@123`) was recorded against a generated ID selector (`#i0118`).

Because the selector contains no semantic information such as "password" or "login", downstream processing cannot easily identify the value as sensitive.

---

## Playwright Codegen Detect Password Fields


When Playwright Codegen records a `fill()` action, it inspects the DOM element being interacted with.

If the element is recognized as a password field (for example, an `<input type="password">`), Playwright marks the recorded event as sensitive.

Example JSONL event:

```json
{
  "name": "fill",
  "selector": "#i0118",
  "text": "demopass@123",
  "sensitive": true
}
```

The presence of:

```json
"sensitive": true
```

indicates that Playwright identified the field as containing sensitive information.

---




### Layer 1 — Honor Playwright's Sensitive Flag

```javascript
if (event.sensitive === true) {
  step.text = '[REDACTED]';
}
```

If Playwright identifies the value as sensitive, it is immediately masked.

---

### Layer 2 — Keyword-Based Detection

```javascript
function containsSensitiveHint(value) {
  return /(password|otp|secret|token|apikey|api_key|authorization|bearer)/i
    .test(String(value || ''));
}
```

This catches fields whose labels, names, placeholders, or locators contain security-related terms.

Examples:

```text
Password
OTP
Access Token
API Key
Authorization
Bearer Token
```

---

## Remaining Limitation

A selector such as:

```javascript
#i0118
```

contains no meaningful metadata.

If:

* no `sensitive` flag exists
* no label is available
* no placeholder exists
* no accessibility information exists

then automatic detection becomes extremely difficult.

Example:

```javascript
await page.locator('#i0118').fill('demopass@123');
```

In this situation, manual review or additional DOM inspection is required.

---

# Issue 2 — Google Authentication Blocked During Recording

## Problem

When recording workflows that begin with Google OAuth or Google Single Sign-On (SSO), Playwright Codegen may fail to complete authentication.

Common symptoms include:

* CAPTCHA challenges
* Additional verification screens
* MFA prompts
* "This browser may not be secure"
* Risk-based security checks
* Repeated login loops



Google uses multiple security mechanisms to detect suspicious login activity.


Automated browser sessions may be treated as higher-risk than normal user sessions.

As a result, authentication flows that work manually may fail during recording.

---

# Solution 1 — Save Session State and Reuse It 

## How It Works

1. Log in manually once.
2. Save cookies and browser storage.
3. Reuse the saved state for future recordings.
4. Start recording from an already authenticated page.

---

## Save Authentication State

```bash
npx playwright codegen --save-storage=auth.json https://www.zoho.com/people/
```

A browser opens.

Complete the login process manually, including:

* Google authentication
* MFA
* Device verification

Close the browser.

Playwright saves the session to:

```text
auth.json
```

---

## Reuse Authentication State

```bash
npx playwright codegen --load-storage=auth.json https://hrms.zoho.com/home
```

The browser launches already authenticated.

Recording can begin immediately without repeating Google login.

---

# Solution 2 — Reuse Existing Authentication

## Option A — Use a Persistent Browser Profile

Instead of logging in repeatedly, launch Playwright with a browser profile that already contains authentication data.

Example:

```javascript
const context =
  await chromium.launchPersistentContext(
    './user-data',
    {
      headless: false
    }
  );
```

The profile contains:

* Cookies
* Local Storage
* Session Data

allowing previously authenticated sessions to be reused.

---

## Option B — Restore Cookies

If valid session cookies are available:

```javascript
await context.addCookies([
  {
    name: 'ZSESSIONID',
    value: 'session-value',
    domain: '.zoho.com',
    path: '/'
  }
]);

await page.goto('https://hrms.zoho.com/home');
```

---

## Important Limitation

Modern applications may store authentication data in:

* Cookies
* Local Storage
* Session Storage
* IndexedDB

Therefore:

```text
Valid Cookie ≠ Guaranteed Login
```

Some applications require additional browser storage to be restored.

For this reason, Storage State is generally more reliable than cookie-only restoration.

---

## Solution 3 — Attach to an Existing Chrome Session (CDP)

### How Does "Attach To Existing Chrome" Work?

---

#### Step 1 — Close All Chrome Windows

Close all existing Chrome windows before starting.

---

#### Step 2 — Start Chrome with Remote Debugging

**Windows:**

```bash
chrome.exe --remote-debugging-port=9222
```

Or with full path:

```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

This starts Chrome and exposes a control endpoint at `http://localhost:9222`.

---

#### Step 3 — Log In Normally

Use Chrome exactly as a normal user and log in to any app, for example:

- Google
- Zoho
- Salesforce

---

#### Step 4 — Attach Playwright

```javascript
import { chromium } from '@playwright/test';

const browser = await chromium.connectOverCDP('http://localhost:9222');
```

Playwright is now controlling your already-running Chrome session.

---

### What Does Playwright See?

Instead of starting fresh:

```
Fresh Browser → No Cookies
```

Playwright sees the existing session:

```
Chrome → Google Cookies → Zoho Cookies → LinkedIn Cookies
```

because they already exist in the running browser.

---

### How Would Your Recorder Work?

Once Chrome is running and the user is logged in:

```
Chrome → User Logged In → Start Recorder
```

Recorder attaches to the running browser:

```javascript
const browser = await chromium.connectOverCDP('http://localhost:9222');
```

Gets the current page from the existing context:

```javascript
const context = browser.contexts()[0];
const page = context.pages()[0];
```

Now record actions as the user interacts:

```
Click → Type → Navigate → Scroll
```

## What Playwright Does NOT Give You

Out of the box Playwright gives:

✓ Browser Control
✓ Click
✓ Type
✓ Download
✓ Upload
✓ Screenshots
✓ Network Interception

It does NOT give:

✗ Workflow Recorder
✗ Business Process Designer
✗ Task Scheduler
✗ Credential Vault
✗ Workflow Dashboard
✗ Human Approval Steps
✗ Enterprise Orchestration

Those are RPA platform features.





### Issue Summary: Recorded SAML/Microsoft Login URL Fails During Replay

#### Problem

During recording, Playwright captured a Microsoft SSO/SAML authentication URL:

```ts id="s9q9ow"
await page.goto(
  'https://login.microsoftonline.com/...SAMLRequest=...&RelayState=...'
);
```

When the script is replayed later, Playwright throws:

```text id="z4x8y9"
ERR_ABORTED
```

and navigation fails.

---

#### Root Cause

The recorded URL is not a normal application URL.

It is a temporary SAML authentication request generated during the login process and contains:

```text id="jjwxpk"
SAMLRequest
RelayState
Session-specific data
One-time authentication tokens
```

These values are only valid for the original login session.

When replayed later:

```text id="30dld4"
SAML Request Expired
or
SAML Request Already Consumed
or
Authentication Context Invalid
```

and Microsoft rejects the request.

---

#### Why It Happens

Playwright Codegen records browser navigations exactly as they occur.

During SSO authentication:

```text id="s6h4yt"
Zoho
↓
Redirects to Microsoft
↓
Generates Temporary SAML URL
↓
Codegen Records URL
```

The recorded URL works only during that specific authentication flow and is not suitable for long-term replay.

---

#### Resolution

Remove the recorded:

```ts id="gl2ikc"
page.goto('https://login.microsoftonline.com/...SAMLRequest=...')
```

statement.

Instead:

1. Start from the application's normal login page.
2. Allow the application to perform redirects naturally.
3. Reuse an authenticated session (`storageState`, persistent profile, or existing Chrome session) when possible.

---

#### Key Learning

> Authentication URLs generated by OAuth, SAML, Google Sign-In, or Microsoft Sign-In are typically temporary and should not be hardcoded into Playwright automation scripts. Only stable application URLs should be used for replay.


iN THE Timesheet
 2 unit testing