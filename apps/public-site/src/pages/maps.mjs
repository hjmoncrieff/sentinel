// Region maps, drawn at build time as SVG. The browser only adds hover, pin and zoom.

import {topoFeatures, fitMercator, shape, intersects} from '../lib/geo.mjs';
import {esc, LEVELS, chip, lvl, tLabel, ago, fmtDate} from '../lib/html.mjs';

const STATUS_FILL = {stable: 'var(--st-stable-i)', strained: 'var(--st-strained-i)', crisis: 'var(--st-crisis-i)', authoritarian: 'var(--st-auth-i)'};
const outlookFill = level => `color-mix(in srgb, var(--st-crisis-i) ${18 + Math.max(0, LEVELS.indexOf(level)) * 20}%, var(--olive-3))`;

function project(model, width, pad) {
  const byNum = Object.fromEntries(model.countries.map(c => [String(c.num), c]));
  const all = topoFeatures(model.topology, 'countries');
  const tracked = all.filter(f => byNum[String(Number(f.id))]).map(f => ({...f, c: byNum[String(Number(f.id))]}));
  const proj = fitMercator(tracked, width, pad);
  const trackedShapes = tracked.map(f => ({c: f.c, ...shape(f, proj.project)}));
  const backdrop = all.filter(f => !byNum[String(Number(f.id))]).map(f => shape(f, proj.project))
    .filter(s => s.d && intersects(s.bounds, proj.width, proj.height));
  return {proj, trackedShapes, backdrop};
}

/** Front-page map: status / outlook / activity layers, located events, per-country count stacks. */
export function heroMap(model, events, ctx) {
  const W = 620;
  const {proj, trackedShapes, backdrop} = project(model, W, 6);
  const H = proj.height;
  const maxN30 = Math.max(1, ...model.countries.map(c => c.n30));
  const fills = c => ({
    status: STATUS_FILL[c.cmr_class] || 'var(--olive-3)',
    outlook: outlookFill(c.outlook.level),
    activity: c.n30 ? `color-mix(in srgb, var(--i-amber) ${25 + Math.round(75 * c.n30 / maxN30)}%, var(--olive-3))` : 'var(--olive-3)',
  });
  const attrs = c => {
    const f = fills(c);
    return `data-iso="${c.iso3}" data-status="${f.status}" data-outlook="${f.outlook}" data-activity="${f.activity}" fill="${f.status}" tabindex="0" role="button" aria-label="${esc(`${c.name}: ${c.cmr_status}, outlook ${c.outlook.level || 'not modeled'}`)}"`;
  };
  const countries = trackedShapes.map(s => `<path class="hm-c" d="${s.d}" ${attrs(s.c)} fill-opacity=".85" stroke="var(--olive)" stroke-width=".6"/>`).join('');
  const small = trackedShapes.filter(s => s.area < 160)
    .map(s => `<circle class="hm-c" cx="${s.centroid[0].toFixed(1)}" cy="${s.centroid[1].toFixed(1)}" r="5.5" ${attrs(s.c)} stroke="var(--olive)" stroke-width=".6"/>`).join('');
  const located = events.filter(e => e.coords && e.precision === 'place')
    .sort((a, b) => (a.sal === 'high') - (b.sal === 'high'))
    .map(e => { const [x, y] = proj.project([e.coords[1], e.coords[0]]); return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${e.sal === 'high' ? 4.2 : 2.8}" fill="${e.sal === 'high' ? 'var(--st-crisis-i)' : 'var(--i-ink)'}" stroke="var(--olive)" stroke-width="1"/>`; }).join('');
  const shapeBy = Object.fromEntries(trackedShapes.map(s => [s.c.name, s]));
  const stacks = {};
  for (const e of events) if (e.precision !== 'place' && shapeBy[e.country]) {
    const s = (stacks[e.country] ||= {n: 0, high: 0}); s.n++; if (e.sal === 'high') s.high++;
  }
  const stackSvg = Object.entries(stacks).map(([name, s]) => {
    const [x, y] = shapeBy[name].centroid;
    const label = `${name}: ${s.n} country-level event${s.n === 1 ? '' : 's'} (${s.high} high). Open them in the feed.`;
    return `<a href="${ctx.url(`feed/?c=${encodeURIComponent(name)}&p=30`)}" aria-label="${esc(label)}"><g transform="translate(${x.toFixed(1)},${(y - 12).toFixed(1)})"><title>${esc(label)}</title><rect x="-11" y="-8" width="22" height="16" rx="8" fill="var(--olive)" stroke="${s.high ? 'var(--st-crisis-i)' : 'var(--i-dim)'}" stroke-width="1.2"/><text text-anchor="middle" dy=".35em" font-family="IBM Plex Mono, monospace" font-size="10" fill="var(--i-ink)">${s.n}</text></g></a>`;
  }).join('');
  const labels = trackedShapes.filter(s => s.area > 900)
    .map(s => `<text x="${s.centroid[0].toFixed(1)}" y="${(s.centroid[1] + 12).toFixed(1)}" text-anchor="middle" fill="var(--olive)" font-family="IBM Plex Mono, monospace" font-size="9.5" font-weight="500">${s.c.iso3}</text>`).join('');

  // Zoom presets: a viewBox around each subregion group, kept at the full map's aspect ratio.
  const groups = {all: () => true, north: c => ['Mexico', 'Central America'].includes(c.subregion), Caribbean: c => c.subregion === 'Caribbean', Andean: c => c.subregion === 'Andean', south: c => ['Brazil', 'Southern Cone'].includes(c.subregion)};
  const zooms = {};
  for (const [key, test] of Object.entries(groups)) {
    if (key === 'all') { zooms.all = [0, 0, W, H]; continue; }
    const bs = trackedShapes.filter(s => test(s.c)).map(s => s.bounds);
    let [x0, y0, x1, y1] = [Math.min(...bs.map(b => b[0])), Math.min(...bs.map(b => b[1])), Math.max(...bs.map(b => b[2])), Math.max(...bs.map(b => b[3]))];
    let w = (x1 - x0) * 1.12, h = (y1 - y0) * 1.12;
    if (w / h > W / H) h = w * H / W; else w = h * W / H;
    zooms[key] = [(x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - h / 2, w, h].map(v => +v.toFixed(1));
  }

  const cards = Object.fromEntries(model.countries.map(c => {
    const evs = events.filter(e => e.country === c.name);
    const dom = Object.entries(evs.reduce((m, e) => (m[e.type] = (m[e.type] || 0) + 1, m), {})).sort((a, b) => b[1] - a[1])[0];
    const high = evs.filter(e => e.sal === 'high').length;
    const watch = c.outlook.watch?.[0];
    return [c.iso3, `
      <div class="hm-card-h"><b>${esc(c.name)}</b><span class="iso">${c.iso3}</span><button type="button" class="hm-x" aria-label="Close">×</button></div>
      <div class="hm-row">${chip(c)}${lvl(c.outlook.level)}</div>
      <dl>
        <dt>Leading pressure</dt><dd>${esc(c.outlook.leading || '—')}</dd>
        <dt>Events, 30 days</dt><dd>${evs.length}${high ? ` · ${high} high` : ''}${dom ? ` · mostly ${esc(tLabel(dom[0]).toLowerCase())}` : ''}</dd>
        ${c.last ? `<dt>Last event</dt><dd>${ago(model.asof, c.last)}</dd>` : ''}
      </dl>
      ${watch ? `<p class="hm-watch">${esc(watch[0].toUpperCase() + watch.slice(1))}.</p>` : ''}
      <div class="hm-actions"><a href="${ctx.url(`countries/${c.iso3.toLowerCase()}/`)}">Open monitor →</a>${evs.length ? `<a href="${ctx.url(`feed/?c=${encodeURIComponent(c.name)}&p=30`)}">See ${evs.length} event${evs.length === 1 ? '' : 's'}</a>` : ''}</div>
      <p class="hm-hint">Click to pin</p>`];
  }));

  const legend = (items) => items.map(([n, col]) => `<span><i style="background:${col}"></i>${n}</span>`).join('');
  const legends = {
    status: legend([['Stable', 'var(--st-stable-i)'], ['Strained', 'var(--st-strained-i)'], ['Crisis', 'var(--st-crisis-i)'], ['Authoritarian', 'var(--st-auth-i)']]),
    outlook: legend(LEVELS.map(l => [l[0].toUpperCase() + l.slice(1), outlookFill(l)])),
    activity: legend([['None', 'var(--olive-3)'], ['Some', 'color-mix(in srgb, var(--i-amber) 40%, var(--olive-3))'], ['Most', 'var(--i-amber)']]),
  };
  const marks = '<span><i style="background:var(--i-ink);border-radius:50%;width:6px;height:6px"></i>Located event</span><span><i style="background:var(--olive);border:1.2px solid var(--i-dim);border-radius:6px;width:14px"></i>Country-level count</span>';

  const svg = `<svg id="hero-map" viewBox="0 0 ${W} ${H}" data-zooms='${JSON.stringify(zooms)}' role="group" aria-label="Map of Latin America and the Caribbean with coded events from the past 30 days">
    <g>${backdrop.map(s => `<path d="${s.d}" fill="var(--olive-2)" stroke="var(--olive)" stroke-width=".5"/>`).join('')}</g>
    <g>${countries}</g><g>${small}</g>
    <g style="pointer-events:none">${located}</g><g>${stackSvg}</g>
    <g style="pointer-events:none">${labels}</g></svg>`;
  return {svg, cards, legends, marks};
}

/** Countries-page map: status fill, in-depth outline, each country a link. */
export function boardMap(model, ctx) {
  const W = 480;
  const {proj, trackedShapes, backdrop} = project(model, W, 8);
  const paths = trackedShapes.map(s => {
    const c = s.c, deep = !!c.in_depth;
    return `<a href="${ctx.url(`countries/${c.iso3.toLowerCase()}/`)}" data-iso="${c.iso3}"><path d="${s.d}" data-deep="${deep ? 1 : 0}" fill="${STATUS_FILL[c.cmr_class]}" fill-opacity=".82" stroke="${deep ? 'var(--i-amber)' : 'var(--olive)'}" stroke-width="${deep ? 1.5 : .6}"><title>${esc(`${c.name} · ${c.cmr_status} · outlook ${c.outlook.level || '—'}`)}</title></path></a>`;
  }).join('');
  const labels = trackedShapes.filter(s => s.area > 900)
    .map(s => `<text x="${s.centroid[0].toFixed(1)}" y="${s.centroid[1].toFixed(1)}" dy=".35em" text-anchor="middle" fill="var(--olive)" font-family="IBM Plex Mono, monospace" font-size="10" font-weight="500" style="pointer-events:none">${s.c.iso3}</text>`).join('');
  return `<svg id="map" viewBox="0 0 ${W} ${proj.height}" role="group" aria-label="Map of Latin America and the Caribbean coloured by civil-military status">
    <g>${backdrop.map(s => `<path d="${s.d}" fill="var(--olive-3)" stroke="var(--olive)" stroke-width=".5"/>`).join('')}</g><g>${paths}</g><g>${labels}</g></svg>`;
}

/** In-depth timeline: curated milestones by lane plus the country's coded events. */
const LANES = [['military', 'Military', '--t-coup'], ['political', 'Political', '--t-protest'], ['peace', 'Peace process', '--t-peace'], ['reform', 'Reform', '--t-reform'], ['oc', 'Organized crime', '--t-oc'], ['intl', 'International', '--t-coop'], ['live', 'Coded events', '--i-amber']];
export function timeline(c, events, asof) {
  const sm = c.in_depth;
  const W = 1100, laneH = 30, top = 24, H = top + LANES.length * laneH + 26, x0 = 118, x1 = W - 12;
  const t0 = Date.UTC(sm.timeline_start, 0, 1), t1 = new Date(asof + 'T00:00:00Z').getTime();
  const x = d => x0 + (new Date(d + 'T00:00:00Z').getTime() - t0) / (t1 - t0) * (x1 - x0);
  const lane = Object.fromEntries(LANES.map((l, i) => [l[0], top + i * laneH + laneH / 2]));
  const color = Object.fromEntries(LANES.map(l => [l[0], `var(${l[2]})`]));
  const years = []; for (let y = sm.timeline_start; y <= +asof.slice(0, 4); y++) years.push(y);
  const grid = years.map(y => { const gx = x(`${y}-01-01`).toFixed(1); return `<line x1="${gx}" x2="${gx}" y1="${top - 6}" y2="${H - 22}" stroke="var(--olive-line)"/><text x="${(+gx + 3).toFixed(1)}" y="${H - 8}" fill="var(--i-faint)" font-family="IBM Plex Mono, monospace" font-size="10">${y}</text>`; }).join('');
  const lanes = LANES.map(l => `<text x="0" y="${lane[l[0]] + 4}" fill="var(--i-dim)" font-family="IBM Plex Sans Condensed, sans-serif" font-size="12">${l[1]}</text><line x1="${x0}" x2="${x1}" y1="${lane[l[0]]}" y2="${lane[l[0]]}" stroke="var(--olive-line)" stroke-dasharray="2 4"/>`).join('');
  const read = (d, kind) => `data-date="${esc(fmtDate(d.date))}" data-kind="${kind}" data-title="${esc(d.title)}" data-desc="${esc(d.desc || d.summary || '')}"`;
  const live = events.filter(e => e.date >= `${sm.timeline_start}-01-01`).map(e =>
    `<circle class="tl-m" cx="${x(e.date).toFixed(1)}" cy="${lane.live + (e.sal === 'high' ? 0 : e.sal === 'medium' ? 5 : -5)}" r="${e.sal === 'high' ? 4 : 2.6}" fill="var(--i-amber)" fill-opacity="${e.sal === 'high' ? .95 : .45}" ${read(e, 'Coded event')}/>`).join('');
  const marks = sm.milestones.map(m => {
    const cy = lane[m.cat] ?? lane.political;
    return `<rect class="tl-m" tabindex="0" x="${(x(m.date) - 5).toFixed(1)}" y="${cy - 5}" width="10" height="10" fill="${color[m.cat] || 'var(--i-dim)'}" stroke="var(--i-ink)" stroke-width=".8" ${read(m, 'Milestone')}><title>${esc(`${fmtDate(m.date)}: ${m.title}`)}</title></rect>`;
  }).join('');
  const last = sm.milestones[sm.milestones.length - 1];
  return {
    svg: `<svg id="tl" viewBox="0 0 ${W} ${H}" height="${H}" role="group" aria-label="${esc(`Timeline of ${c.name}, ${sm.timeline_start} to today`)}"><g>${grid}</g><g>${lanes}</g><g>${live}</g><g>${marks}</g></svg>`,
    initial: last ? `<span class="d">${esc(fmtDate(last.date))}<br>Milestone</span><div><h3>${esc(last.title)}</h3><p>${esc(last.desc || '')}</p></div>` : '',
  };
}
