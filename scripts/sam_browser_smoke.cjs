/* Manual paid live SAM smoke through the actual browser UI, never the default test suite.
 * Input is a rendered overhead calibration image, not physical-world evidence.
 * Requires backend :8000, worker and web :3000 (or RW_WEB_URL).
 */
const { chromium, expect } = require("../apps/web/node_modules/@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

async function main() {
  const output = path.resolve(__dirname, "../artifacts/sam_smoke");
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(process.env.RW_WEB_URL || "http://127.0.0.1:3000");
    await page.locator("#image-scenario-panel summary").click();
    const photo = await page.evaluate(() => {
      const canvas = document.createElement("canvas");
      canvas.width = 1200; canvas.height = 800;
      const context = canvas.getContext("2d");
      context.fillStyle = "white"; context.fillRect(0, 0, 1200, 800);
      context.fillStyle = "red"; context.fillRect(460, 260, 61, 61); context.fillRect(700, 480, 61, 61);
      return canvas.toDataURL("image/png").split(",")[1];
    });
    await page.locator("#input-scenario-photo").setInputFiles({
      name: "overhead-calibration.png", mimeType: "image/png", buffer: Buffer.from(photo, "base64"),
    });
    await expect(page.locator("#image-detection-preview")).toBeVisible();
    await page.locator("#input-sam-concepts").fill("red square");
    const [detected] = await Promise.all([
      page.waitForResponse((r) => r.url().endsWith("/from-image/detect"), { timeout: 200_000 }),
      page.locator("#btn-detect-photo").click(),
    ]);
    expect(detected.status()).toBe(200);
    const detection = await detected.json();
    expect(detection.provenance).toBe("LIVE_META");
    expect(detection.model).toBe("sam-3.1");
    expect(detection.detections.length).toBe(2);
    await page.locator("#input-image-name").fill("SAM browser live calibration");
    await page.locator("#input-image-width").fill("12");
    await page.locator("#input-image-height").fill("8");
    await page.locator("#check-image-overhead").check();
    await page.locator("#btn-preview-image-scenario").click();
    await expect(page.locator("#image-scenario-result")).toBeVisible();
    await page.locator("#image-scenario-result").screenshot({ path: path.join(output, "live-browser-preview.png") });
    const [queued] = await Promise.all([
      page.waitForResponse((r) => r.url().endsWith("/api/runs") && r.request().method() === "POST"),
      page.locator("#btn-run-image-scenario").click(),
    ]);
    expect(queued.status()).toBe(202);
    const job = await queued.json();
    await expect(page.locator(".rw-verdict-value").filter({ hasText: "COMPLETED WITHOUT A CRASH" }).first()).toBeVisible({ timeout: 120_000 });
    const used = await page.evaluate(() => ({
      run_id: localStorage.getItem("rw_run_id"),
      scenario: document.querySelector(".rw-summary.mono")?.textContent,
    }));
    expect(used.run_id).toBe(job.result_id);
    expect(used.scenario).toContain("RW-IMG-");
    const measuredResponse = await page.request.get(`${new URL(queued.url()).origin}/api/runs/${job.result_id}`);
    expect(measuredResponse.ok()).toBe(true);
    const measured = await measuredResponse.json();
    expect(measured.oracle_status).toBe("PASS");
    await page.reload();
    await page.locator("#image-scenario-panel summary").click();
    await expect(page.locator("#select-saved-image-scenario option").filter({ hasText: "SAM browser live calibration" }).first()).toBeAttached();
    expect(errors).toEqual([]);
    const result = { source: "rendered_overhead_calibration", model: detection.model,
      detections: detection.detections.length, run_id: job.result_id,
      verdict: measured.oracle_status, metrics: measured.metrics,
      saved_reload: true, page_errors: errors };
    fs.writeFileSync(path.join(output, "live-browser-result.json"), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
  } finally { await browser.close(); }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
