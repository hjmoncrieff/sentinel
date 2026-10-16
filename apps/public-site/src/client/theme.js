// Light / dark switch. The choice is shared with the static pages through localStorage
// ('sentinel-theme'); with no stored choice the system setting applies.

const root = document.documentElement;
const btn = document.getElementById('theme-toggle');
const media = matchMedia('(prefers-color-scheme: dark)');
const current = () => root.dataset.theme || (media.matches ? 'dark' : 'light');

const label = () => {
  if (!btn) return;
  const mode = current();
  btn.dataset.mode = mode;
  btn.setAttribute('aria-label', mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
};

btn?.addEventListener('click', () => {
  const next = current() === 'dark' ? 'light' : 'dark';
  root.dataset.theme = next;
  try { localStorage.setItem('sentinel-theme', next); } catch { /* storage blocked: the choice lasts for this page */ }
  label();
});
media.addEventListener?.('change', label);
label();

// Freshness. Pages are rebuilt only when new data is published, so if publishing stops they would
// keep saying "updated" indefinitely; the browser checks the age of the data instead.
const STALE_HOURS = 48;
document.querySelectorAll('.fresh[data-published]').forEach(el => {
  const t = Date.parse(el.dataset.published);
  if (!t || Date.now() - t < STALE_HOURS * 36e5) return;
  el.classList.add('stale');
  el.title = 'No new events have been published for more than two days.';
  const text = el.querySelector('.fresh-t');
  if (text) text.textContent = `Updates paused since ${new Date(t).toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}`;
});
