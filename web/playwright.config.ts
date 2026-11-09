import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const E2E_DATA_DIR = join(tmpdir(), "nexusrag-e2e-data");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  timeout: 180_000,
  expect: { timeout: 60_000 },
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://localhost:3000",
    // Locally use the installed Chrome. CI installs Playwright's Chromium instead.
    channel: process.env.CI ? undefined : "chrome",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "bun e2e/fake-provider.ts",
      url: "http://127.0.0.1:4010/__requests",
      reuseExistingServer: false,
    },
    {
      command: "uv run python -m nexusrag",
      cwd: "../api",
      env: { NEXUSRAG_DATA_DIR: E2E_DATA_DIR },
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "bun run build && bun run start",
      url: "http://localhost:3000",
      reuseExistingServer: false,
      timeout: 300_000,
    },
  ],
});
