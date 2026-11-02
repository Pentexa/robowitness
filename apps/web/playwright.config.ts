import { defineConfig } from "@playwright/test";

/**
 * Browser E2E against the LIVE local stack (backend :8000, worker, web :3000
 * must already be running — the same stack scripts/e2e_live_stack.py uses).
 * Start everything first, then: npm run test:e2e
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 30_000 },
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.RW_WEB_URL || "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
});
