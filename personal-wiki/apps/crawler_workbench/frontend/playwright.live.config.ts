import { defineConfig } from "@playwright/test";

const frontendPort = process.env.PW_WORKBENCH_E2E_FRONTEND_PORT ?? "5174";
const backendUrl = process.env.PW_WORKBENCH_E2E_BACKEND_URL ?? "http://127.0.0.1:18765";

const webServerEnv: Record<string, string> = {};
for (const [key, value] of Object.entries(process.env)) {
  if (value !== undefined) {
    webServerEnv[key] = value;
  }
}
webServerEnv.VITE_API_TARGET = backendUrl;

export default defineConfig({
  testDir: "./tests",
  testMatch: /source-subscriptions\.live\.spec\.ts/,
  timeout: 60_000,
  expect: {
    timeout: 15_000
  },
  reporter: [
    ["list"],
    [
      "html",
      {
        open: "never",
        outputFolder: process.env.PW_WORKBENCH_E2E_REPORT_DIR ?? "playwright-report/source-subscriptions-live"
      }
    ],
    [
      "json",
      {
        outputFile: process.env.PW_WORKBENCH_E2E_JSON_REPORT ?? "test-results/source-subscriptions-live.json"
      }
    ]
  ],
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort} --strictPort`,
    url: `http://127.0.0.1:${frontendPort}`,
    reuseExistingServer: false,
    env: webServerEnv
  },
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    screenshot: "only-on-failure",
    trace: "retain-on-failure"
  }
});
