// Light / dark switch. The choice is shared with the dashboard through localStorage
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
