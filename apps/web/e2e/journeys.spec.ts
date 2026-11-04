import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#select-library-scenario")).toBeVisible();
});

test("library has grouped scenarios incl. crowd, badge counts obstacles", async ({ page }) => {
  await expect(page.locator('#select-library-scenario optgroup[label*="Crowd"]')).toHaveCount(1);
  await expect(page.locator('#select-library-scenario optgroup[label*="Ultra"]')).toHaveCount(1);

  await page.selectOption("#select-library-scenario", "RW-CROWD-004");
  await expect(page.locator(".rw-badge").filter({ hasText: "5 OBSTACLES" })).toBeVisible();
});

test("baseline crashes in the market crowd (measured verdict shown)", async ({ page }) => {
  await page.selectOption("#select-library-scenario", "RW-CROWD-004");
  await expect(page.locator(".rw-badge").filter({ hasText: "5 OBSTACLES" })).toBeVisible();
  await page.click("#btn-run-baseline");
  await expect(
    page.locator(".rw-verdict-value").filter({ hasText: "CRASH" }).first()
  ).toBeVisible({
    timeout: 180_000,
  });
  // Only a FAIL advances to the inspection step.
  await expect(page.locator(".rw-tab.is-active")).toContainText("Inspect");
});

test("clean corridor passes and does NOT advance to inspection", async ({ page }) => {
  await page.selectOption("#select-library-scenario", "RW-LIB-009");
  await expect(page.locator(".rw-badge").filter({ hasText: "0 OBSTACLES" })).toBeVisible();
  await page.click("#btn-run-baseline");
  await expect(
    page.locator(".rw-verdict-value").filter({ hasText: "COMPLETED WITHOUT A CRASH" }).first()
  ).toBeVisible({ timeout: 180_000 });
  await expect(page.locator(".rw-tab.is-active")).toContainText("Test");
});

test("meta ai branding is visible in chrome and status bar", async ({ page }) => {
  await expect(page.locator("text=Meta AI").first()).toBeVisible();
  await expect(page.locator("#btn-generate-ai")).toContainText("Meta AI");
});

test("language switcher flips the UI to Turkish and back", async ({ page }) => {
  await page.click("#btn-lang-tr");
  await expect(page.locator("text=Test Alanı").first()).toBeVisible();
  await page.click("#btn-lang-en");
  await expect(page.locator("text=Test Area").first()).toBeVisible();
});

test("report card tab renders robot, profile and battery controls", async ({ page }) => {
  await page.getByRole("tab", { name: "Report Card" }).click();
  await expect(page.locator("#select-battery-robot")).toBeVisible();
  await expect(page.locator("#btn-run-battery")).toBeVisible();
  await expect(page.locator("#select-battery-profile")).toBeVisible();
});

test("admin tab renders enterprise controls", async ({ page }) => {
  await page.getByRole("tab", { name: "Admin" }).click();
  await expect(page.locator("text=System Status")).toBeVisible();
  await expect(page.locator("#btn-admin-backup")).toBeVisible();
  await expect(page.locator("#btn-create-api-key")).toBeVisible();
});

test("voice button is honest about speech support", async ({ page }) => {
  const button = page.getByRole("button", { name: /Describe the Failure/ });
  await expect(button).toBeVisible();
  const supported = await page.evaluate(() => {
    const w = window as unknown as Record<string, unknown>;
    return Boolean(w.SpeechRecognition ?? w.webkitSpeechRecognition);
  });
  if (!supported) {
    // No fabricated listening: the UI must say speech is unavailable here.
    await expect(page.getByText(/does not support speech recognition/)).toBeVisible();
  }
});

test("pixel proof tab is honest without a verification", async ({ page }) => {
  await page.getByRole("tab", { name: "Pixel Proof" }).click();
  await expect(page.getByText(/needs a completed verification/)).toBeVisible();
  await expect(page.getByText(/not a sixth gate/)).toBeVisible();
});

test("english UI contains no Turkish characters (i18n leak guard)", async ({ page }) => {
  // textContent (not innerText) also covers hidden tabs, so every panel is scanned.
  const text = await page.locator("body").evaluate((el) => el.textContent ?? "");
  expect(text).not.toMatch(/[ğĞşŞıİçÇöÖüÜ]/);
});
