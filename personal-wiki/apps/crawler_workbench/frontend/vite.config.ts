import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_API_TARGET ?? "http://localhost:8765";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ["spark-8c85.tail04bc15.ts.net"],
    proxy: {
      "/api": apiTarget
    }
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"]
  }
});
