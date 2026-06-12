// Import the Chromium browser launcher from Playwright.
const { chromium } = require('playwright');

// This script extracts text from a webpage.
// Wrap everything in an async function so await can be used.
(async () => {
  // Launch Chromium in headless mode.
  const browser = await chromium.launch({
    headless: true
  });

  // Open a new browser page.
  const page = await browser.newPage();

  // Navigate to the Playwright docs page and wait for network activity to settle.
  await page.goto(
    'https://playwright.dev/java/docs/locators',
    { waitUntil: 'networkidle' }
  );

  // Collect the text from all paragraph elements.
  const paragraphs = await page.locator('p').allTextContents();

  // Remove empty or whitespace-only paragraph entries.
  const filtered = paragraphs
    .map(p => p.trim())
    .filter(p => p.length > 0);

  // Print how many paragraphs were found.
  console.log(`Found ${filtered.length} paragraphs\n`);

  // Print the first 10 paragraphs with numbering.
  filtered.slice(0, 10).forEach((text, index) => {
    // Print the paragraph number.
    console.log(`Paragraph ${index + 1}:`);
    // Print the paragraph text.
    console.log(text);
    // Add spacing between entries for readability.
    console.log('\n---------------------------------\n');
  });

  // Close the browser after scraping is complete.
  await browser.close();
})();