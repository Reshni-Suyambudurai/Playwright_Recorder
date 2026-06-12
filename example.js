// Import the Chromium browser launcher from Playwright.
const { chromium } = require('playwright');

// Run the browser logic inside an async function so await can be used.
(async () => {
  // Launch Chromium in headless mode.
  const browser = await chromium.launch({
    headless: true
  });

  // Open a new browser page.
  const page = await browser.newPage();

  // Go to the Playwright docs page.
  await page.goto(
    'https://playwright.dev/java/docs/locators',
    { waitUntil: 'networkidle' }
  );

  // Read all visible text from the body element.
  const text = await page.locator('body').innerText();

  // Split the text into separate lines and clean them up.
  const lines = text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0);

  // Print a label before showing the extracted lines.
  console.log('First 4 lines:\n');

  // Print the first four cleaned lines with numbering.
  lines.slice(0, 4).forEach((line, index) => {
    // Show the line number and the line text.
    console.log(`${index + 1}. ${line}`);
  });

  // Close the browser when finished.
  await browser.close();
})();