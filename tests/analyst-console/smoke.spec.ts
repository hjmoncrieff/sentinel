import { expect, test } from "@playwright/test";

test("analyst console loads the dark operations desk", async ({ page }) => {
  await page.goto("");

  await expect(
    page.getByRole("navigation", { name: /global workspace/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: /event brief/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: /review actions/i }),
  ).toBeVisible();
});

test("public country profile renders dossier-backed structural cards", async ({ page }) => {
  await page.goto("http://127.0.0.1:8000/index.html");

  await page.locator('.tab-btn[data-tab="profiles"]').click();
  await page.locator('.cp-btn[data-country="Brazil"]').click();

  await expect(page.getByText("Electoral Democracy")).toBeVisible();
  await expect(page.getByText("Military Spending / GDP")).toBeVisible();
});
