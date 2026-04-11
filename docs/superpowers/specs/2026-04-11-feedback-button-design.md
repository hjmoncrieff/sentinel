# Feedback Button — Design Spec
**Date:** 2026-04-11  
**Status:** Approved

---

## Overview

Add a persistent feedback button (fixed, bottom-right) to the SENTINEL dashboard. Opens a corner slide-up panel where users can submit categorized tips, corrections, and source suggestions. Submissions go to Formspree; the structured subject line makes the Formspree inbox a ready-made triage queue for the planned daily digest.

---

## Trigger & Placement

- Fixed position: `bottom: 24px; right: 24px`
- Visible on **all tabs** at all times (z-index above content, below modals)
- Button label: `● Suggest` in DM Mono, SENTINEL slate background, gold dot accent
- Button style matches existing SENTINEL mono-button aesthetic (no border-radius > 2px, no drop shadows beyond subtle)

---

## Panel

- Slides up above the button on click (`transform: translateY` + `opacity` transition, ~150ms)
- Width: `300px`; anchored to bottom-right
- Closes on: ✕ button click, click outside the panel, `Escape` key
- Does **not** dim or disrupt the dashboard behind it

### Fields (in order)

| # | Field | Type | Required |
|---|-------|------|----------|
| 1 | Category | `<select>` | Yes |
| 2 | Country | `<select>` | No (defaults to blank) |
| 3 | Message | `<textarea>` | Yes |
| 4 | Email | `<input type="email">` | No |

**Category options:**
- Missed event
- Wrong classification
- Source suggestion
- Country profile correction
- Research tip
- Other

**Country options:** All 25 SENTINEL-monitored countries (alphabetical) + "Regional / General" as first non-blank option.

---

## Submission

- **Method:** `fetch()` POST to Formspree endpoint (`Content-Type: application/json`)
- **Payload fields:**
  - `email` — user-supplied; key excluded from payload entirely if field is empty
  - `category` — selected category label (always present)
  - `country` — selected country; key excluded from payload entirely if no country selected
  - `message` — textarea content (always present)
  - `_subject` — auto-constructed: `SENTINEL Feedback — {category}` (e.g. `SENTINEL Feedback — Missed event`)
- **Endpoint:** `const FORMSPREE_ENDPOINT = 'https://formspree.io/f/REPLACE_ME'` at top of JS block, with comment linking to formspree.io setup

### Success state
- Panel body replaced with: `"Sent. Thank you."` in DM Mono
- Auto-closes after 2 seconds
- Form resets on next open

### Error state
- Inline error message below the send button: `"Something went wrong — try again."`
- Form stays open, user can retry

---

## Digest integration (future)

Formspree stores all submissions and can forward them by email. The `_subject` field pre-sorts by category in any email client. When the daily digest script is built, it can pull from the Formspree submissions API (requires Formspree API key in `.env`) to append feedback to the digest alongside high-salience events.

---

## Files changed

- `index.html` — all changes self-contained:
  - CSS: `.fb-btn`, `.fb-panel`, `.fb-panel.open`, `.fb-field`, `.fb-select`, `.fb-textarea`, `.fb-send`, `.fb-success`, `.fb-error`
  - HTML: button + panel added before closing `</body>`
  - JS: `toggleFeedback()`, `submitFeedback(e)`, outside-click + Escape listeners

No new files. No external dependencies beyond Formspree endpoint.

---

## Out of scope

- Formspree account creation (user action required before deploy)
- Daily digest script modifications (separate feature)
- Stats bar on Overview tab (separate feature)
- Country CMR radar card (separate feature)
