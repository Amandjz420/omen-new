import {expect, test} from '@playwright/test';

// The authenticated journey runs against the real backend, with a login supplied
// in the environment and never in the code:
//   E2E_USERNAME=... E2E_PASSWORD=... npm run e2e
const USER = process.env.E2E_USERNAME, PASSWORD = process.env.E2E_PASSWORD;

test('the sign-in screen carries the Omen Assessors band and fits the screen', async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('heading', {name: 'Sign in'})).toBeVisible();
  await expect(page.getByText('OMEN', {exact: true})).toBeVisible();
  await expect(page.getByLabel('Username')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);                                 // no sideways scrolling, even on a phone
});

test('an unknown address says so, instead of showing a blank page', async ({page}) => {
  await page.goto('/no-such-page');
  await expect(page.getByRole('heading', {name: 'Sign in'})).toBeVisible();   // signed out: the gate comes first
});

test.describe('signed in', () => {
  test.skip(!USER || !PASSWORD, 'Set E2E_USERNAME and E2E_PASSWORD to run the journey against the backend');

  test.beforeEach(async ({page}) => {
    await page.goto('/');
    await page.getByLabel('Username').fill(USER);
    await page.getByLabel('Password', {exact: true}).fill(PASSWORD);
    await page.getByRole('button', {name: 'Sign in'}).click();
    await expect(page.getByRole('heading', {name: 'My work'})).toBeVisible();
  });

  test('my work shows what is waiting at each stage', async ({page}) => {
    const track = page.getByRole('list', {name: 'Work waiting at each stage'});
    await expect(track).toBeVisible();
    await expect(track.getByRole('listitem')).toHaveCount(7);
  });

  test('a lead opens at its own address with the stage of each case', async ({page}) => {
    await page.goto('/leads');
    await page.getByRole('table').getByRole('link').first().click();
    await expect(page).toHaveURL(/\/leads\/[0-9a-f-]{36}$/);
    await expect(page.getByRole('heading', {name: 'Where each case stands'})).toBeVisible();
    await page.reload();                                                   // the address survives a refresh
    await expect(page.getByRole('heading', {name: 'Where each case stands'})).toBeVisible();
  });

  test('the valuations screen opens inside the new layout', async ({page}) => {
    await page.goto('/valuations');
    await expect(page.getByRole('heading', {name: 'Valuations', level: 1})).toBeVisible();
  });

  test('on a phone, the bottom bar replaces the sidebar', async ({page}, info) => {
    test.skip(info.project.name !== 'phone', 'phone layout only');
    await expect(page.getByRole('contentinfo', {name: 'Quick navigation'}).getByRole('link', {name: 'Valuations'})).toBeVisible();
    const inert = () => page.evaluate(() => document.querySelector('nav[aria-label="Main"]').inert);
    await expect.poll(inert).toBe(true);
    await page.getByRole('button', {name: 'Menu', exact: true}).click();
    await expect.poll(inert).toBe(false);
  });
});
