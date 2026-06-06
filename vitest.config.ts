import { resolve } from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "apps/analyst-console/src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./apps/analyst-console/src/test/setup.ts"],
  },
});
