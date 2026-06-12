import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('https://www.zoho.com/people/');
  await page.getByRole('link', { name: 'Sign In' }).click();
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).click();
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).fill('Reshni.Suyambudurai@kanini.com');
  await page.getByRole('button', { name: 'Next' }).click();  await page.getByRole('textbox', { name: 'Enter your email, phone, or' }).fill('Reshni.Suyambudurai@kanini.com');
  await page.getByRole('button', { name: 'Next' }).click();
  await page.locator('#i0118').fill('demo@123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('button', { name: 'Yes' }).click();
  await page.getByRole('listitem').filter({ hasText: 'Leave Tracker' }).locator('i').click();
  await page.getByRole('listitem').filter({ hasText: 'Time Tracker' }).locator('i').click();
  await page.locator('#my_logselectBtn').click();
  await page.getByRole('menuitem', { name: 'Weekly Log' }).click();
  await page.locator('#bulk_log_addrow').click();
  await page.locator('#weekclientselect12-container > .zselectbox__icon > .zselectbox__arrow').click();
  await page.locator('#zselect-22424481-listbox-11653000019440024 > .zdropdownlist__content > .zdropdownlist__text').click();
  await page.locator('#weekprojectselect12-container').getByText('Select').click();
  await page.getByRole('cell', { name: 'Add Row Total' }).click();
  await page.locator('#weekprojectselect12-container > .zselectbox__icon > .zselectbox__arrow').click();
  await page.locator('#zselect-9359064-listbox-11653000035404926 > .zdropdownlist__content > .zdropdownlist__text').click();
  await page.locator('#zselect-9359064-listbox-11653000035404926 > .zdropdownlist__content > .zdropdownlist__text').click();
  await page.locator('#weekrow12 > td:nth-child(8) > .zpl_flexaligngap3 > #daytxt2').fill('1');
  await page.locator('#weekrow12 > td:nth-child(9) > .zpl_flexaligngap3 > #daytxt3').fill('1');
  await page.locator('#weekrow12 > td:nth-child(10) > .zpl_flexaligngap3 > #daytxt4').fill('1');
});