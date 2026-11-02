import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#select-library-scenario")).toBeVisible();
});

test("library has grouped scenarios incl. crowd, badge counts obstacles", async ({ page }) => {
  await expect(page.locator('#select-library-scenario optgroup[label*="Kalabalık"]')).toHaveCount(1);
  await expect(page.locator('#select-library-scenario optgroup[label*="Ultra"]')).toHaveCount(1);

  await page.selectOption("#select-library-scenario", "RW-CROWD-004");
  await expect(page.locator(".rw-badge").filter({ hasText: "5 ENGEL" })).toBeVisible();
});

test("baseline crashes in the market crowd (measured verdict shown)", async ({ page }) => {
  await page.selectOption("#select-library-scenario", "RW-CROWD-004");
  await expect(page.locator(".rw-badge").filter({ hasText: "5 ENGEL" })).toBeVisible();
  await page.click("#btn-run-baseline");
  await expect(
    page.locator(".rw-verdict-value").filter({ hasText: "KAZA OLDU" }).first()
  ).toBeVisible({
    timeout: 180_000,
  });
  // Only a FAIL advances to the investigation step.
  await expect(page.locator(".rw-tab.is-active")).toContainText("İncele");
});

test("clean corridor passes and does NOT advance to investigation", async ({ page }) => {
  await page.selectOption("#select-library-scenario", "RW-LIB-009");
  await expect(page.locator(".rw-badge").filter({ hasText: "0 ENGEL" })).toBeVisible();
  await page.click("#btn-run-baseline");
  await expect(
    page.locator(".rw-verdict-value").filter({ hasText: "KAZASIZ TAMAMLANDI" }).first()
  ).toBeVisible({ timeout: 180_000 });
  await expect(page.locator(".rw-tab.is-active")).toContainText("Test");
});

test("meta ai branding is visible in chrome and status bar", async ({ page }) => {
  await expect(page.locator("text=Meta AI").first()).toBeVisible();
  await expect(page.locator("#btn-generate-ai")).toContainText("Meta AI");
});

test("karne tab renders robot, profile and battery controls", async ({ page }) => {
  await page.getByRole("tab", { name: "Karne" }).click();
  await expect(page.locator("#select-battery-robot")).toBeVisible();
  await expect(page.locator("#btn-run-battery")).toBeVisible();
  await expect(page.locator("#select-battery-profile")).toBeVisible();
});

test("admin tab renders enterprise controls", async ({ page }) => {
  await page.getByRole("tab", { name: "Yönetim" }).click();
  await expect(page.locator("text=Sistem Durumu")).toBeVisible();
  await expect(page.locator("#btn-admin-backup")).toBeVisible();
  await expect(page.locator("#btn-create-api-key")).toBeVisible();
});
