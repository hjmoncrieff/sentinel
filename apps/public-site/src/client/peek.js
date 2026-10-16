// Hover cards. Any element with data-peek="key" shows <template id="pk-key"> beside it:
// on mouse hover, on keyboard focus, or on tap for elements that are not links.
// Every element sharing the key is marked while the card is open, so a timeline entry
// and its marker on the strip light up together.

const card = document.createElement('div');
card.className = 'peek';
card.hidden = true;
card.setAttribute('role', 'dialog');
card.setAttribute('aria-label', 'Preview');
document.body.append(card);

let cur = null, showT = 0, hideT = 0;
const tpl = el => document.getElementById(`pk-${el.dataset.peek}`);
const mark = (k, on) => document.querySelectorAll(`[data-peek="${CSS.escape(k)}"]`).forEach(n => n.classList.toggle('pk-on', on));

function place(el) {
  card.style.left = '0px'; card.style.top = '0px';
  const r = el.getBoundingClientRect(), w = card.offsetWidth, h = card.offsetHeight;
  const vw = document.documentElement.clientWidth, vh = window.innerHeight;
  const x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), vw - w - 8);
  let y = r.bottom + 8;
  if (y + h > vh - 8 && r.top - h - 8 > 8) y = r.top - h - 8;
  card.style.left = `${x + window.scrollX}px`;
  card.style.top = `${y + window.scrollY}px`;
}

function show(el) {
  clearTimeout(hideT);
  if (cur === el) return;
  const t = tpl(el);
  if (!t) return;
  if (cur) mark(cur.dataset.peek, false);
  card.replaceChildren(t.content.cloneNode(true));
  card.hidden = false;
  cur = el;
  mark(el.dataset.peek, true);
  place(el);
}

function hide() {
  clearTimeout(showT);
  if (!cur) return;
  mark(cur.dataset.peek, false);
  cur = null;
  card.hidden = true;
}

const later = () => { clearTimeout(hideT); hideT = setTimeout(hide, 220); };
const trigger = t => t instanceof Element ? t.closest('[data-peek]') : null;

document.addEventListener('pointerover', e => {
  if (e.pointerType !== 'mouse') return;
  if (card.contains(e.target)) { clearTimeout(hideT); return; }
  const el = trigger(e.target);
  clearTimeout(showT);
  if (el) showT = setTimeout(() => show(el), cur ? 60 : 160);
});
document.addEventListener('pointerout', e => {
  if (e.pointerType !== 'mouse') return;
  const to = e.relatedTarget;
  if (to && (card.contains(to) || (cur && trigger(to) === cur))) return;
  clearTimeout(showT);
  if (cur) later();
});

document.addEventListener('focusin', e => {
  if (card.contains(e.target)) { clearTimeout(hideT); return; }
  const el = trigger(e.target);
  if (el) show(el); else if (cur) hide();
});

// Tap or click: buttons and other non-link triggers toggle their card; links navigate as usual.
document.addEventListener('click', e => {
  if (card.contains(e.target)) return;
  const el = trigger(e.target);
  if (el && !el.closest('a')) {
    if (el.tagName === 'LI' && e.target.closest('a, button:not([data-peek])')) return;
    e.preventDefault();
    if (cur === el) hide(); else { hide(); show(el); }
    return;
  }
  if (cur && !el) hide();
});

document.addEventListener('keydown', e => {
  if (e.key !== 'Escape' || !cur) return;
  const el = cur;
  hide();
  if (card.contains(document.activeElement) || document.activeElement === document.body) el.focus?.();
});
window.addEventListener('resize', hide);
