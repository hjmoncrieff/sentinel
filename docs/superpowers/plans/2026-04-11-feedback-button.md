# Feedback Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fixed bottom-right "Suggest" button to the SENTINEL dashboard that opens a corner slide-up panel for submitting categorized feedback to Formspree.

**Architecture:** All changes are self-contained in `index.html` — CSS added before the closing `</style>` tag (line 1344), HTML added before `</body>` (line 6274), and JS added before the closing `</script>` (line 6273). No new files, no dependencies beyond the existing page.

**Tech Stack:** Vanilla JS (`fetch` API), Formspree (external form endpoint), existing SENTINEL CSS variables and fonts (DM Mono, DM Sans).

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `index.html:1340-1344` | Modify | Add `.fb-*` CSS block before `</style>` |
| `index.html:6272-6274` | Modify | Add feedback HTML before `</body>` |
| `index.html:6268-6273` | Modify | Add feedback JS before `</script>` |

---

## Task 1: Add CSS for button and panel

**Files:**
- Modify: `index.html` — insert before `</style>` at line 1344

- [ ] **Step 1: Open `index.html` and locate the `</style>` tag at line 1344**

Find the exact line: `</style>` preceded by the last CSS rule in the file.

- [ ] **Step 2: Insert the following CSS block immediately before `</style>`**

```css
/* ── Feedback Button & Panel ──────────────────────────── */
.fb-btn {
  position: fixed; bottom: 24px; right: 24px; z-index: 900;
  display: flex; align-items: center; gap: 7px;
  background: var(--slate); color: #fffdf8;
  border: none; border-radius: 2px; padding: 9px 14px;
  font-family: var(--mono); font-size: 9px; letter-spacing: 1.2px;
  text-transform: uppercase; cursor: pointer;
  box-shadow: 0 2px 8px rgba(28,26,23,0.18); white-space: nowrap;
}
.fb-btn:hover { background: #2e2b26; }
.fb-btn-dot {
  width: 6px; height: 6px; background: var(--gold);
  border-radius: 50%; flex-shrink: 0;
}
.fb-panel {
  position: fixed; bottom: 68px; right: 24px; z-index: 900;
  width: 300px; background: var(--surface);
  border: 1px solid var(--border2); border-radius: 2px;
  box-shadow: 0 4px 20px rgba(28,26,23,0.14);
  padding: 18px; display: flex; flex-direction: column; gap: 10px;
  transform: translateY(12px); opacity: 0; pointer-events: none;
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.fb-panel.open { transform: translateY(0); opacity: 1; pointer-events: all; }
.fb-panel-title {
  font-family: var(--mono); font-size: 8.5px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-muted);
  border-bottom: 1px solid var(--rule); padding-bottom: 8px;
}
.fb-panel-sub { font-size: 12px; color: var(--text-secondary); line-height: 1.5; font-weight: 300; }
.fb-panel-close {
  position: absolute; top: 12px; right: 12px;
  background: none; border: none; cursor: pointer;
  font-family: var(--mono); font-size: 12px; color: var(--text-muted);
  padding: 2px 5px; line-height: 1;
}
.fb-field-label {
  font-family: var(--mono); font-size: 8px; letter-spacing: 1px;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;
}
.fb-select, .fb-input, .fb-textarea {
  width: 100%; box-sizing: border-box; background: var(--bg2);
  border: 1px solid var(--border2); border-radius: 2px;
  padding: 7px 10px; font-family: var(--sans); font-size: 12.5px;
  color: var(--text); outline: none;
}
.fb-select:focus, .fb-input:focus, .fb-textarea:focus { border-color: var(--border3); }
.fb-textarea { resize: none; height: 72px; }
.fb-send {
  align-self: flex-end; background: var(--slate); color: #fffdf8;
  border: none; border-radius: 2px; padding: 7px 16px;
  font-family: var(--mono); font-size: 8.5px; letter-spacing: 1.2px;
  text-transform: uppercase; cursor: pointer;
}
.fb-send:disabled { opacity: 0.5; cursor: default; }
.fb-success {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.5px;
  color: var(--reform); text-align: center; padding: 20px 0;
}
.fb-error {
  font-family: var(--mono); font-size: 9px; letter-spacing: 0.5px;
  color: var(--coup); margin-top: 2px;
}
```

- [ ] **Step 3: Verify the file still has valid CSS (no unclosed braces)**

```bash
grep -c "{" index.html && grep -c "}" index.html
```

The two counts should be equal (or within 1–2 of each other due to JS objects — just eyeball that nothing looks broken near your edit).

- [ ] **Step 4: Open `index.html` in a browser via `python3 -m http.server 8000` and check the page loads without console errors**

Expected: page renders normally, no CSS parse errors in DevTools console.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add feedback button and panel CSS"
```

---

## Task 2: Add HTML for button and panel

**Files:**
- Modify: `index.html` — insert before `</body>` at line 6274

- [ ] **Step 1: Locate the `</body>` tag near the end of `index.html`**

It is at approximately line 6274, immediately followed by `</html>`.

- [ ] **Step 2: Insert the following HTML block immediately before `</body>`**

```html
<!-- ── Feedback Button & Panel ────────────────────────── -->
<button class="fb-btn" id="fb-trigger" onclick="toggleFeedback()" aria-label="Submit feedback or suggestion">
  <span class="fb-btn-dot"></span>Suggest
</button>
<div class="fb-panel" id="fb-panel" role="dialog" aria-label="Feedback panel">
  <button class="fb-panel-close" onclick="closeFeedback()" aria-label="Close">✕</button>
  <div class="fb-panel-title">Suggest / Feedback</div>
  <div class="fb-panel-sub">Flag a missed event, suggest a source, or correct a classification.</div>
  <form id="fb-form" onsubmit="submitFeedback(event)">
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div>
        <div class="fb-field-label">Category *</div>
        <select class="fb-select" id="fb-category" required>
          <option value="" disabled selected>Select a category</option>
          <option value="Missed event">Missed event</option>
          <option value="Wrong classification">Wrong classification</option>
          <option value="Source suggestion">Source suggestion</option>
          <option value="Country profile correction">Country profile correction</option>
          <option value="Research tip">Research tip</option>
          <option value="Other">Other</option>
        </select>
      </div>
      <div>
        <div class="fb-field-label">Country</div>
        <select class="fb-select" id="fb-country">
          <option value="">Regional / General</option>
          <option value="Argentina">Argentina</option>
          <option value="Belize">Belize</option>
          <option value="Bolivia">Bolivia</option>
          <option value="Brazil">Brazil</option>
          <option value="Chile">Chile</option>
          <option value="Colombia">Colombia</option>
          <option value="Costa Rica">Costa Rica</option>
          <option value="Cuba">Cuba</option>
          <option value="Dominican Republic">Dominican Republic</option>
          <option value="Ecuador">Ecuador</option>
          <option value="El Salvador">El Salvador</option>
          <option value="Guatemala">Guatemala</option>
          <option value="Guyana">Guyana</option>
          <option value="Haiti">Haiti</option>
          <option value="Honduras">Honduras</option>
          <option value="Jamaica">Jamaica</option>
          <option value="Mexico">Mexico</option>
          <option value="Nicaragua">Nicaragua</option>
          <option value="Panama">Panama</option>
          <option value="Paraguay">Paraguay</option>
          <option value="Peru">Peru</option>
          <option value="Suriname">Suriname</option>
          <option value="Trinidad and Tobago">Trinidad and Tobago</option>
          <option value="Uruguay">Uruguay</option>
          <option value="Venezuela">Venezuela</option>
        </select>
      </div>
      <div>
        <div class="fb-field-label">Message *</div>
        <textarea class="fb-textarea" id="fb-message" placeholder="What did we miss?" required></textarea>
      </div>
      <div>
        <div class="fb-field-label">Email (optional)</div>
        <input class="fb-input" type="email" id="fb-email" placeholder="your@email.edu">
      </div>
      <div id="fb-error" class="fb-error" style="display:none;"></div>
      <button class="fb-send" type="submit" id="fb-submit">Send →</button>
    </div>
  </form>
  <div id="fb-success" class="fb-success" style="display:none;">Sent. Thank you.</div>
</div>
```

- [ ] **Step 3: Verify the button renders**

Open `http://localhost:8000` (or restart with `python3 -m http.server 8000`). You should see a dark "● SUGGEST" button fixed at the bottom-right of every tab.

- [ ] **Step 4: Verify the panel appears on click**

Click the button. The panel should slide up above it with the title "Suggest / Feedback" and all four fields visible. Click ✕ — panel should close.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add feedback button and panel HTML"
```

---

## Task 3: Add JavaScript (toggle, close, submit)

**Files:**
- Modify: `index.html` — insert before `</script>` at line 6273

- [ ] **Step 1: Locate the closing `</script>` tag at approximately line 6273**

It is the last `</script>` tag in the file, just before `</body>`.

- [ ] **Step 2: Insert the following JS block immediately before `</script>`**

```javascript
// ── Feedback Button ────────────────────────────────────
const FORMSPREE_ENDPOINT = 'https://formspree.io/f/REPLACE_ME'; // → create form at formspree.io, paste your endpoint ID here

function toggleFeedback() {
  const panel = document.getElementById('fb-panel');
  panel.classList.contains('open') ? closeFeedback() : openFeedback();
}
function openFeedback() {
  document.getElementById('fb-panel').classList.add('open');
}
function closeFeedback() {
  document.getElementById('fb-panel').classList.remove('open');
}
function resetFeedbackForm() {
  document.getElementById('fb-form').reset();
  document.getElementById('fb-form').style.display = '';
  document.getElementById('fb-success').style.display = 'none';
  document.getElementById('fb-error').style.display = 'none';
  document.getElementById('fb-submit').disabled = false;
}
async function submitFeedback(e) {
  e.preventDefault();
  const category = document.getElementById('fb-category').value;
  const country  = document.getElementById('fb-country').value;
  const message  = document.getElementById('fb-message').value;
  const email    = document.getElementById('fb-email').value.trim();
  const errorEl  = document.getElementById('fb-error');
  const submitBtn = document.getElementById('fb-submit');

  const payload = {
    category,
    message,
    _subject: `SENTINEL Feedback — ${category}`
  };
  if (country) payload.country = country;
  if (email)   payload.email   = email;

  submitBtn.disabled = true;
  errorEl.style.display = 'none';

  try {
    const res = await fetch(FORMSPREE_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      document.getElementById('fb-form').style.display = 'none';
      document.getElementById('fb-success').style.display = 'block';
      setTimeout(() => { closeFeedback(); setTimeout(resetFeedbackForm, 300); }, 2000);
    } else {
      throw new Error('server error');
    }
  } catch {
    errorEl.textContent = 'Something went wrong — try again.';
    errorEl.style.display = 'block';
    submitBtn.disabled = false;
  }
}

// Close panel on outside click
document.addEventListener('click', function(e) {
  const panel = document.getElementById('fb-panel');
  const btn   = document.getElementById('fb-trigger');
  if (panel.classList.contains('open') && !panel.contains(e.target) && !btn.contains(e.target)) {
    closeFeedback();
  }
});
// Close panel on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeFeedback();
});
```

- [ ] **Step 3: Reload the page and verify toggle behavior**

- Click "Suggest" → panel opens
- Click "Suggest" again → panel closes
- Open panel → click outside it → panel closes
- Open panel → press Escape → panel closes
- Open panel → click ✕ → panel closes

- [ ] **Step 4: Verify form validation**

- Click "Suggest", click "Send →" without filling anything → browser should block submission (native `required` validation on Category and Message)
- Fill Category + Message, leave Email blank → "Send →" should attempt fetch (will fail with `REPLACE_ME` endpoint — that's expected; you should see "Something went wrong — try again." in the error line)

- [ ] **Step 5: Verify error state**

With `REPLACE_ME` still in place, submitting a valid form should show "Something went wrong — try again." below the send button, and the button should re-enable.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat: add feedback button JS (toggle, Formspree submit, success/error states)"
```

---

## Task 4: Wire up Formspree endpoint

**Files:**
- Modify: `index.html` — update `FORMSPREE_ENDPOINT` constant

- [ ] **Step 1: Create a Formspree account and form**

1. Go to [formspree.io](https://formspree.io) and sign up (free tier supports 50 submissions/month)
2. Create a new form — name it "SENTINEL Feedback"
3. Copy the endpoint URL (format: `https://formspree.io/f/xxxxxxxx`)

- [ ] **Step 2: Replace the placeholder in `index.html`**

Find this line (near the end of the JS block you just added):

```javascript
const FORMSPREE_ENDPOINT = 'https://formspree.io/f/REPLACE_ME';
```

Replace with your actual endpoint:

```javascript
const FORMSPREE_ENDPOINT = 'https://formspree.io/f/YOUR_FORM_ID';
```

- [ ] **Step 3: Verify end-to-end submission**

1. Open `http://localhost:8000`
2. Click "Suggest"
3. Select Category: "Research tip", Country: "Mexico", fill in a test message, leave email blank
4. Click "Send →"
5. Panel should show "Sent. Thank you." and auto-close after 2 seconds
6. Check Formspree dashboard — submission should appear with subject `SENTINEL Feedback — Research tip`

- [ ] **Step 4: Verify success-then-reopen flow**

After the panel auto-closes, click "Suggest" again. The form should be reset (blank fields, no success/error message visible).

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: wire Formspree endpoint for feedback button"
```

---

## Self-Review Notes

- **Spec coverage:** All spec requirements covered — button placement, panel fields, category/country dropdowns, optional email, fetch POST, `_subject` field, success/error states, close behaviors, `FORMSPREE_ENDPOINT` constant with comment.
- **No placeholders** in implementation steps — all code is complete and runnable.
- **Type consistency:** `toggleFeedback`, `openFeedback`, `closeFeedback`, `resetFeedbackForm`, `submitFeedback` used consistently across tasks. IDs `fb-panel`, `fb-trigger`, `fb-form`, `fb-category`, `fb-country`, `fb-message`, `fb-email`, `fb-submit`, `fb-error`, `fb-success` defined in Task 2 HTML and referenced in Task 3 JS.
- **Formspree note:** Task 4 is a user action (requires account creation). The code in Task 3 is complete and testable with the `REPLACE_ME` placeholder — error state is the expected result until Task 4 is done.
