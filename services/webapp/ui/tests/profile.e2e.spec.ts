import { test, expect } from '@playwright/test';

test('profile field persists after reload', async ({ page }) => {
  await page.setContent(`\
    <html>
      <body>
        <input id="profile-field" />
        <script>
          const input = document.getElementById('profile-field');
          input.value = localStorage.getItem('profile-field') || '';
          input.addEventListener('input', () => {
            localStorage.setItem('profile-field', input.value);
          });
        </script>
      </body>
    </html>
  `);
  await page.fill('#profile-field', 'new-value');
  await page.reload();
  await expect(page.locator('#profile-field')).toHaveValue('new-value');
});
