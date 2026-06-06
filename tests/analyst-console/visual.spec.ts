import { expect, test } from "@playwright/test";

test("review desk visual baseline", async ({ page }) => {
  await page.goto("");
  await expect(page).toHaveScreenshot("analyst-console-review-desk.png", {
    fullPage: true,
  });
});
