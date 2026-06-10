#!/usr/bin/env node

import { spawn } from "node:child_process";
import process from "node:process";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "playwright";

const host = process.env.HOST || "127.0.0.1";
const editorialPaper = "rgb(244, 239, 230)";
const ignoredConsoleErrors = [
  "Failed to create chart: can't acquire context from the given item",
];
let serverExited = false;
let serverStartError = "";

async function startServer(preferredPort) {
  const candidates = [preferredPort, 8000, 8001, 8002, 4173, 4321];

  for (const candidate of candidates) {
    serverExited = false;
    serverStartError = "";

    const server = spawn("python3", ["-m", "http.server", String(candidate), "--bind", host], {
      cwd: process.cwd(),
      stdio: ["ignore", "pipe", "pipe"],
    });

    server.on("exit", () => {
      serverExited = true;
    });

    server.stderr.on("data", chunk => {
      serverStartError += chunk.toString();
    });

    await delay(300);

    if (!serverExited) {
      return { server, port: candidate };
    }
  }

  throw new Error(`Unable to start a static server on any expected local port.\n${serverStartError.trim()}`);
}

async function waitForServer(url, attempts = 40) {
  for (let i = 0; i < attempts; i += 1) {
    if (serverExited) {
      const suffix = serverStartError ? `\n${serverStartError.trim()}` : "";
      throw new Error(`Static server exited before Playwright could connect.${suffix}`);
    }
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (res.ok) return;
    } catch {
      // Keep polling until the static server is reachable.
    }
    await delay(250);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function main() {
  const preferredPort = Number(process.env.PORT || 8000);
  const { server, port } = await startServer(preferredPort);
  const baseUrl = `http://${host}:${port}`;

  try {
    await waitForServer(`${baseUrl}/index.html`);

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    const consoleErrors = [];

    page.on("console", message => {
      if (message.type() === "error") {
        consoleErrors.push(message.text());
      }
    });

    page.on("pageerror", error => {
      consoleErrors.push(error.message);
    });

    await page.goto(`${baseUrl}/index.html`, { waitUntil: "networkidle" });
    await page.locator('[data-editorial-surface="overview-stage"]').waitFor({ timeout: 30000 });

    await page.locator('.tab-btn[data-tab="profiles"]').click();
    await page.locator('.cp-btn[data-country="Brazil"]').click();
    await page.locator('[data-editorial-surface="country-dossier"]').waitFor({ timeout: 30000 });

    await page.locator('.tab-btn[data-tab="about"]').click();
    await page.locator('[data-editorial-section="about-method"]').waitFor({ timeout: 30000 });

    const bodyBackground = await page.locator("body").evaluate(element =>
      window.getComputedStyle(element).backgroundColor,
    );
    if (bodyBackground !== editorialPaper) {
      throw new Error(`Unexpected body background color: ${bodyBackground}`);
    }

    const actionableErrors = consoleErrors.filter(message =>
      !ignoredConsoleErrors.some(ignored => message.includes(ignored)),
    );

    if (actionableErrors.length) {
      throw new Error(`Browser console errors detected:\n${consoleErrors.join("\n")}`);
    }

    console.log(`Dashboard smoke test passed at ${baseUrl}`);
    await browser.close();
  } finally {
    server.kill("SIGTERM");
    await delay(250);
  }
}

main().catch(error => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
