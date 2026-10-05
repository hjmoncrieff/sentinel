// Small rendering helpers shared by the build (Node) and the browser.

export const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

// Legacy event families: the layer every event carries, v2- or v3-coded.
export const TYPE = {
  coup: ['Coup', '--t-coup'], purge: ['Purge', '--t-purge'], coup_proofing: ['Coup-proofing', '--t-cp'], aid: ['Military aid', '--t-aid'],
  coop: ['Security cooperation', '--t-coop'], protest: ['Protest', '--t-protest'], reform: ['Reform', '--t-reform'], conflict: ['Armed conflict', '--t-conflict'],
  exercise: ['Exercise', '--t-exercise'], procurement: ['Procurement', '--t-procurement'], peace: ['Peace process', '--t-peace'], oc: ['Organized crime', '--t-oc'], other: ['Other', '--t-other'],
};
export const tLabel = t => (TYPE[t] || TYPE.other)[0];
export const tColor = t => `var(${(TYPE[t] || TYPE.other)[1]})`;

export const LEVELS = ['low', 'guarded', 'elevated', 'high', 'severe'];

export const fmtDate = (d, opts = {day: 'numeric', month: 'short', year: 'numeric'}) =>
  new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', {timeZone: 'UTC', ...opts});
export const daysBetween = (later, earlier) => Math.round((new Date(later + 'T00:00:00Z') - new Date(earlier + 'T00:00:00Z')) / 864e5);
export const ago = (asof, d) => { if (!d) return '—'; const n = daysBetween(asof, d); return n <= 0 ? 'today' : n < 60 ? `D−${n}` : d.slice(0, 7); };

export function pips(level, pipVar = '--i-amber') {
  const n = LEVELS.indexOf(level) + 1;
  return `<span class="pips" style="--pip:var(${pipVar})" aria-hidden="true">${LEVELS.map((_, i) => `<span class="${i < n ? 'on' : ''}"></span>`).join('')}</span>`;
}
export const lvl = (level, pipVar) => level ? `<span class="lvl">${pips(level, pipVar)}${esc(level)}</span>` : '<span class="lvl">not modeled</span>';
export function dir(trend) {
  const t = (trend || 'stable').toLowerCase();
  if (t.startsWith('ris') || t.startsWith('up') || t.startsWith('worsen')) return '<span class="dir">↗ rising</span>';
  if (t.startsWith('eas') || t.startsWith('fall') || t.startsWith('down') || t.startsWith('improv')) return '<span class="dir">↘ easing</span>';
  return '<span class="dir">→ steady</span>';
}
export const chip = c => `<span class="chip st-${esc(c.cmr_class)}">${esc(c.cmr_status || '—')}</span>`;

// Corroboration pairs salience with how well sourced a record is.
export function corroboration(e) {
  const best = Math.min(...e.sources.map(s => s.tier || 9));
  if (e.n_sources >= 3 || (e.n_sources >= 2 && best <= 2)) return ['strong', 'Corroborated'];
  if (e.n_sources >= 2 || best <= 2) return ['moderate', 'One strong source'];
  return ['thin', 'Single source'];
}

const ACTOR_WORDS = {oc_group: 'an organized-crime group', military: 'the military', police: 'the police', external: 'an external actor', population: 'civilians', government: 'the government', executive: 'the executive', armed_group: 'an armed group', legislature: 'the legislature', judiciary: 'the courts', opposition: 'the opposition'};
export const plainActor = a => ACTOR_WORDS[a] || String(a).replaceAll('_', ' ');

// Event-count bars on one shared scale; the last seven bars are the past week.
export function sparkBars(series, max, w = 84, h = 22, color = 'var(--i-ink)') {
  const bw = w / series.length;
  const bars = series.map((v, i) => {
    if (!v) return '';
    const bh = Math.max(2, v / max * h), recent = i >= series.length - 7;
    return `<rect x="${(i * bw).toFixed(1)}" y="${(h - bh).toFixed(1)}" width="${Math.max(1, bw - .6).toFixed(1)}" height="${bh.toFixed(1)}" fill="${recent ? 'var(--i-amber)' : color}" fill-opacity="${recent ? 1 : .6}"/>`;
  }).join('');
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${series.reduce((a, b) => a + b, 0)} events in ${series.length} days"><line x1="0" x2="${w}" y1="${h - .5}" y2="${h - .5}" stroke="var(--line)"/><g>${bars}</g></svg>`;
}

export function lineSpark(series, w = 84, h = 26) {
  const vals = (series || []).filter(v => typeof v === 'number');
  if (vals.length < 2) return '';
  const lo = Math.min(...vals), hi = Math.max(...vals), r = hi - lo || 1;
  const pts = vals.map((v, i) => [i / (vals.length - 1) * (w - 4) + 2, h - 3 - (v - lo) / r * (h - 6)]);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('');
  const last = pts[pts.length - 1];
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="${d}L${last[0].toFixed(1)},${h}L2,${h}Z" fill="var(--amber-soft)"/><path d="${d}" fill="none" stroke="var(--ink-2)" stroke-width="1.2"/><circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.4" fill="var(--amber)"/></svg>`;
}
