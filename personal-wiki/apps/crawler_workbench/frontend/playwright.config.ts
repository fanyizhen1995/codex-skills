import { defineConfig } from "@playwright/test";

const port = Number(process.env.PW_WORKBENCH_E2E_FRONTEND_PORT ?? "15173");
const apiTarget = process.env.PW_WORKBENCH_E2E_BACKEND_URL ?? "http://127.0.0.1:18765";

export default defineConfig({
  testDir: "./tests",
  webServer: {
    command: `VITE_API_TARGET=${apiTarget} npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false
  },
  use: {
    baseURL: `http://127.0.0.1:${port}`
  }
});
