import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(rootDir, "apps/analyst-console/src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./apps/analyst-console/src/test/setup.ts"],
    exclude: ["tests/**", "node_modules/**", "dist/**"],
  },
});
