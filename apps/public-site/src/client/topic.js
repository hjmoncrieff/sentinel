// Topic pages: the kind-of-event chips filter the year strip and the story list together.

const chips = [...document.querySelectorAll('.pl-chip')];
const list = document.querySelector('.cevents[data-show]');
const more = document.querySelector('.pl-more');
let lane = null, all = false;

function apply() {
  chips.forEach(c => c.setAttribute('aria-pressed', String(c.dataset.ln === lane)));
  document.querySelectorAll('.plstrip .pl-dot').forEach(d => d.classList.toggle('dim', !!lane && d.dataset.ln !== lane));
  document.querySelectorAll('.plstrip .pl-row').forEach(r => r.classList.toggle('on', r.dataset.ln === lane));
  if (!list) return;
  const rows = [...list.querySelectorAll(':scope > .cev')], match = rows.filter(r => !lane || r.dataset.ln === lane), n = +list.dataset.show;
  rows.forEach(r => { r.hidden = true; });
  match.forEach((r, i) => { r.hidden = !all && i >= n; });
  if (more) {
    more.hidden = all || match.length <= n;
    more.textContent = `Show all ${match.length}`;
  }
  let empty = list.querySelector('.pl-empty');
  if (!match.length) {
    if (!empty) { empty = document.createElement('p'); empty.className = 'note pl-empty'; list.append(empty); }
    empty.textContent = 'Nothing of this kind in the period.';
    empty.hidden = false;
  } else if (empty) empty.hidden = true;
}

chips.forEach(c => c.addEventListener('click', () => {
  lane = lane === c.dataset.ln ? null : c.dataset.ln;
  all = false;
  apply();
}));
more?.addEventListener('click', () => { all = true; apply(); });
if (chips.length) apply();
