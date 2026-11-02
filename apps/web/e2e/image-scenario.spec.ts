import { expect, test } from "@playwright/test";

// The normal suite mocks only the paid SAM HTTP boundary. Full live coverage
// is recorded separately by scripts/sam_live_smoke.py and the live UI smoke.
test.use({
  launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
  permissions: ["camera"],
});

async function uploadCalibration(page: import("@playwright/test").Page) {
  const data = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 1200; canvas.height = 800;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "white"; ctx.fillRect(0, 0, 1200, 800);
    ctx.fillStyle = "red"; ctx.fillRect(460, 260, 61, 61); ctx.fillRect(700, 480, 61, 61);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page.locator("#input-scenario-photo").setInputFiles({
    name: "overhead-calibration.png", mimeType: "image/png", buffer: Buffer.from(data, "base64"),
  });
  await expect(page.locator("#image-detection-preview")).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.locator("#image-scenario-panel summary").click();
});

test("photo detection requires explicit scale and overhead confirmation before preview", async ({ page }) => {
  await uploadCalibration(page);
  await page.route("**/api/scenarios/from-image/detect", async (route) => {
    const body = route.request().postDataJSON();
    expect(body.concepts).toEqual(["red square"]);
    expect(body.image_data_url).toMatch(/^data:image\/jpeg;base64,/);
    await route.fulfill({ json: {
      detection_id: "img-0123456789abcdef01234567", image_width: 1200, image_height: 800,
      model: "sam-3.1", provenance: "LIVE_META", detections: [
        { id: "red square:0", concept: "red square", confidence: 0.94, box: { left: 460, top: 260, right: 521, bottom: 321 } },
        { id: "red square:1", concept: "red square", confidence: 0.94, box: { left: 700, top: 480, right: 761, bottom: 541 } },
      ],
    } });
  });
  await page.locator("#input-sam-concepts").fill("red square");
  await page.locator("#btn-detect-photo").click();
  await expect(page.getByText("2 objects detected", { exact: false })).toBeVisible();
  await expect(page.locator("#image-detection-preview rect")).toHaveCount(2);
  await expect(page.locator("#btn-preview-image-scenario")).toBeDisabled();
  await page.locator("#input-image-width").fill("12");
  await page.locator("#input-image-height").fill("8");
  await expect(page.locator("#btn-preview-image-scenario")).toBeDisabled();
  await page.locator("#check-image-overhead").check();
  await expect(page.locator("#btn-preview-image-scenario")).toBeEnabled();
  await expect(page.locator("#btn-save-image-scenario")).toHaveCount(0);
});

test("SAM errors are visible and do not manufacture detections", async ({ page }) => {
  await uploadCalibration(page);
  await page.route("**/api/scenarios/from-image/detect", (route) => route.fulfill({
    status: 502, json: { error: { code: "SAM_PROVIDER_ERROR", message: "SAM unavailable in transport test" } },
  }));
  await page.locator("#btn-detect-photo").click();
  await expect(page.locator("#image-scenario-panel").getByRole("alert")).toContainText("SAM unavailable in transport test");
  await expect(page.locator("#btn-preview-image-scenario")).toHaveCount(0);
});

test("camera captures one still and releases the media track", async ({ page }) => {
  await page.locator("#btn-open-camera").click();
  const video = page.getByLabel("Camera preview", { exact: true });
  await expect(video).toBeVisible();
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).videoWidth)).toBeGreaterThan(0);
  await page.evaluate(() => {
    (window as Window & { savedCamera?: MediaStream }).savedCamera = document.querySelector("video")!.srcObject as MediaStream;
  });
  await page.locator("#btn-capture-photo").click();
  await expect(video).toHaveCount(0);
  await expect(page.locator("#image-detection-preview")).toBeVisible();
  expect(await page.evaluate(() => (window as Window & { savedCamera?: MediaStream }).savedCamera!.getTracks().map((t) => t.readyState))).toEqual(["ended"]);
});

test("camera permission failure offers photo upload", async ({ page }) => {
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException("Denied", "NotAllowedError"); };
  });
  await page.locator("#btn-open-camera").click();
  await expect(page.locator("#image-scenario-panel").getByRole("alert")).toContainText("Allow camera permission or upload a photo");
  await expect(page.locator("video")).toHaveCount(0);
});
