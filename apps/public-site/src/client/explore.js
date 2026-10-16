// Explore page: map layer switching, sortable indicator table, and the long-run comparison chart.

const $ = (s, el = document) => el.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

/* ── Map layers ── */
document.querySelectorAll('.x-map [data-layer]').forEach(btn => btn.addEventListener('click', () => {
  const layer = btn.dataset.layer;
  document.querySelectorAll('.x-map [data-layer]').forEach(b => b.setAttribute('aria-checked', String(b === btn)));
  document.querySelectorAll('#xmap .xm-c').forEach(p => p.setAttribute('fill', p.dataset[layer.replace(/-(\w)/g, (_, c) => c.toUpperCase())]));
  $('[data-legend="status"]').hidden = layer !== 'status';
  $('[data-legend="level"]').hidden = layer === 'status';
}));

/* ── Sortable indicators ── */
const table = $('#x-ind-t');
if (table) {
  table.querySelectorAll('th[data-sort] button').forEach(btn => btn.addEventListener('click', () => {
    const th = btn.closest('th'), key = th.dataset.sort, col = [...th.parentNode.children].indexOf(th);
    const asc = th.getAttribute('aria-sort') === 'descending' || (th.getAttribute('aria-sort') == null && key === 'name');
    table.querySelectorAll('th[data-sort]').forEach(h => h.removeAttribute('aria-sort'));
    th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
    const body = table.tBodies[0], rows = [...body.rows];
    const val = r => key === 'name' ? r.dataset.name : parseFloat(r.cells[col].dataset.v);
    rows.sort((a, b) => {
      const x = val(a), y = val(b);
      if (key === 'name') return asc ? x.localeCompare(y) : y.localeCompare(x);
      if (Number.isNaN(x)) return 1; if (Number.isNaN(y)) return -1;
      return asc ? x - y : y - x;
    });
    body.append(...rows);
  }));
}

/* ── Long-run comparison ── */
const dataEl = $('#x-data');
if (dataEl) {
  const data = JSON.parse(dataEl.textContent);
  const COLORS = ['var(--amber)', 'var(--t-aid)', 'var(--t-reform)', 'var(--t-cp)', 'var(--t-coup)'];
  const draw = () => {
    const code = $('#x-ind-pick').value, d = data[code];
    const picks = [...document.querySelectorAll('.x-picks [aria-pressed="true"]')].map(b => b.dataset.c).filter(c => d.countries[c]);
    const W = 760, H = 300, L = 46, R = 110, T = 14, B = 28;
    const lines = picks.map(c => d.countries[c]);
    // Each series ends at its stated year; earlier points are spaced evenly back from it.
    const last = Math.max(...lines.map(s => s.last), 0), first = Math.min(...lines.map(s => s.last - s.series.length + 1), last);
    const vals = lines.flatMap(s => s.series.filter(v => typeof v === 'number'));
    if (!vals.length) { $('#x-chart-svg').innerHTML = '<p class="note">Choose at least one country with data.</p>'; return; }
    let lo = Math.min(...vals), hi = Math.max(...vals); if (lo === hi) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * .08; lo -= pad; hi += pad;
    const x = yr => L + (W - L - R) * (yr - first) / Math.max(1, last - first);
    const y = v => T + (H - T - B) * (1 - (v - lo) / (hi - lo));
    const ticks = Array.from({length: 5}, (_, i) => lo + (hi - lo) * i / 4);
    const fmt = v => Math.abs(hi - lo) < 5 ? v.toFixed(2) : v.toFixed(0);
    const decades = []; for (let yr = Math.ceil(first / 10) * 10; yr <= last; yr += 10) decades.push(yr);
    let svg = ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="var(--rule-2)"/><text x="${L - 6}" y="${y(v).toFixed(1)}" dy=".32em" text-anchor="end">${fmt(v)}</text>`).join('');
    svg += decades.map(yr => `<text x="${x(yr).toFixed(1)}" y="${H - 8}" text-anchor="middle">${yr}</text>`).join('');
    const ends = [];
    picks.forEach((c, i) => {
      const s = d.countries[c], start = s.last - s.series.length + 1;
      const pts = s.series.map((v, j) => typeof v === 'number' ? [x(start + j), y(v)] : null).filter(Boolean);
      if (!pts.length) return;
      svg += `<path d="${pts.map((p, j) => `${j ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('')}" fill="none" stroke="${COLORS[i]}" stroke-width="2"><title>${esc(c)}</title></path>`;
      const lp = pts[pts.length - 1];
      ends.push({c, y: lp[1], x: lp[0], color: COLORS[i], v: s.series.filter(v => typeof v === 'number').at(-1)});
    });
    // Keep end labels from overlapping.
    ends.sort((a, b) => a.y - b.y).forEach((e, i, arr) => { if (i && e.y - arr[i - 1].y < 14) e.y = arr[i - 1].y + 14; });
    svg += ends.map(e => `<circle cx="${e.x.toFixed(1)}" cy="${e.y.toFixed(1)}" r="3" fill="${e.color}"/><text class="lbl" x="${(e.x + 8).toFixed(1)}" y="${e.y.toFixed(1)}" dy=".32em" fill="${e.color}">${esc(e.c)} ${fmt(e.v)}</text>`).join('');
    $('#x-chart-svg').innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`${d.label}, ${first} to ${last}: ${picks.join(', ')}`)}">${svg}</svg>`;
    $('#x-chart-cap').textContent = `${d.label}, ${first}–${last}. Source: ${d.source}. Years before the latest are spaced evenly; for World Bank governance indicators, the early years were published every other year.`;
  };
  $('#x-ind-pick').addEventListener('change', draw);
  $('.x-picks').addEventListener('click', e => {
    const b = e.target.closest('[data-c]'); if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    if (!on && document.querySelectorAll('.x-picks [aria-pressed="true"]').length >= 5) return;
    b.setAttribute('aria-pressed', String(!on)); draw();
  });
  draw();
}
