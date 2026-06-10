import { copyFile, mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const rootDir = fileURLToPath(new URL(".", import.meta.url));
const analystConsoleArtifacts = [
  {
    requestPath: "/data/review/review_queue.json",
    sourcePath: resolve(rootDir, "data/review/review_queue.json"),
    outputPath: resolve(rootDir, "dist/data/review/review_queue.json"),
  },
  {
    requestPath: "/data/review/council_analyses.json",
    sourcePath: resolve(rootDir, "data/review/council_analyses.json"),
    outputPath: resolve(rootDir, "dist/data/review/council_analyses.json"),
  },
  {
    requestPath: "/data/published/country_monitors.json",
    sourcePath: resolve(rootDir, "data/published/country_monitors.json"),
    outputPath: resolve(rootDir, "dist/data/published/country_monitors.json"),
  },
  {
    requestPath: "/config/actors/actor_registry.json",
    sourcePath: resolve(rootDir, "config/actors/actor_registry.json"),
    outputPath: resolve(rootDir, "dist/config/actors/actor_registry.json"),
  },
] as const;

function serveAnalystConsoleArtifacts() {
  return {
    name: "serve-analyst-console-artifacts",
    configureServer(server: {
      middlewares: {
        use: (
          handler: (
            req: { url?: string | undefined },
            res: {
              statusCode: number;
              setHeader: (name: string, value: string) => void;
              end: (body: string) => void;
            },
            next: () => void,
          ) => void,
        ) => void;
      };
    }) {
      server.middlewares.use((req, res, next) => {
        const requestPath = req.url ? new URL(req.url, "http://localhost").pathname : "";
        const artifact = analystConsoleArtifacts.find(
          (entry) => entry.requestPath === requestPath,
        );

        if (!artifact) {
          next();
          return;
        }

        void readFile(artifact.sourcePath, "utf8")
          .then((body) => {
            res.statusCode = 200;
            res.setHeader("Content-Type", "application/json; charset=utf-8");
            res.end(body);
          })
          .catch(() => {
            res.statusCode = 404;
            res.end("{}");
          });
      });
    },
    async writeBundle() {
      await Promise.all(
        analystConsoleArtifacts.map(async (artifact) => {
          await mkdir(dirname(artifact.outputPath), { recursive: true });
          await copyFile(artifact.sourcePath, artifact.outputPath);
        }),
      );
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), serveAnalystConsoleArtifacts()],
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
