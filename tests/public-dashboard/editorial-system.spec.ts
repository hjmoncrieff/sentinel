import { expect, test, type Page } from "@playwright/test";

const editorialPaper = "rgb(244, 239, 230)";

async function openCountryProfileWithAtLeastEvents(page: Page, minimumEvents: number) {
  const countryButtons = page.locator('.cp-btn[data-country]');
  const countryCount = await countryButtons.count();

  for (let index = 0; index < countryCount; index += 1) {
    await countryButtons.nth(index).click();
    await expect(page.locator('[data-editorial-surface="country-dossier"]')).toBeVisible();

    if (await page.locator(".cp2-event-item").count() >= minimumEvents) {
      return;
    }
  }

  throw new Error(`Could not find a country profile with at least ${minimumEvents} live events.`);
}

async function expectEditorialPublicationSurface(page: Page, selector: string, tab?: string) {
  if (tab) {
    await page.locator(`.tab-btn[data-tab="${tab}"]`).click();
  }

  await expect(page.locator(selector)).toBeVisible();
  await expect(page.locator("body")).toHaveCSS("background-color", editorialPaper);
}

test("site shell uses the editorial oxide palette and single-line masthead", async ({ page }) => {
  await page.goto("/index.html");

  await expect(page.getByText("Political Risk Desk")).toHaveCount(0);
  await expect(page.locator("body")).toHaveCSS("background-color", editorialPaper);
  await expect(page.locator("header")).toHaveCSS("border-bottom-color", "rgba(202, 191, 170, 0.9)");
  await expect(page.locator(".login-btn")).toHaveCSS("background-color", "rgb(38, 50, 33)");
});

test("country dossier and about surfaces expose stable editorial hooks", async ({ page }) => {
  await page.goto("/index.html");

  await expect(page.locator('[data-editorial-surface="overview-stage"]')).toBeVisible();
  await page.locator('.tab-btn[data-tab="profiles"]').click();
  await expect(page.locator('[data-editorial-surface="profiles-hero"]')).toBeVisible();

  await page.locator('.cp-btn[data-country="Brazil"]').click();
  await expect(page.locator('[data-editorial-surface="country-dossier"]')).toBeVisible();
  await expect(page.locator('[data-editorial-block="country-event-accordion"]')).toBeVisible();

  await page.locator('.tab-btn[data-tab="about"]').click();
  await expect(page.locator('[data-editorial-section="about-method"]')).toBeVisible();
});

test("events tab restores the classic feed workspace while keeping the editorial palette", async ({ page }) => {
  await page.goto("/index.html");

  await page.locator('.tab-btn[data-tab="events"]').click();
  await expect(page.locator('[data-editorial-surface="events-list"]')).toBeVisible();
  await expect(page.locator('[data-editorial-surface="events-map"]')).toBeVisible();
  await expect(page.locator('[data-editorial-surface="events-detail"]')).toBeVisible();
  await expect(page.locator('.ev-item').first()).toBeVisible();

  await page.locator('.ev-item').first().click();
  await expect(page.locator('#detail .detail-country-name')).toBeVisible();
});

test("about tab keeps the editorial method treatment hooks", async ({ page }) => {
  await page.goto("/index.html");

  await page.locator('.tab-btn[data-tab="about"]').click();
  const aboutMethod = page.locator('[data-editorial-section="about-method"]');
  await expect(page.getByText("Editorial Method")).toBeVisible();
  await expect(aboutMethod).toBeVisible();
  await expect(aboutMethod.locator(".about-tagline")).toBeVisible();
  await expect(aboutMethod.locator(".editorial-stat-strip")).toBeVisible();
});

test("key public tabs read as one editorial publication", async ({ page }) => {
  await page.goto("/index.html");

  await expectEditorialPublicationSurface(page, '[data-editorial-surface="overview-stage"]');
  await expectEditorialPublicationSurface(page, '[data-editorial-surface="profiles-hero"]', "profiles");
  await expectEditorialPublicationSurface(page, '[data-editorial-surface="oc-hero"]', "transnational");
  await expectEditorialPublicationSurface(page, '[data-editorial-surface="us-hero"]', "us");
  await expectEditorialPublicationSurface(page, '[data-editorial-section="about-method"]', "about");
});

test("country event accordion keeps only one event expanded", async ({ page }) => {
  await page.goto("/index.html");

  await page.locator('.tab-btn[data-tab="profiles"]').click();
  await openCountryProfileWithAtLeastEvents(page, 2);

  const items = page.locator('.cp2-event-item');
  const itemCount = await items.count();
  expect(itemCount).toBeGreaterThanOrEqual(2);

  await items.first().locator('.cp2-event-row').click();
  await expect(page.locator('.cp2-event-item.is-open')).toHaveCount(1);
  await expect(items.first()).toHaveClass(/is-open/);

  await items.nth(1).locator('.cp2-event-row').click();
  await expect(page.locator('.cp2-event-item.is-open')).toHaveCount(1);
  await expect(items.first()).not.toHaveClass(/is-open/);
  await expect(items.nth(1)).toHaveClass(/is-open/);
});
