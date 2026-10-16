// Explore: the data behind the monitors, laid side by side. Risk readings on a layered map,
// the structural indicators for every country (sortable), a long-run comparison chart, and
// coded activity by month and by country. Replaces the old dashboard's Explore tab.

import {esc, fmtDate, tColor, tLabel, chip, lvl, dir, lineSpark, LEVELS, TYPE} from '../lib/html.mjs';
import {layout} from './layout.mjs';
import {exploreMap, levelFill, statusFill} from './maps.mjs';

const countryUrl = (ctx, c) => ctx.url(`countries/${c.iso3.toLowerCase()}/`);
const CONSTRUCTS = [['regime_vulnerability', 'Regime vulnerability'], ['militarization', 'Militarization'], ['security_fragmentation', 'Security fragmentation']];
const NOTES = {
  polyarchy: 'V-Dem electoral democracy index, 0 to 1. Higher is more democratic.',
  mil_constrain: 'V-Dem: how far the military is constrained by civilian institutions. Higher is more constrained.',
  mil_exec: 'V-Dem: how far the executive depends on or is drawn from the military, 0 to 1. Higher is more entangled.',
  wgi_rule_of_law: 'World Bank governance indicator, roughly −2.5 to 2.5. Higher is stronger rule of law.',
  mil_exp_pct_gdp: 'Military expenditure as a share of GDP (SIPRI, via the World Bank).',
  inflation_consumer_prices_pct: 'Consumer price inflation, annual %.',
};

// Direction as an arrow, with the word for screen readers and on hover, so the table fits beside the map.
const arrow = trend => { const d = dir(trend), word = (d.match(/(rising|easing|steady)/) || [, 'steady'])[1]; return ` <span class="x-dir" title="${word}" aria-label="${word}">${d.match(/[↗↘→]/)[0]}</span>`; };

function readings(model, ctx) {
  const layers = [
    ['status', 'CMR status', statusFill],
    ['outlook', '90-day outlook', c => levelFill(c.outlook.level)],
    ...CONSTRUCTS.map(([code, label]) => [code.replaceAll('_', '-'), label, c => levelFill(c.constructs.find(k => k.code === code)?.level)]),
  ];
  const rows = model.subregions.map(s => `<tr class="grp"><td colspan="6">${esc(s)}</td></tr>` + model.countries.filter(c => c.subregion === s).map(c => `
    <tr><td><a href="${countryUrl(ctx, c)}">${esc(c.name)}</a></td><td>${chip(c)}</td><td>${lvl(c.outlook.level)}</td>${CONSTRUCTS.map(([code]) => { const k = c.constructs.find(x => x.code === code); return `<td>${k ? `${lvl(k.level)}${arrow(k.trend)}` : '—'}</td>`; }).join('')}</tr>`).join('')).join('');
  const levelLegend = LEVELS.map(l => `<span><i style="background:${levelFill(l)}"></i>${l}</span>`).join('');
  return `
    <section class="section" aria-labelledby="x-risk">
      <div class="sec-head"><h2 id="x-risk">Risk readings</h2><span class="kicker">Country risk model · as of ${fmtDate(model.asof)}</span></div>
      <div class="x-risk">
        <figure class="instr x-map">
          <div class="panel-title"><span>Map layer</span><span class="hm-layers" role="radiogroup" aria-label="Map layer">${layers.map(([k, l], i) => `<button type="button" role="radio" data-layer="${k}" aria-checked="${i === 0}">${esc(l)}</button>`).join('')}</span></div>
          ${exploreMap(model, ctx, layers)}
          <div class="map-legend" data-legend="status"><span><i style="background:var(--st-stable-i)"></i>Stable</span><span><i style="background:var(--st-strained-i)"></i>Strained</span><span><i style="background:var(--st-crisis-i)"></i>Crisis</span><span><i style="background:var(--st-auth-i)"></i>Authoritarian</span></div>
          <div class="map-legend" data-legend="level" hidden>${levelLegend}</div>
          <figcaption>Select a country to open its monitor. Levels are labelled readings; numeric scores are withheld until the model is validated.</figcaption>
        </figure>
        <div class="x-layers">
          <div class="kicker">What the layers show</div>
          <dl class="defs">
            <dt>CMR status</dt><dd>An analyst judgement in four classes: stable, strained, crisis and authoritarian. It changes rarely and only on review.</dd>
            <dt>90-day outlook</dt><dd>The risk model's overall reading for the next three months, combining structural indicators with recent coded events. ${model.countries.filter(c => ['high', 'severe'].includes(c.outlook.level)).length} countries are at high or severe.</dd>
            ${CONSTRUCTS.map(([code, label]) => `<dt>${esc(label)}</dt><dd>${esc(model.countries.flatMap(c => c.constructs).find(k => k.code === code)?.goal || '')}</dd>`).join('')}
          </dl>
          <p class="note">The three readings are shown on each country monitor with the events behind them.</p>
        </div>
      </div>
      <div class="tbl-scroll" style="margin-top:var(--s-5)"><table class="tbl x-read">
        <thead><tr><th>Country</th><th>Status</th><th>Outlook</th>${CONSTRUCTS.map(([, l]) => `<th>${esc(l)}</th>`).join('')}</tr></thead>
        <tbody>${rows}</tbody></table></div>
    </section>`;
}

function indicators(model, ctx) {
  const cols = model.countries[0].structural.map(s => ({code: s.code, label: s.label, source: s.source, year: s.year}));
  const cell = (c, code) => {
    const s = c.structural.find(x => x.code === code);
    if (!s) return '<td class="num">—</td>';
    const above = s.median != null && typeof s.num === 'number' ? s.num > parseFloat(s.median) : null;
    return `<td class="num" data-v="${typeof s.num === 'number' ? s.num : ''}"><span class="x-v">${esc(s.value)}</span>${lineSpark(s.series, 54, 18)}<small class="${above ? 'hi' : 'lo'}">${s.year !== cols.find(x => x.code === code).year ? s.year : ''}</small></td>`;
  };
  const median = code => model.countries.map(c => c.structural.find(x => x.code === code)).find(s => s?.median)?.median || '—';
  return `
    <section class="section" aria-labelledby="x-ind">
      <div class="sec-head"><h2 id="x-ind">Structural indicators</h2><span class="kicker">Select a column to sort</span></div>
      <div class="tbl-scroll"><table class="tbl x-ind" id="x-ind-t">
        <thead><tr><th data-sort="name" aria-sort="ascending"><button type="button">Country</button></th>${cols.map(c => `<th class="num" data-sort="${c.code}"><button type="button">${esc(c.label)}</button><small>${esc(c.source)} · ${c.year}</small></th>`).join('')}</tr>
          <tr class="x-med"><td>Region median</td>${cols.map(c => `<td class="num mono">${esc(median(c.code))}</td>`).join('')}</tr></thead>
        <tbody>${model.countries.map(c => `<tr data-name="${esc(c.name)}"><td><a href="${countryUrl(ctx, c)}">${esc(c.name)}</a></td>${cols.map(k => cell(c, k.code)).join('')}</tr>`).join('')}</tbody>
      </table></div>
      <dl class="x-defs">${cols.map(c => `<dt>${esc(c.label)}</dt><dd>${esc(NOTES[c.code] || '')} Small lines show the full series; a year is shown where a country's latest value is older.</dd>`).join('')}</dl>
    </section>`;
}

// Long-run comparison: the browser draws the chart from this data (client/explore.js).
function comparison(model) {
  const data = {};
  for (const s of model.countries[0].structural) {
    data[s.code] = {label: s.label, source: s.source, countries: {}};
    for (const c of model.countries) {
      const x = c.structural.find(k => k.code === s.code);
      if (x?.series?.length) data[s.code].countries[c.name] = {last: x.year, series: x.series};
    }
  }
  const picks = ['Venezuela', 'Colombia', 'Mexico', 'Uruguay'];
  return `
    <section class="section" aria-labelledby="x-cmp">
      <div class="sec-head"><h2 id="x-cmp">Over the long run</h2><span class="kicker">Compare up to five countries</span></div>
      <div class="x-cmp">
        <div class="x-cmp-ctl">
          <label class="kicker" for="x-ind-pick">Indicator</label>
          <select id="x-ind-pick" class="fselect">${Object.entries(data).map(([code, d], i) => `<option value="${code}"${i === 0 ? ' selected' : ''}>${esc(d.label)}</option>`).join('')}</select>
          <div class="kicker" style="margin-top:12px">Countries</div>
          <div class="x-picks" role="group" aria-label="Countries to compare">${model.countries.map(c => `<button type="button" data-c="${esc(c.name)}" aria-pressed="${picks.includes(c.name)}">${esc(c.name)}</button>`).join('')}</div>
        </div>
        <figure class="x-chart"><div id="x-chart-svg"></div><figcaption id="x-chart-cap"></figcaption></figure>
      </div>
      <script type="application/json" id="x-data">${JSON.stringify(data).replace(/</g, '\\u003c')}</script>
    </section>`;
}

function activity(model, ctx) {
  const months = model.monthly.slice(-18).map(([k]) => k);
  const types = Object.keys(TYPE);
  const by = months.map(k => { const m = {}; for (const e of model.events) if (e.content_type === 'event' && e.date.startsWith(k)) m[e.type] = (m[e.type] || 0) + 1; return [k, m]; });
  const W = 960, H = 210, L = 34, B = 34, T = 10, peak = Math.max(1, ...by.map(([, m]) => Object.values(m).reduce((a, b) => a + b, 0)));
  const step = [5, 10, 20, 25, 50, 100].find(s => peak / s <= 5) || 200, top = Math.ceil(peak / step) * step;
  const y = v => T + (H - T - B) * (1 - v / top), slot = (W - L) / by.length, bw = slot * .64;
  const grid = Array.from({length: top / step + 1}, (_, i) => i * step).map(v => `<line x1="${L}" x2="${W}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="var(--rule-2)"/><text x="${L - 6}" y="${y(v).toFixed(1)}" dy=".32em" text-anchor="end">${v}</text>`).join('');
  const bars = by.map(([k, m], i) => {
    const x = L + i * slot + (slot - bw) / 2, d = new Date(k + '-01T00:00:00Z'), total = Object.values(m).reduce((a, b) => a + b, 0);
    let acc = 0;
    const segs = types.filter(t => m[t]).map(t => { const y1 = y(acc + m[t]), h = y(acc) - y1; acc += m[t]; return `<rect x="${x.toFixed(1)}" y="${y1.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(0, h - .6).toFixed(1)}" fill="${tColor(t)}"/>`; }).join('');
    return `<g><title>${esc(`${fmtDate(k + '-01', {month: 'long', year: 'numeric'})}: ${total} events — ${Object.entries(m).sort((a, b) => b[1] - a[1]).map(([t, n]) => `${tLabel(t)} ${n}`).join(', ')}`)}</title>${segs}${total ? `<text class="n" x="${(x + bw / 2).toFixed(1)}" y="${(y(total) - 5).toFixed(1)}" text-anchor="middle">${total}</text>` : ''}<text x="${(x + bw / 2).toFixed(1)}" y="${H - B + 16}" text-anchor="middle">${d.toLocaleDateString('en-GB', {timeZone: 'UTC', month: 'short'})}</text>${i === 0 || d.getUTCMonth() === 0 ? `<text class="yr" x="${(x + bw / 2).toFixed(1)}" y="${H - B + 30}" text-anchor="middle">${d.getUTCFullYear()}</text>` : ''}</g>`;
  }).join('');
  // Country × type, past 12 months: where each kind of event is concentrated.
  const year = model.recent(365).filter(e => e.content_type === 'event');
  const used = types.filter(t => year.some(e => e.type === t));
  const max = Math.max(1, ...model.countries.flatMap(c => used.map(t => year.filter(e => e.country === c.name && e.type === t).length)));
  const heat = model.countries.filter(c => c.n365).sort((a, b) => b.n365 - a.n365).map(c => `<tr><td><a href="${countryUrl(ctx, c)}">${esc(c.name)}</a></td>${used.map(t => { const n = year.filter(e => e.country === c.name && e.type === t).length; return `<td class="num"${n ? ` style="background:color-mix(in srgb, ${tColor(t)} ${Math.round(12 + 70 * n / max)}%, transparent)"` : ''}>${n || ''}</td>`; }).join('')}<td class="num mono"><b>${c.n365}</b></td></tr>`).join('');
  return `
    <section class="section" aria-labelledby="x-act">
      <div class="sec-head"><h2 id="x-act">Coded activity</h2><a href="${ctx.url('feed/')}">Every record in the live feed →</a></div>
      <div class="act-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Coded events per month by type, region">${grid}${bars}</svg></div>
      <div class="aid-legend x-types">${used.map(t => `<span><i style="background:${tColor(t)}"></i>${esc(tLabel(t))}</span>`).join('')}</div>
      <p class="note">Events per month across the region, by type. Counts reflect how much was collected as well as what happened: collection started in March 2026 and was irregular until October 2026.</p>
      <div class="sec-head section"><h2>Where each kind of event happens</h2><span class="kicker">Past 12 months · deeper colour, more events</span></div>
      <div class="tbl-scroll"><table class="tbl x-heat"><thead><tr><th>Country</th>${used.map(t => `<th class="num">${esc(tLabel(t))}</th>`).join('')}<th class="num">All</th></tr></thead><tbody>${heat}</tbody></table></div>
    </section>`;
}

export function renderExplore(model, ctx) {
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>Explore</span></div>
    <section class="c-head" style="align-items:start">
      <div><div class="kicker">Explore · ${model.countries.length} countries</div><h1 style="margin-top:8px;font-size:clamp(38px,5vw,64px)">Explore the data</h1>
        <p class="dek">The readings and indicators behind the country monitors, side by side: where the risk model sees pressure, how the region compares on democracy, military constraint and spending over sixty years, and where each kind of event is being coded.</p></div>
      <dl class="facts">
        <dt>Risk readings</dt><dd>Country risk model, ${model.countries.length} countries</dd>
        <dt>Indicators</dt><dd>V-Dem v16, World Bank WDI and WGI</dd>
        <dt>Events</dt><dd class="mono">${model.events.length.toLocaleString('en')} coded records</dd>
        <dt>Also</dt><dd><a href="${ctx.url('us-security/')}#hist-h">US assistance since 1946</a> · <a href="${ctx.url('organized-crime/')}">organized crime</a></dd>
      </dl>
    </section>
    ${readings(model, ctx)}
    ${indicators(model, ctx)}
    ${comparison(model)}
    ${activity(model, ctx)}
  </div>`;
  return layout(ctx, {title: 'Explore the data', description: `Risk readings, structural indicators and coded activity for ${model.countries.length} countries in Latin America and the Caribbean.`, nav: 'explore', body, scripts: ['explore.js']});
}
