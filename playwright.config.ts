import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/analyst-console",
  use: {
    baseURL: "http://127.0.0.1:4173/apps/analyst-console/",
    trace: "on-first-retry",
  },
  webServer: {
    command: "pnpm exec vite --config vite.config.ts --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173/apps/analyst-console/",
    reuseExistingServer: true,
  },
});
