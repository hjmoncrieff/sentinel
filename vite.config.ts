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
    // Local preview convenience only: copy workspace JSON next to the build so
    // `vite preview` works offline. Skipped for deploys (CONSOLE_DEPLOY=1) and
    // tolerant of missing files, because data/review/* is private and gitignored.
    async writeBundle() {
      if (process.env.CONSOLE_DEPLOY === "1") return;
      await Promise.all(
        analystConsoleArtifacts.map(async (artifact) => {
          try {
            await mkdir(dirname(artifact.outputPath), { recursive: true });
            await copyFile(artifact.sourcePath, artifact.outputPath);
          } catch {
            console.warn(`[analyst-console] skipped missing artifact ${artifact.requestPath}`);
          }
        }),
      );
    },
  };
}

export default defineConfig({
  // GitHub Pages serves the site under /sentinel/; local dev and preview use "/".
  base: process.env.CONSOLE_BASE ?? "/",
  plugins: [react(), tailwindcss(), serveAnalystConsoleArtifacts()],
  resolve: {
    alias: {
      "@": resolve(rootDir, "apps/analyst-console/src"),
    },
  },
  build: {
    outDir: resolve(rootDir, "dist"),
    // Keep hashed bundles inside the console folder so they never mix with the
    // public dashboard's /assets when the two are deployed together.
    assetsDir: "apps/analyst-console/assets",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        analystConsole: resolve(rootDir, "apps/analyst-console/index.html"),
      },
    },
  },
});
