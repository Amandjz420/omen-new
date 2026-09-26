import {expect, test} from '@playwright/test';

// The signed-in layout, with the backend replaced by sample responses, so it runs on
// every change with no login and no real data. Screenshots go to test-results/.
const LEAD = '3f1c2a9e-5b7d-4e21-9c3a-6d8e0f1a2b3c';
const SAMPLE = {
  'session/': {username: 'sanjeev', staff: true},
  'valuations/?status=not_started': {total: 42}, 'valuations/?status=Pending': {total: 17}, 'valuations/?status=Revert': {total: 5},
  'verifications/': {counts: {legal: 6, technical: 9, social: 3, general: 4}},
  'bank-reports/': {counts: {pending: 11}}, 'approvals/': {counts: {pending: 8}},
  'invoices/?state=unpaid': {counts: {unpaid: 249}}, 'invoices/': {counts: {to_invoice: 14}},
  'receipts/': {counts: {to_check: 26, to_verify: 22}}, 'dispatch/awaiting/': {total: 65},
  [`leads/${LEAD}/stages/`]: {cases: [{id: 'c1', borrower: 'M/s Bhola Warehouse', service: 'Valuation', subtype: 'Land and building', report_number: 'R-0123178710',
    stages: [['Intake', 'done'], ['Work order', 'done', 'O-0123150042'], ['Valuation', 'done', 'Submitted'], ['Verification', 'done'], ['Bank report', 'done'],
             ['Approval', 'done'], ['Invoice', 'done', 'I-0126050311'], ['Payment', 'current', '₹4,150.00 outstanding'], ['Dispatch', 'waiting']]
      .map(([label, state, detail = '']) => ({key: label, label, state, detail}))}]},
  [`leads/${LEAD}/`]: {id: LEAD, number: 'L-0123135269', status_label: 'In process', date_basis: 'actual_intake', received_date: '2026-01-23',
    office: {name: 'State Bank of India', branch: 'Main Branch Itarsi'}, contact: {name: 'R. K. Sharma', phone: '9826012345'}, issues: [], notes: [], cases: []},
  'leads/': {count: 1, results: [{id: LEAD, number: 'L-0123135269', source_id: '35269', office: {name: 'State Bank of India', branch: 'Main Branch Itarsi'},
    received_date: '2026-01-23', status_label: 'In process'}]},
};

test.beforeEach(async ({page}) => {
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api\//, '') + new URL(route.request().url()).search;
    const key = Object.keys(SAMPLE).sort((a, b) => b.length - a.length).find(k => path.startsWith(k.split('?')[0]) && (!k.includes('?') || path.includes(k.split('?')[1])));
    route.fulfill({status: key ? 200 : 404, contentType: 'application/json', body: JSON.stringify(key ? SAMPLE[key] : {error: 'Not found'})});
  });
});

test('my work: the stage track and the queues', async ({page}, info) => {
  await page.goto('/');
  const track = page.getByRole('list', {name: 'Work waiting at each stage'});
  await expect(track.getByRole('listitem')).toHaveCount(7);
  await expect(track.getByText('64')).toBeVisible();                     // valuation: 42 + 17 + 5
  await expect(page.getByRole('link', {name: 'Receipts to check or verify'})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await page.screenshot({path: `test-results/shots/my-work-${info.project.name}.png`, fullPage: true});
});

test('a lead page: where each case stands', async ({page}, info) => {
  await page.goto(`/leads/${LEAD}`);
  await expect(page.getByRole('heading', {name: 'L-0123135269'})).toBeVisible();
  const stages = page.getByRole('list', {name: 'Stages for M/s Bhola Warehouse'});
  await expect(stages.locator('[aria-current="step"]')).toContainText('Payment');
  await page.screenshot({path: `test-results/shots/lead-${info.project.name}.png`, fullPage: true});
});

test('navigation: sidebar on desktop, bottom bar and menu on a phone', async ({page}, info) => {
  await page.goto('/');
  const main = page.getByRole('navigation', {name: 'Main'});
  // Closed, the phone menu sits off-screen and is inert: out of sight, out of the tab
  // order, and not read by screen readers. Playwright counts an off-screen element as
  // visible, so the test checks position and inertness directly.
  const closed = () => page.evaluate(() => {const n = document.querySelector('nav[aria-label="Main"]');
    return n.getBoundingClientRect().right <= 0 && n.inert;});
  if (info.project.name === 'phone') {
    await expect.poll(closed).toBe(true);
    await page.getByRole('button', {name: 'Menu', exact: true}).click();
    await expect.poll(closed).toBe(false);
    await expect(main.getByRole('link', {name: 'Receipts'})).toBeVisible();
    await main.getByRole('link', {name: 'Leads', exact: true}).click();
    await expect(page).toHaveURL(/\/leads$/);
    await expect.poll(closed).toBe(true);                                // choosing a page closes the menu
  } else {
    await main.getByRole('link', {name: 'Leads', exact: true}).click();
    await expect(page).toHaveURL(/\/leads$/);
    await expect(page.getByRole('link', {name: 'L-0123135269'})).toBeVisible();
  }
  await page.goBack();                                                    // the back button works
  await expect(page.getByRole('heading', {name: 'My work'})).toBeVisible();
});
