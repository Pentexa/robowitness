import { expect, test } from "@playwright/test";

// Paid SAM calls and explicit HTTP failure cases are mocked in this suite.
// Real SAM + conversion + worker coverage is scripts/sam_live_smoke.py and
// scripts/sam_browser_smoke.cjs; these do not run on the normal test command.
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

async function prepareDetectedPhoto(page: import("@playwright/test").Page) {
  await uploadCalibration(page);
  await page.route("**/api/scenarios/from-image/detect", (route) => route.fulfill({ json: {
    detection_id: "img-0123456789abcdef01234567", image_width: 1200, image_height: 800,
    model: "sam-3.1", provenance: "LIVE_META", detections: [
      { id: "red square:0", concept: "red square", confidence: 0.94, box: { left: 460, top: 260, right: 521, bottom: 321 } },
    ],
  } }));
  await page.locator("#input-sam-concepts").fill("red square");
  await page.locator("#btn-detect-photo").click();
  await expect(page.getByText("1 objects detected", { exact: false })).toBeVisible();
  await page.locator("#input-image-width").fill("12");
  await page.locator("#input-image-height").fill("8");
  await page.locator("#check-image-overhead").check();
}

test("audit: failed second detection cannot reuse previous objects", async ({ page }) => {
  await prepareDetectedPhoto(page);
  await page.route("**/api/scenarios/from-image/detect", (route) => route.fulfill({
    status: 502, json: { error: { message: "Second detection failed" } },
  }));
  await page.locator("#input-sam-concepts").fill("chair");
  await page.locator("#btn-detect-photo").click();
  await expect(page.locator("#image-scenario-panel").getByRole("alert")).toContainText("Second detection failed");
  await expect(page.locator("#image-detection-preview rect")).toHaveCount(0, { timeout: 3000 });
  await expect(page.locator("#btn-preview-image-scenario")).toHaveCount(0);
});

test("audit: switching tabs releases an open camera", async ({ page }) => {
  await page.locator("#btn-open-camera").click();
  const video = page.getByLabel("Camera preview", { exact: true });
  await expect(video).toBeVisible();
  await expect.poll(() => video.evaluate((element) => (element as HTMLVideoElement).videoWidth)).toBeGreaterThan(0);
  await page.evaluate(() => {
    (window as Window & { savedCamera?: MediaStream }).savedCamera = document.querySelector("video")!.srcObject as MediaStream;
  });
  await page.getByRole("tab", { name: "Report Card" }).click();
  await expect.poll(() => page.evaluate(() => (window as Window & { savedCamera?: MediaStream }).savedCamera!.getTracks().map((t) => t.readyState)), { timeout: 3000 }).toEqual(["ended"]);
});

test("audit: photo clicks map correctly in the laptop layout", async ({ page }) => {
  await page.setViewportSize({ width: 1000, height: 900 });
  await prepareDetectedPhoto(page);
  const photo = page.locator("#image-detection-preview");
  await photo.scrollIntoViewIfNeeded();
  const point = await photo.evaluate((element) => {
    const svg = element as SVGSVGElement;
    const pixel = new DOMPoint(200, 350).matrixTransform(svg.getScreenCTM()!);
    return { x: pixel.x, y: pixel.y };
  });
  await page.mouse.click(point.x, point.y);
  await expect(page.locator("#input-image-start-x")).toHaveValue("20", { timeout: 3000 });
  await expect(page.locator("#input-image-start-y")).toHaveValue("50");
});

test("audit: save and run reports a rejected simulation request", async ({ page }) => {
  await prepareDetectedPhoto(page);
  const reference = (await (await page.request.get("http://127.0.0.1:8000/api/scenarios/reference")).json())[0];
  await page.route("**/api/scenarios/from-image/scenario", (route) => route.fulfill({ json: {
    scenario: reference, name: "HTTP failure fixture", detection_id: "img-0123456789abcdef01234567",
    provenance: "LIVE_META", model: "sam-3.1", saved: route.request().postDataJSON().save, warnings: [],
  } }));
  await page.route("**/api/runs", (route) => route.fulfill({
    status: 503, json: { error: { message: "Simulation queue unavailable" } },
  }));
  await page.locator("#btn-preview-image-scenario").click();
  await expect(page.locator("#btn-run-image-scenario")).toBeVisible();
  await page.locator("#btn-run-image-scenario").click();
  await expect(page.locator("#image-scenario-panel").getByRole("alert")).toContainText("simulation", { timeout: 3000 });
});

test("audit: a failed history refresh cannot block the run request", async ({ page }) => {
  await prepareDetectedPhoto(page);
  const reference = (await (await page.request.get("http://127.0.0.1:8000/api/scenarios/reference")).json())[0];
  await page.route("**/api/scenarios/from-image/scenario", (route) => route.fulfill({ json: {
    scenario: reference, name: "History failure fixture", detection_id: "img-0123456789abcdef01234567",
    provenance: "LIVE_META", model: "sam-3.1", saved: route.request().postDataJSON().save, warnings: [],
  } }));
  await page.route("**/api/scenarios/from-image/saved", (route) => route.fulfill({ status: 503, json: {} }));
  let runRequests = 0;
  await page.route("**/api/runs", (route) => {
    runRequests += 1;
    return route.fulfill({ status: 503, json: { error: { message: "Queue failure fixture" } } });
  });
  await page.locator("#btn-preview-image-scenario").click();
  await expect(page.locator("#btn-run-image-scenario")).toBeVisible();
  await page.locator("#btn-run-image-scenario").click();
  await expect.poll(() => runRequests).toBe(1);
  await expect(page.locator("#select-saved-image-scenario option").filter({ hasText: "History failure fixture" })).toBeAttached();
});

test("audit: a failed worker job is visible to the user", async ({ page }) => {
  await page.route("**/api/runs", (route) => route.fulfill({ status: 202, json: {
    job_id: "job-audit-failed", result_id: "run-audit-failed", status: "queued",
  } }));
  await page.route("**/api/jobs/job-audit-failed", (route) => route.fulfill({ json: {
    status: "failed", error_code: "AUDIT_WORKER_FAILURE",
  } }));
  await expect(page.locator("#btn-run-baseline")).toBeEnabled();
  await page.locator("#btn-run-baseline").click();
  await expect(page.locator("#run-error")).toContainText("simulation job failed");
  await expect(page.locator("#btn-run-baseline")).toBeEnabled();
});
