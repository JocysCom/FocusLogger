import { test, expect } from '@playwright/test';

test.describe('Demo', () => {
  test('example.com has the Example Domain heading @demo', async ({ page }) => {
    await page.goto('https://example.com/');

    await expect(page.getByRole('heading', { name: 'Example Domain' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'More information...' })).toBeVisible();
  });
});
