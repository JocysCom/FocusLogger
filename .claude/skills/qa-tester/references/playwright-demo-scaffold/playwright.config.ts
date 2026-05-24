import { defineConfig, devices } from '@playwright/test';

// Demo-oriented config.
// - Demo tests are excluded from default runs/CI by default.
// - Run demo explicitly with: npx playwright test --grep @demo
export default defineConfig({
  testDir: './',
  testMatch: ['**/*.spec.ts'],
  grepInvert: /@demo/,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
