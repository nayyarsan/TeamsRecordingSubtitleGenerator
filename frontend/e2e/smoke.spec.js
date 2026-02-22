import { test, expect } from '@playwright/test';

const MOCK_VIDEOS = [
  { id: 'vid1', name: 'team-meeting.mp4', timestamp: '2026-02-21T10:00:00Z', speaker_count: 3 },
];
const MOCK_METADATA = { speakers: [{ id: 'SPEAKER_00', name: 'Alice' }] };
const MOCK_SUBTITLES = { subtitles: [{ start: 0, end: 5, speaker_id: 'SPEAKER_00', text: 'Hello world' }] };
const MOCK_FACES = { faces: [] };

/** Routes common to all dashboard tests */
async function mockDashboard(page, videos = []) {
  await page.route('**/api/videos', (r) => r.fulfill({ json: { videos } }));
  await page.route('**/api/ollama/status', (r) => r.fulfill({ json: { available: false } }));
  await page.route('**/api/ollama/models', (r) => r.fulfill({ json: { models: [] } }));
  await page.route('**/api/system/info', (r) => r.fulfill({ json: {} }));
}

/** Routes common to all workspace tests */
async function mockWorkspace(page) {
  await page.route('**/api/video/vid1/metadata', (r) => r.fulfill({ json: MOCK_METADATA }));
  await page.route('**/api/video/vid1/subtitles', (r) => r.fulfill({ json: MOCK_SUBTITLES }));
  await page.route('**/api/video/vid1/faces', (r) => r.fulfill({ json: MOCK_FACES }));
  await page.route('**/api/video/vid1/original', (r) => r.abort());
}

// ---------------------------------------------------------------------------
// Dashboard tests
// ---------------------------------------------------------------------------

test('dashboard - page loads with correct heading', async ({ page }) => {
  await mockDashboard(page);
  await page.goto('/');
  await expect(page.getByText('MediaProcessor Dashboard')).toBeVisible();
  await expect(page.locator('[data-testid="dropzone"]')).toBeVisible();
});

test('dashboard - shows video cards from API', async ({ page }) => {
  await mockDashboard(page, MOCK_VIDEOS);
  await page.goto('/');
  await expect(page.locator('[data-testid="video-card"]')).toHaveCount(1);
  await expect(page.getByText('team-meeting.mp4')).toBeVisible();
});

test('dashboard - pipeline config fields are present', async ({ page }) => {
  await mockDashboard(page);
  await page.goto('/');
  await expect(page.getByText('Pipeline Config')).toBeVisible();
  await expect(page.getByLabel('ASR Model')).toBeVisible();
  await expect(page.getByLabel('Max Speakers')).toBeVisible();
  await expect(page.getByText('Start Processing')).toBeVisible();
});

test('dashboard - start processing button disabled without file', async ({ page }) => {
  await mockDashboard(page);
  await page.goto('/');
  await expect(page.getByText('Upload a file first')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Workspace tests
// ---------------------------------------------------------------------------

test('workspace - loads and shows header elements', async ({ page }) => {
  await mockWorkspace(page);
  await page.goto('/workspace/vid1');
  await expect(page.getByText('Export')).toBeVisible();
  await expect(page.getByText('File')).toBeVisible();
  await expect(page.locator('[data-testid="tab-timeline"]')).toBeVisible();
  await expect(page.locator('[data-testid="tab-speakers"]')).toBeVisible();
});

test('workspace - switching tabs updates active state', async ({ page }) => {
  await mockWorkspace(page);
  await page.goto('/workspace/vid1');
  await page.locator('[data-testid="tab-speakers"]').click();
  await expect(page.locator('[data-testid="tab-speakers"]')).toHaveClass(/text-primary/);
});

test('workspace - export modal opens and closes', async ({ page }) => {
  await mockWorkspace(page);
  await page.goto('/workspace/vid1');
  await page.getByText('Export').click();
  await expect(page.locator('[data-testid="export-modal"]')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-testid="export-modal"]')).not.toBeVisible();
});

test('workspace - face overlay toggle changes button text', async ({ page }) => {
  await mockWorkspace(page);
  await page.goto('/workspace/vid1');
  const toggle = page.locator('[data-testid="face-toggle"]');
  const initialText = await toggle.innerText();
  await toggle.click();
  const updatedText = await toggle.innerText();
  expect(updatedText).not.toBe(initialText);
});
