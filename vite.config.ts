import { copyFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

function copyAnalystConsoleReviewSnapshot() {
  return {
    name: "copy-analyst-console-review-snapshot",
    async writeBundle() {
      const outputDir = resolve(rootDir, "dist/data/review");
      await mkdir(outputDir, { recursive: true });
      await copyFile(
        resolve(rootDir, "data/review/review_queue.json"),
        resolve(outputDir, "review_queue.json"),
      );
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), copyAnalystConsoleReviewSnapshot()],
  resolve: {
    alias: {
      "@": resolve(rootDir, "apps/analyst-console/src"),
    },
  },
  build: {
    outDir: resolve(rootDir, "dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        analystConsole: resolve(rootDir, "apps/analyst-console/index.html"),
      },
    },
  },
});
