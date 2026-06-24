import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('https://www.zoho.com/people/');
  await page.getByRole('link', { name: 'Sign In' }).click();
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).click();
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).fill('Reshni.Suyambudurai@kanini.com');
  await page.getByRole('button', { name: 'Next' }).click();
  await page.getByRole('textbox', { name: 'Enter your email, phone, or' }).fill('Reshni.Suyambudurai@kanini.com');
  await page.getByRole('button', { name: 'Next' }).click();
  await page.locator('#i0118').fill('Shree@123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('button', { name: 'Yes' }).click();
  await page.getByRole('listitem').filter({ hasText: 'Leave Tracker' }).locator('i').click();
  await page.getByRole('listitem', { name: 'Time Tracker' }).locator('i').click();
  await page.goto('https://myhrms.kanini.com/kanini/zp#timetracker/mydata/timelogs-mode:list');
  await page.locator('#my_logselectBtn').click();
  await page.getByText('Weekly Log').click();
  await page.getByRole('cell', { name: '2', exact: true }).click();
  await page.locator('#bulk_log_addrow').click();
  await page.locator('#weekjobselect14-container').getByText('Select').click();
// Instead of the dynamic ID selector:
//await page.locator('#zselect-37287888-listbox-11653000060460660 > .zdropdownlist__content > .zdropdownlist__text').click();

// Use the visible dropdown item directly:
await page.locator('.zdropdownlist__text').first().click();
// This ID is generated fresh every time the page loads. The numbers 37287888 and 11653000060460660 are internal session/instance IDs that Zoho assigns at runtime. So:

// When Codegen recorded it → ID was 37287888-...
// When the test runs → Zoho generates a completely different ID like #zselect-99413180-...
// Playwright looks for the old ID → finds nothing → timeout
  await page.locator('#weekworkitem14').click();
  await page.locator('#weekworkitem14').fill('00:01');
  await page.getByRole('button', { name: 'Save' }).click();
  
});