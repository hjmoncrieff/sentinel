# SENTINEL Editorial System Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved `C2 — Editorial Oxide` system across the public dashboard so `Overview`, `Countries`, `OC`, `US-LATAM`, `Events`, and `About` read like one publication while preserving `Events` as the most operational tab.

**Architecture:** Keep the current static-site architecture intact and implement the redesign inside the existing public-dashboard shell: `index.html` for structure, `assets/css/dashboard.css` for visual tokens and layout rules, and `assets/js/dashboard.js` for country-profile/detail rendering. Add a dedicated public-dashboard Playwright harness so the palette, tab-level coherence, and event-accordion behavior are regression-tested alongside the existing analyst-console checks.

**Tech Stack:** Static HTML, vanilla JavaScript, shared CSS tokens, Playwright, existing Node scripts, Python `http.server`

---

## File Structure Map

### Existing files to modify
- `index.html` — public dashboard shell, tab markup, masthead, hero sections, `About` content, cache-busting asset version
- `assets/css/dashboard.css` — shared palette tokens, borders, surfaces, tab-level layout treatments, country/event/about styling
- `assets/js/dashboard.js` — country dossier rendering, section wrappers, accordion/detail hooks, minor semantic markup
- `package.json` — add a dedicated public-dashboard Playwright script
- `scripts/dev/playwright_smoke_dashboard.mjs` — align the existing smoke script with the redesigned selectors and operational checks
- `CHANGELOG.md` — record the implementation-plan milestone and later implementation work

### New files to create
- `playwright.dashboard.config.ts` — standalone Playwright config for the public dashboard
- `tests/public-dashboard/editorial-system.spec.ts` — regression coverage for palette, shared editorial surfaces, about methods section, and accordion behavior

### Existing files to read during implementation
- `docs/superpowers/specs/2026-06-06-sentinel-editorial-system-redesign-design.md`
- `tests/analyst-console/smoke.spec.ts`
- `playwright.config.ts`
- `scripts/dev/playwright_smoke_dashboard.mjs`

---

### Task 1: Add a public-dashboard regression harness and stable editorial hooks

**Files:**
- Create: `playwright.dashboard.config.ts`
- Create: `tests/public-dashboard/editorial-system.spec.ts`
- Modify: `package.json`
- Modify: `index.html`
- Modify: `assets/js/dashboard.js`

- [ ] **Step 1: Write the failing public-dashboard Playwright test**

```ts
// tests/public-dashboard/editorial-system.spec.ts
import { expect, test } from "@playwright/test";

test("country dossier and about surfaces expose stable editorial hooks", async ({ page }) => {
  await page.goto("/index.html");

  await expect(page.locator('[data-editorial-surface="overview-stage"]')).toBeVisible();
  await page.locator('.tab-btn[data-tab="profiles"]').click();
  await expect(page.locator('[data-editorial-surface="profiles-hero"]')).toBeVisible();

  await page.locator('.cp-btn[data-country="Brazil"]').click();
  await expect(page.locator('[data-editorial-surface="country-dossier"]')).toBeVisible();
  await expect(page.locator('[data-editorial-block="country-event-accordion"]')).toBeVisible();

  await page.locator('.tab-btn[data-tab="about"]').click();
  await expect(page.locator('[data-editorial-section="about-method"]')).toBeVisible();
});

test("country event accordion keeps only one event expanded", async ({ page }) => {
  await page.goto("/index.html");

  await page.locator('.tab-btn[data-tab="profiles"]').click();
  await page.locator('.cp-btn[data-country="Brazil"]').click();

  const items = page.locator('.cp2-event-item');
  await items.nth(1).locator('.cp2-event-row').click();
  await expect(page.locator('.cp2-event-item.is-open')).toHaveCount(1);

  await items.nth(2).locator('.cp2-event-row').click();
  await expect(page.locator('.cp2-event-item.is-open')).toHaveCount(1);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts`

Expected: FAIL because the dashboard Playwright config does not exist yet and the public markup does not expose the `data-editorial-*` hooks.

- [ ] **Step 3: Add the standalone Playwright config, npm script, and semantic hooks**

```ts
// playwright.dashboard.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/public-dashboard",
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "python3 -m http.server 8000 --bind 127.0.0.1",
    url: "http://127.0.0.1:8000/index.html",
    reuseExistingServer: true,
  },
});
```

```json
// package.json
{
  "scripts": {
    "dashboard:test:e2e": "playwright test -c playwright.dashboard.config.ts"
  }
}
```

```html
<!-- index.html -->
<div class="ov-page" data-editorial-surface="overview-stage">
  <section class="ov-section ov-fade">
    <div class="ov-kicker">Regional Monitor · Latin America &amp; the Caribbean</div>
    <div class="ov-title">SENTINEL.</div>
    <div class="ov-tagline">Civil-Military Relations · 25 Countries · Updated Nightly</div>
  </section>
</div>

<section class="editorial-tab-hero profiles-hero" data-editorial-surface="profiles-hero">
  <div class="profiles-hero-grid">
    <div class="profiles-hero-main">
      <div class="editorial-kicker">Regional Country Monitor</div>
      <div class="editorial-title">Country profiles for the hemisphere, read as a regional brief.</div>
    </div>
  </div>
</section>

<div class="about-section" data-editorial-section="about-method">
  <div class="about-h2">Editorial Method</div>
</div>
```

```js
// assets/js/dashboard.js
countryDiv.innerHTML = `<article class="cp2-article" data-editorial-surface="country-dossier">
  ${hdrHtml}
  ${heroHtml}
  ${briefingHtml}
  ${pressureHtml}
  <section class="cp2-live-field-shell">${pulseHtml + eventsHtml}</section>
</article>`;

const eventsHtml = `
  <div class="cp2-events-section" data-editorial-block="country-event-accordion">
    <div class="cp2-events-hdr">
      <span class="cp2-events-label">Field Reporting & Event Briefs</span>
      <span class="cp2-events-count">${cEvs.length} events · latest ${escapeHtml(latestEventLabel)}</span>
    </div>
    <div class="cp2-events-layout">
      <div class="cp2-events-list cp2-events-list-accordion">${evRows}</div>
    </div>
  </div>`;
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts`

Expected: PASS with `2 passed` once the public dashboard exposes the new hooks and the existing accordion behavior is addressable by the test.

- [ ] **Step 5: Commit**

```bash
git add playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts package.json index.html assets/js/dashboard.js
git commit -m "test: add public dashboard editorial regression harness"
```

---

### Task 2: Establish the shared C2 palette and public-site shell framing

**Files:**
- Modify: `assets/css/dashboard.css`
- Modify: `index.html`
- Modify: `tests/public-dashboard/editorial-system.spec.ts`

- [ ] **Step 1: Extend the dashboard test with palette and masthead assertions**

```ts
// tests/public-dashboard/editorial-system.spec.ts
test("site shell uses the editorial oxide palette and single-line masthead", async ({ page }) => {
  await page.goto("/index.html");

  await expect(page.getByText("Political Risk Desk")).toHaveCount(0);
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(244, 239, 230)");
  await expect(page.locator("header")).toHaveCSS("border-bottom-color", "rgb(202, 191, 170)");
  await expect(page.locator(".login-btn")).toHaveCSS("background-color", "rgb(38, 50, 33)");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts --grep "editorial oxide palette"`

Expected: FAIL because the current `:root` tokens, header border, and CTA color values still reflect the older palette.

- [ ] **Step 3: Replace the shared shell tokens and remove the broad gradient wash**

```css
/* assets/css/dashboard.css */
:root {
  --bg: #f4efe6;
  --surface: #f8f4ec;
  --surface-alt: #efe7da;
  --border: #cabfaa;
  --border2: #a9987c;
  --rule: #cabfaa;
  --text: #191712;
  --text-dim: #474137;
  --text-muted: #7b7366;
  --text-faint: #afa38f;
  --olive-dark: #263221;
  --olive-mid: #4b5c45;
  --olive-warm: #7a7b58;
  --amber: #a86131;
  --paper-line: rgba(90, 79, 61, 0.08);
  --paper-glow: rgba(168, 97, 49, 0.05);
  --shadow: 0 10px 24px rgba(41, 34, 25, 0.05);
  --shadow-md: 0 18px 38px rgba(41, 34, 25, 0.09);
  --shell-shadow: 0 14px 30px rgba(41, 34, 25, 0.06);
  --card-radius: 14px;
}

body {
  background: var(--bg);
  color: var(--text);
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: -1;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0)),
    repeating-linear-gradient(180deg, transparent 0 39px, var(--paper-line) 39px 40px);
}

header {
  background: rgba(244, 239, 230, 0.94);
  border-bottom: 1px solid rgba(202, 191, 170, 0.9);
}

.tab-btn::after {
  background: var(--amber);
}

.login-btn {
  background: var(--olive-dark);
  border-color: var(--olive-dark);
  color: #f4efe6;
}
```

```html
<!-- index.html -->
<link rel="stylesheet" href="assets/css/dashboard.css?v=20260606-editorial-system">
<script src="assets/js/dashboard.js?v=20260606-editorial-system" defer></script>
```

- [ ] **Step 4: Run the targeted test and dashboard syntax check**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts --grep "editorial oxide palette"`

Expected: PASS with the new body, header, and CTA colors.

Run: `node --check assets/js/dashboard.js`

Expected: PASS with no syntax errors.

- [ ] **Step 5: Commit**

```bash
git add assets/css/dashboard.css index.html tests/public-dashboard/editorial-system.spec.ts
git commit -m "feat: establish editorial oxide palette and shell"
```

---

### Task 3: Apply dossier-style surfaces to Countries, OC, and US-LATAM

**Files:**
- Modify: `index.html`
- Modify: `assets/css/dashboard.css`
- Modify: `assets/js/dashboard.js`
- Modify: `tests/public-dashboard/editorial-system.spec.ts`

- [ ] **Step 1: Write the failing cross-tab dossier-surface test**

```ts
// tests/public-dashboard/editorial-system.spec.ts
test("countries, OC, and US-LATAM share the dossier surface system", async ({ page }) => {
  await page.goto("/index.html");

  await expect(page.locator('[data-editorial-surface="overview-stage"]')).toBeVisible();
  await page.locator('.tab-btn[data-tab="profiles"]').click();
  await expect(page.locator('[data-editorial-surface="profiles-hero"]')).toHaveCSS("background-color", "rgb(248, 244, 236)");

  await page.locator('.tab-btn[data-tab="transnational"]').click();
  await expect(page.locator('[data-editorial-surface="oc-hero"]')).toBeVisible();
  await expect(page.locator('[data-editorial-surface="oc-frontlines"]')).toBeVisible();

  await page.locator('.tab-btn[data-tab="us"]').click();
  await expect(page.locator('[data-editorial-surface="us-hero"]')).toBeVisible();
  await expect(page.locator('[data-editorial-surface="us-brief-grid"]')).toBeVisible();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts --grep "share the dossier surface system"`

Expected: FAIL because the OC and US-LATAM sections do not yet expose the shared dossier-surface hooks or the revised paper-panel styling.

- [ ] **Step 3: Reframe the section markup and shared CSS around dossier panels**

```html
<!-- index.html -->
<section class="editorial-tab-hero profiles-hero editorial-surface editorial-surface-dossier" data-editorial-surface="profiles-hero">
  <div class="profiles-hero-grid">
    <div class="profiles-hero-main">
      <div class="editorial-kicker">Regional Country Monitor</div>
      <div class="editorial-title">Country profiles for the hemisphere, read as a regional brief.</div>
    </div>
  </div>
</section>
<section class="editorial-tab-hero field-hero oc-hero editorial-surface editorial-surface-dossier" data-editorial-surface="oc-hero">
  <div class="field-hero-grid">
    <div class="field-hero-main">
      <div class="editorial-kicker">Organized Crime Pressure Monitor</div>
      <div class="editorial-title">Criminal economies are reordering coercive power across the hemisphere.</div>
    </div>
  </div>
</section>
<div class="tab-focus-block oc-frontline-block editorial-surface editorial-surface-dossier" data-editorial-surface="oc-frontlines">
  <div class="tab-focus-head">
    <div>
      <div style="font-family:var(--mono);font-size:8px;letter-spacing:1.6px;text-transform:uppercase;color:var(--text-muted);margin-bottom:4px;">Frontline Cases</div>
      <div style="font-family:var(--serif);font-size:22px;color:var(--slate);line-height:1.08;">Organized crime becomes politically meaningful when it starts reordering who wields coercive power.</div>
    </div>
  </div>
</div>
<section class="editorial-tab-hero us-hero editorial-surface editorial-surface-dossier" data-editorial-surface="us-hero">
  <div class="field-hero-grid">
    <div class="field-hero-main">
      <div class="editorial-kicker">US-LatAm Security Monitor</div>
      <div class="editorial-title">Security cooperation, aid flows, and military presence across the hemisphere.</div>
    </div>
  </div>
</section>
<div class="tab-brief-grid us-brief-grid" data-editorial-surface="us-brief-grid">
  <div class="tab-brief-panel">
    <div class="sec-title">Priority Security Channels</div>
  </div>
</div>
```

```css
/* assets/css/dashboard.css */
.editorial-surface {
  background: var(--surface);
  border: 1px solid rgba(202, 191, 170, 0.95);
  border-radius: 14px;
  box-shadow: none;
}

.editorial-surface-dossier {
  position: relative;
  overflow: hidden;
}

.editorial-surface-dossier::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0)),
    linear-gradient(90deg, rgba(168, 97, 49, 0.06), transparent 24%);
}

.profiles-route-card,
.profiles-focus-card,
.oc-front-card,
.card,
.tab-brief-panel,
.context-panel,
.context-map-card {
  background: var(--surface);
  border: 1px solid rgba(202, 191, 170, 0.95);
  border-radius: 12px;
  box-shadow: none;
}

.profiles-route-card.active,
.profiles-focus-card:hover,
.oc-front-card:hover {
  border-color: rgba(168, 97, 49, 0.55);
  background: #fbf7f0;
}
```

```js
// assets/js/dashboard.js
countryDiv.innerHTML = `<article class="cp2-article editorial-surface editorial-surface-dossier" data-editorial-surface="country-dossier">
  ${hdrHtml}
  ${heroHtml}
  ${briefingHtml}
  ${pressureHtml}
  <section class="cp2-live-field-shell">${pulseHtml + eventsHtml}</section>
</article>`;
```

- [ ] **Step 4: Run the cross-tab test**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts --grep "share the dossier surface system"`

Expected: PASS with the three public sections exposing the same dossier-surface contract.

- [ ] **Step 5: Commit**

```bash
git add index.html assets/css/dashboard.css assets/js/dashboard.js tests/public-dashboard/editorial-system.spec.ts
git commit -m "feat: align country oc and us tabs to dossier surfaces"
```

---

### Task 4: Rework the Events tab as an operational editorial list and rewrite About as a methods note

**Files:**
- Modify: `index.html`
- Modify: `assets/css/dashboard.css`
- Modify: `assets/js/dashboard.js`
- Modify: `tests/public-dashboard/editorial-system.spec.ts`

- [ ] **Step 1: Write the failing Events and About regression checks**

```ts
// tests/public-dashboard/editorial-system.spec.ts
test("events remains operational while about reads like an editorial methods note", async ({ page }) => {
  await page.goto("/index.html");

  await page.locator('.tab-btn[data-tab="events"]').click();
  await expect(page.locator('[data-editorial-surface="events-ops-shell"]')).toBeVisible();
  await expect(page.locator('[data-editorial-surface="events-list"]')).toBeVisible();

  await page.locator('.tab-btn[data-tab="about"]').click();
  await expect(page.getByText("Editorial Method", { exact: true })).toBeVisible();
  await expect(page.locator('[data-editorial-section="about-method"]')).toContainText("regional brief");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts --grep "operational while about reads"`

Expected: FAIL because the Events shell does not yet expose the operational hooks and the About page does not yet contain the `Editorial Method` section heading.

- [ ] **Step 3: Tighten the Events shell and rewrite the About opening sections**

```html
<!-- index.html -->
<div class="events-layout editorial-surface editorial-surface-ops" data-editorial-surface="events-ops-shell">
  <div class="events-main-column">
    <div class="events-feed-shell" data-editorial-surface="events-list">
      <div id="event-list"></div>
    </div>
  </div>
</div>
<div class="about-section" data-editorial-section="about-method">
  <div class="about-h2">Editorial Method</div>
  <div class="about-body">
    <p>SENTINEL is built to read like a regional brief rather than a feed dump. The publication combines a live event layer, slower structural context, and country monitor interpretation so users can move from incident to pattern without leaving the same public surface.</p>
    <p>The visual system follows the same logic: overview establishes the frame, countries act as dossiers, OC and US-LATAM operate as thematic desks, and Events remains the fastest operational reading layer.</p>
  </div>
</div>
```

```css
/* assets/css/dashboard.css */
.editorial-surface-ops {
  background: #f7f2e9;
  border: 1px solid rgba(202, 191, 170, 0.95);
  border-radius: 14px;
}

.events-layout .ev-item,
.events-layout .events-sidebar-card,
.events-layout .events-filter-card {
  background: #fbf7f0;
  border: 1px solid rgba(202, 191, 170, 0.85);
  box-shadow: none;
}

.events-layout .ev-item:hover,
.events-layout .ev-item.is-active {
  border-color: rgba(168, 97, 49, 0.5);
}

.about-section {
  background: var(--surface);
  border: 1px solid rgba(202, 191, 170, 0.95);
  border-radius: 14px;
}
```

```js
// assets/js/dashboard.js
const eventsShell = document.querySelector(".events-layout");
if (eventsShell) {
  eventsShell.setAttribute("data-editorial-surface", "events-ops-shell");
}

const eventList = document.getElementById("event-list");
if (eventList) {
  eventList.setAttribute("data-editorial-surface", "events-list");
}
```

- [ ] **Step 4: Run the targeted test**

Run: `pnpm exec playwright test -c playwright.dashboard.config.ts tests/public-dashboard/editorial-system.spec.ts --grep "operational while about reads"`

Expected: PASS with the events shell discoverable as the operational surface and About exposing the new methods-note section.

- [ ] **Step 5: Commit**

```bash
git add index.html assets/css/dashboard.css assets/js/dashboard.js tests/public-dashboard/editorial-system.spec.ts
git commit -m "feat: align events operations shell and about methods note"
```

---

### Task 5: Final dashboard QA, smoke alignment, and release notes

**Files:**
- Modify: `scripts/dev/playwright_smoke_dashboard.mjs`
- Modify: `CHANGELOG.md`
- Modify: `tests/public-dashboard/editorial-system.spec.ts`

- [ ] **Step 1: Add a final end-to-end regression that covers the approved palette and section coherence**

```ts
// tests/public-dashboard/editorial-system.spec.ts
test("public dashboard reads as one publication across key tabs", async ({ page }) => {
  await page.goto("/index.html");

  await expect(page.locator('[data-editorial-surface="overview-stage"]')).toBeVisible();
  await page.locator('.tab-btn[data-tab="profiles"]').click();
  await expect(page.locator('[data-editorial-surface="profiles-hero"]')).toBeVisible();

  await page.locator('.tab-btn[data-tab="transnational"]').click();
  await expect(page.locator('[data-editorial-surface="oc-hero"]')).toBeVisible();

  await page.locator('.tab-btn[data-tab="us"]').click();
  await expect(page.locator('[data-editorial-surface="us-hero"]')).toBeVisible();

  await page.locator('.tab-btn[data-tab="about"]').click();
  await expect(page.locator('[data-editorial-section="about-method"]')).toBeVisible();
});
```

- [ ] **Step 2: Run the full dashboard suite to verify any remaining failures**

Run: `pnpm run dashboard:test:e2e`

Expected: FAIL only if any tab is still missing a shared editorial hook or a previous task left broken markup behind.

- [ ] **Step 3: Align the existing smoke script and update the changelog**

```js
// scripts/dev/playwright_smoke_dashboard.mjs
await page.goto(`${baseUrl}/index.html`, { waitUntil: "networkidle" });

await page.locator('.tab-btn[data-tab="profiles"]').click();
await page.locator('.cp-btn[data-country="Brazil"]').click();
await page.locator('[data-editorial-surface="country-dossier"]').waitFor({ timeout: 30000 });

await page.locator('.tab-btn[data-tab="about"]').click();
await page.locator('[data-editorial-section="about-method"]').waitFor({ timeout: 30000 });

const bodyColor = await page.locator("body").evaluate(el => getComputedStyle(el).backgroundColor);
if (bodyColor !== "rgb(244, 239, 230)") {
  throw new Error(`Unexpected editorial background color: ${bodyColor}`);
}
```

```md
<!-- CHANGELOG.md -->
### Editorial System Implementation Plan

Affected areas:
- `docs/superpowers/plans/2026-06-06-sentinel-editorial-system-redesign.md`

What changed:
- Added the execution plan for the approved public-site editorial redesign, including test coverage, palette work, dossier-surface rollout, operational Events treatment, and About rewrite sequencing.

Validation completed:
- Reviewed the plan against the approved design spec for coverage, naming consistency, and placeholder-free task detail.

Remaining risks / follow-up:
- The plan still needs to be executed task by task in the working tree.
```

- [ ] **Step 4: Run the full QA pass**

Run: `pnpm run dashboard:test:e2e`

Expected: PASS with the public Playwright suite green.

Run: `pnpm run smoke:dashboard`

Expected: PASS with `Dashboard smoke test passed`.

Run: `node --check assets/js/dashboard.js`

Expected: PASS with no syntax errors.

- [ ] **Step 5: Commit**

```bash
git add scripts/dev/playwright_smoke_dashboard.mjs CHANGELOG.md tests/public-dashboard/editorial-system.spec.ts
git commit -m "chore: finalize editorial dashboard QA coverage"
```
