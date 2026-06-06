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
