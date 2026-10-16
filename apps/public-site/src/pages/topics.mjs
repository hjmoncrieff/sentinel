// Topic pages: organized crime and US security. Each combines three layers: readings
// computed from the published events and the country risk model, structural data
// (UNODC figures, US assistance, the Greenbook), and a hand-written background in
// content/*.json whose every claim carries a numbered source.

import {esc, fmtDate, tColor, tLabel, lvl, dir, chip, daysBetween, usd, aidBars, lineSpark, LEVELS, AID_GROUPS} from '../lib/html.mjs';
import {layout} from './layout.mjs';
import {regionMap} from './maps.mjs';
import {eventUrl} from './event.mjs';
import {groupStories} from '../lib/model.mjs';

const countryUrl = (ctx, c) => ctx.url(`countries/${c.iso3.toLowerCase()}/`);
const within = (model, e, d) => { const n = daysBetween(model.asof, e.date); return n >= 0 && n <= d; };
const SAL = {high: 0, medium: 1, low: 2};
const COLLECTION_NOTE = 'Counts reflect how much was collected as well as what happened: collection started in March 2026 and was irregular until October 2026, and earlier dates come from archive searches.';

/* ───────────── Shared pieces ───────────── */

// Events of one story fold under their lead record, as on the country monitors.
function storyList(events, model, ctx, n) {
  const stories = groupStories(events).slice(0, n);
  if (!stories.length) return '<p class="note">No matching events in this period.</p>';
  const day = d => fmtDate(d, {day: 'numeric', month: 'short'});
  return `<div class="cevents">${stories.map(({lead: e, others}) => `
    <div class="cev"><span class="d">${day(e.date)}</span><span class="b" style="background:${tColor(e.type)}"></span>
      <div><a href="${eventUrl(ctx, e.id)}" style="text-decoration:none">${esc(e.title)}</a><small>${esc(e.country)} · ${tLabel(e.type)} · ${e.sal} salience · ${e.n_sources} source${e.n_sources > 1 ? 's' : ''}</small>
        ${others.length ? `<details class="cev-more"><summary>${others.length} more record${others.length > 1 ? 's' : ''} of this story</summary><ul>${others.map(o => `<li><a href="${eventUrl(ctx, o.id)}">${esc(o.title)}</a> <span>${esc(o.sources[0]?.name || '')} · ${day(o.date)}</span></li>`).join('')}</ul></details>` : ''}</div></div>`).join('')}</div>`;
}

const monthsOf = (events, asof, n = 12) => Array.from({length: n}, (_, i) => {
  const key = new Date(Date.UTC(+asof.slice(0, 4), +asof.slice(5, 7) - n + i, 1)).toISOString().slice(0, 7);
  return [key, events.filter(e => e.date.startsWith(key)).length];
});
function monthBars(series, color) {
  const W = 520, H = 120, L = 26, B = 22, T = 14, peak = Math.max(1, ...series.map(([, v]) => v)), slot = (W - L) / series.length, bw = slot * .62;
  const y = v => T + (H - T - B) * (1 - v / peak);
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`Events per month: ${series.map(([k, v]) => `${k} ${v}`).join(', ')}`)}">
    <line x1="${L}" x2="${W}" y1="${H - B}" y2="${H - B}" stroke="var(--rule)"/>
    ${series.map(([k, v], i) => { const x = L + i * slot + (slot - bw) / 2; return `<g><title>${esc(`${k}: ${v}`)}</title>${v ? `<rect x="${x.toFixed(1)}" y="${y(v).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H - B - y(v)).toFixed(1)}" fill="${color}"/><text x="${(x + bw / 2).toFixed(1)}" y="${(y(v) - 4).toFixed(1)}" text-anchor="middle">${v}</text>` : ''}<text x="${(x + bw / 2).toFixed(1)}" y="${H - 7}" text-anchor="middle">${new Date(k + '-01T00:00:00Z').toLocaleDateString('en-GB', {timeZone: 'UTC', month: 'short'})}</text></g>`; }).join('')}</svg>`;
}

// Numbered source marks; the list itself is rendered once at the foot of the page.
const cite = (ids = []) => ids.length ? `<sup class="rb-fn">${ids.map(i => `<a href="#src-${i + 1}" aria-label="Source ${i + 1}">${i + 1}</a>`).join(',')}</sup>` : '';
const para = parts => `<p>${parts.map(([t, ids]) => `${esc(t)}${cite(ids)}`).join(' ')}</p>`;
const byline = c => `<span class="label-ai">Written by hand · facts checked ${esc(fmtDate(c.as_of, {day: 'numeric', month: 'short', year: 'numeric'}))}</span>`;

function sourceList(c) {
  return `
    <section class="section" aria-labelledby="src-h">
      <div class="sec-head"><h2 id="src-h">Sources</h2><span class="kicker">Facts checked ${esc(fmtDate(c.as_of, {day: 'numeric', month: 'short', year: 'numeric'}))}</span></div>
      <p class="note" style="margin:0 0 var(--s-4)">${esc(c.written_by)}.</p>
      <ol class="src-list">${c.sources.map((s, i) => `<li id="src-${i + 1}"><span class="mono">${i + 1}</span><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)} ↗</a></li>`).join('')}</ol>
    </section>`;
}

// Indicator cards in the country monitors' format: value, small trend line, year and source.
function figureStrip(cards) {
  return `<section class="struct-strip fig-strip" aria-label="Key figures" style="--n:${cards.length}">${cards.map(f => `
    <div class="sstat"><div class="l">${esc(f.label)}</div><div class="sstat-v"><span class="v">${esc(f.value)}</span>${f.series ? lineSpark(f.series, 72, 24) : ''}</div>
      <div class="y">${esc(f.year)}${f.source != null ? ` · source ${cite([f.source])}` : f.from ? ` · ${esc(f.from)}` : ''}</div>${f.note ? `<div class="y med">${esc(f.note)}</div>` : ''}</div>`).join('')}</section>`;
}

// A region-wide reading of one risk construct, in the instrument register of the country outlook panel.
function regionReading(model, ctx, code, {title, question}) {
  const read = model.countries.map(c => ({c, k: c.constructs.find(k => k.code === code)})).filter(r => r.k?.level);
  const counts = LEVELS.map(l => [l, read.filter(r => r.k.level === l).length]);
  const top = read.filter(r => ['severe', 'high'].includes(r.k.level)).sort((a, b) => LEVELS.indexOf(b.k.level) - LEVELS.indexOf(a.k.level) || (b.k.trend === 'rising') - (a.k.trend === 'rising'));
  const rising = read.filter(r => /^ris|^up|^wors/.test(r.k.trend || ''));
  const seen = new Set();
  const evidence = top.flatMap(r => r.k.evidence.slice(0, 1).map(e => ({e, c: r.c}))).filter(({e}) => !seen.has(e.id) && seen.add(e.id)).slice(0, 4);
  const max = Math.max(1, ...counts.map(([, n]) => n));
  return `
  <section class="outlook instr" aria-label="${esc(title)}">
    <div class="outlook-grid">
      <div class="ol-main">
        <div class="panel-title"><span>${esc(title)}</span><span class="mono">country risk model</span></div>
        <div class="ol-level" style="font-size:38px;text-transform:none">${top.length} of ${read.length}</div>
        <div style="font-size:13px;color:var(--i-dim)">${esc(question)} ${rising.length ? `Rising in ${rising.length}.` : ''}</div>
        <div class="lvl-dist">${counts.map(([l, n]) => `<div><span class="mono">${l}</span><span class="bar"><i style="width:${(n / max * 100).toFixed(0)}%"></i></span><b class="mono">${n}</b></div>`).join('')}</div>
        <div class="withheld">Shown as levels. Numeric scores are withheld until the model is validated.</div>
      </div>
      <div class="rr-right">
        <div class="kicker" style="margin-bottom:8px">Severe and high</div>
        <ul class="rr-list">${top.map(r => `<li><a href="${countryUrl(ctx, r.c)}">${esc(r.c.name)}</a>${lvl(r.k.level)}${dir(r.k.trend)}</li>`).join('') || '<li>None at present.</li>'}</ul>
        ${evidence.length ? `<div class="con-ev"><div class="kicker">Events behind these readings · past 90 days</div>${evidence.map(({e, c}) => `
          <a href="${eventUrl(ctx, e.id)}"><span class="mono">${fmtDate(e.date, {day: 'numeric', month: 'short'})} · ${esc(c.iso3)}</span>${esc(e.title)}</a>`).join('')}</div>` : ''}
      </div>
    </div>
  </section>`;
}

// Text on the left; its chart or table beside it, so the page reads like a feature, not a column.
function editorialSection(sec, extra = '') {
  const table = sec.table ? `<div class="tbl-scroll"><table class="tbl"><thead><tr>${sec.table.head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead>
        <tbody>${sec.table.rows.map(r => `<tr>${r.map((v, i) => `<td${i === 1 ? ' class="strong"' : ''}>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
        <p class="note">Sources ${cite(sec.table.source)}</p>` : '';
  const aside = table + extra;
  return `
    <article class="ed-sec${aside ? ' has-aside' : ''}" id="${esc(sec.id)}">
      <div class="ed-main"><div class="kicker">${esc(sec.kicker)}</div>
        <h3>${esc(sec.title)}</h3>
        <div class="prose">${sec.paras.map(para).join('')}</div></div>
      ${aside ? `<div class="ed-aside">${aside}</div>` : ''}
    </article>`;
}

/* ───────────── Organized crime ───────────── */

function cocaChart(f) {
  const years = Array.from({length: f.series.length}, (_, i) => 2024 - f.series.length + 1 + i);
  const W = 420, H = 150, L = 30, B = 22, T = 14, peak = Math.max(...f.series) * 1.08, slot = (W - L) / years.length, bw = slot * .6;
  const y = v => T + (H - T - B) * (1 - v / peak);
  return `<figure class="ed-fig"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`Coca cultivated in Colombia, thousand hectares: ${years.map((yr, i) => `${yr} ${f.series[i]}`).join(', ')}`)}">
    <line x1="${L}" x2="${W}" y1="${H - B}" y2="${H - B}" stroke="var(--rule)"/>
    ${years.map((yr, i) => { const x = L + i * slot + (slot - bw) / 2, v = f.series[i]; return `<g><rect x="${x.toFixed(1)}" y="${y(v).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H - B - y(v)).toFixed(1)}" fill="var(--t-oc)" fill-opacity="${i === years.length - 1 ? 1 : .55}"/><text x="${(x + bw / 2).toFixed(1)}" y="${(y(v) - 4).toFixed(1)}" text-anchor="middle">${v}</text><text x="${(x + bw / 2).toFixed(1)}" y="${H - 7}" text-anchor="middle">${yr}</text></g>`; }).join('')}
  </svg><figcaption>Coca cultivated in Colombia, thousand hectares. Colombia–UNODC monitoring surveys ${cite([0, 1])}</figcaption></figure>`;
}

function frontlines(content, model, ctx) {
  return `<div class="fronts">${content.frontlines.map(f => {
    const c = model.byName[f.country];
    if (!c) return '';
    const frag = c.constructs.find(k => k.code === 'security_fragmentation');
    return `<a class="front" href="${countryUrl(ctx, c)}"><div class="kicker">Frontline · ${esc(c.iso3)}</div><h3>${esc(c.name)}</h3><p>${esc(f.text)}</p>
      <div class="front-foot">${chip(c)}${frag ? lvl(frag.level, '--amber') : ''}</div></a>`;
  }).join('')}</div>`;
}

export function renderOrganizedCrime(model, ctx) {
  const content = model.topics.oc;
  const isOc = e => e.content_type === 'event' && (e.type === 'oc' || (e.type === 'conflict' && [e.actor, e.target].includes('armed_non_state_actor')));
  const year = model.events.filter(e => isOc(e) && within(model, e, 365));
  const recent = year.filter(e => within(model, e, 30)).sort((a, b) => SAL[a.sal] - SAL[b.sal] || b.date.localeCompare(a.date));
  const map = regionMap(model, year, 'Organized crime and armed-group events, past 12 months');
  const rows = model.countries.map(c => {
    const evs = year.filter(e => e.country === c.name), frag = c.constructs.find(k => k.code === 'security_fragmentation');
    return {c, n: evs.length, n30: evs.filter(e => within(model, e, 30)).length, high: evs.filter(e => e.sal === 'high').length, frag};
  }).filter(r => r.n || r.frag).sort((a, b) => b.n - a.n);
  const groups = {};
  for (const e of year) for (const a of e.coding?.actors || []) if (['criminal_org', 'insurgent_group', 'paramilitary_militia'].includes(a.group) && a.name) {
    const g = (groups[a.name] ||= {n: 0, countries: new Set()}); g.n++; g.countries.add(e.country);
  }
  const named = Object.entries(groups).filter(([, g]) => g.n >= 2).sort((a, b) => b[1].n - a[1].n).slice(0, 12);
  const coded = year.filter(e => e.coding).length;
  const coca = content?.figures.find(f => f.series);
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>Organized crime</span></div>
    <section class="c-head" style="align-items:start">
      <div><div class="kicker">Topic monitor · ${model.countries.length} countries</div><h1 style="margin-top:8px;font-size:clamp(38px,5vw,64px)">Organized crime and the state</h1>
        <p class="dek">${esc(content?.lede || 'SENTINEL treats organized crime as a force inside civil–military relations, not as a separate crime beat.')}</p></div>
      <dl class="facts">
        <dt>Events, 12 months</dt><dd class="mono">${year.length}</dd>
        <dt>Past 30 days</dt><dd class="mono">${recent.length}${recent.filter(e => e.sal === 'high').length ? ` · ${recent.filter(e => e.sal === 'high').length} high salience` : ''}</dd>
        <dt>Countries</dt><dd class="mono">${new Set(year.map(e => e.country)).size}</dd>
        <dt>What counts</dt><dd>Events coded as organized crime, and armed-conflict events that involve a non-state armed actor.</dd>
      </dl>
    </section>
    ${content ? figureStrip(content.figures) : ''}
    ${regionReading(model, ctx, 'security_fragmentation', {title: 'Security fragmentation across the region', question: 'Countries where the model reads criminal and armed-group pressure on the state as high or severe.'})}
    <div class="two section" style="padding-top:var(--s-6)">
      <div>
        <div class="sec-head"><h2>By country</h2><span class="kicker">Past 12 months</span></div>
        <div class="tbl-scroll"><table class="tbl">
          <thead><tr><th>Country</th><th class="num">Events</th><th class="num">30 days</th><th class="num">High</th><th>Security fragmentation</th><th>Direction</th></tr></thead>
          <tbody>${rows.map(r => `<tr><td><a href="${countryUrl(ctx, r.c)}">${esc(r.c.name)}</a></td><td class="num mono">${r.n || '—'}</td><td class="num mono">${r.n30 || '—'}</td><td class="num mono">${r.high || '—'}</td><td>${r.frag ? lvl(r.frag.level, '--amber') : '—'}</td><td>${r.frag ? dir(r.frag.trend) : ''}</td></tr>`).join('')}</tbody>
        </table></div>
        <p class="note">Security fragmentation is a reading from the country risk model, shown as a level; numeric scores are withheld until the model is validated. ${COLLECTION_NOTE}</p>
        <div class="sec-head section"><h2>Events per month</h2><span class="kicker">Region</span></div>
        <div class="act-chart">${monthBars(monthsOf(year, model.asof), 'var(--t-oc)')}</div>
        <div class="sec-head section"><h2>Past 30 days</h2><a href="${ctx.url('feed/?t=oc&p=30')}">Organized-crime events in the feed →</a></div>
        ${storyList(recent, model, ctx, 12)}
      </div>
      <aside>
        <div class="sec-head"><h2>Where</h2><span class="kicker">Past 12 months</span></div>
        <div class="cmap instr">${map.svg}</div>
        <p class="note">${map.n} of ${year.length} events are placed at a town or region (${map.places} places). Red marks include a high-salience event. Country-level events are not drawn.</p>
        ${content ? `<div class="sec-head section"><h2>Frontlines</h2></div>${frontlines(content, model, ctx)}` : ''}
        ${named.length >= 5 ? `<div class="sec-head section"><h2>Groups named most often</h2></div>
        <ul class="missions">${named.map(([name, g]) => `<li><span>${esc(name)}<small class="grp-c">${esc([...g.countries].join(', '))}</small></span><span class="mono">${g.n}</span></li>`).join('')}</ul>
        <p class="note">Names as written by the coder in ${coded} of ${year.length} events (those coded since October 2026). Spelling variants are not merged, so counts are a floor.</p>` : ''}
      </aside>
    </div>
    ${content ? `
    <section class="section ed" aria-labelledby="bg-h">
      <div class="sec-head"><h2 id="bg-h">Background</h2>${byline(content)}</div>
      ${editorialSection(content.sections[0], coca ? cocaChart(coca) : '')}
      ${content.sections.slice(1).map(s => editorialSection(s)).join('')}
    </section>
    ${sourceList(content)}` : ''}
  </div>`;
  return layout(ctx, {title: 'Organized crime and the state', description: `Organized crime and armed-group events across ${model.countries.length} countries: ${year.length} in the past 12 months, with security-fragmentation readings, sourced background and US terrorist designations.`, nav: 'oc', body});
}

/* ───────────── US security ───────────── */

const US_WORDS = /(?<![\w])(US|U\.S\.|United States|EE\.? ?UU\.?|Estados Unidos|EUA|SOUTHCOM|Southern Command|Comando Sur|Pentagon|Pentágono|DEA|JIATF)(?![\w])/;
const US_TYPES = new Set(['aid', 'coop', 'exercise', 'procurement']);

// Short names for the funding accounts that carry security assistance.
const ACCOUNT = [
  [/^International Narcotics Control/, 'INCLE', 'Narcotics control and law enforcement (State)'],
  [/^Foreign Military Financing/, 'FMF', 'Foreign Military Financing (State)'],
  [/^Nonproliferation, Anti-Terrorism/, 'NADR', 'Anti-terrorism, demining and nonproliferation (State)'],
  [/^International Military Education/, 'IMET', 'Officer education and training (State)'],
  [/^Peace ?Keeping Operations/, 'PKO', 'Peacekeeping operations (State)'],
  [/^Excess Defense Articles/, 'EDA', 'Surplus equipment transfers'],
  [/Andean Counterdrug/, 'ACP', 'Andean Counterdrug Programs (State, ended)'],
  [/Drug Interdiction and Counter-Drug/, 'DoD CN', 'Defense counter-drug activities'],
  [/Operation and Maintenance, Defense-Wide/, 'DoD O&M', 'Defense-wide operations, incl. Section 333 train-and-equip'],
];
const accountName = name => { const hit = ACCOUNT.find(([re]) => re.test(name)); return hit ? [hit[1], hit[2]] : ['', name.replace(/^Department of (Defense|the Army|the Navy|the Air Force), /, '$1: ')]; };

function channelTable(model, ctx, full) {
  const aid = model.assistance;
  if (!aid?.countries?.[0]?.security_accounts) return '';
  const acc = {};
  for (const c of aid.countries) for (const a of c.security_accounts) {
    const r = (acc[a.account] ||= {account: a.account, group: a.group, now: 0, prev: 0, by: {}});
    const now = Math.max(0, a.years[String(full)] || 0), prev = Math.max(0, a.years[String(full - 1)] || 0);
    r.now += now; r.prev += prev;
    if (now) r.by[c.country] = (r.by[c.country] || 0) + now;
  }
  const rows = Object.values(acc).filter(r => r.now >= 2e6 || r.prev >= 2e6).sort((a, b) => b.now - a.now || b.prev - a.prev).slice(0, 9);
  return `
        <div class="sec-head section"><h2>By funding channel</h2><span class="kicker">Fiscal ${full - 1} and ${full}</span></div>
        <div class="tbl-scroll"><table class="tbl">
          <thead><tr><th>Channel</th><th class="num">FY${full - 1}</th><th class="num">FY${full}</th><th>Largest recipients, FY${full}</th></tr></thead>
          <tbody>${rows.map(r => { const [abbr, label] = accountName(r.account); const top = Object.entries(r.by).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([c, v]) => { const m = model.byName[c]; return `${m ? `<a href="${countryUrl(ctx, m)}">${esc(c)}</a>` : esc(c)} ${usd(v)}`; }).join(', '); return `<tr><td>${abbr ? `<b class="mono">${esc(abbr)}</b> ` : ''}${esc(label)}<small class="grp-c">${r.group === 'military' ? 'military' : 'counternarcotics'}</small></td><td class="num mono">${r.prev ? usd(r.prev) : '—'}</td><td class="num mono">${r.now ? usd(r.now) : '—'}</td><td style="font-size:13px">${top || '—'}</td></tr>`; }).join('')}</tbody>
        </table></div>
        <p class="note">${esc(model.topics.us?.channels_note || '')} Obligations to the ${model.countries.length} monitored countries, constant dollars; Defense Department accounts are reported with a lag and may show nothing for the latest year. Source: ForeignAssistance.gov.</p>`;
}

// Long-run Greenbook history, economic and military obligations to the monitored countries.
function greenbookHistory(model, ctx) {
  const g = model.greenbook;
  if (!g) return '';
  const norm = n => n.replace(' & ', ' and ');
  const years = {};
  for (const c of g.countries) for (const p of c.series) { const r = (years[p.year] ||= {year: p.year, economic: 0, military: 0}); r.economic += p.economic; r.military += p.military; }
  const series = Object.values(years).filter(p => p.economic + p.military > 0).sort((a, b) => a.year - b.year);
  const first = series[0].year, last = series.at(-1).year;
  const total = series.reduce((a, p) => a + p.economic + p.military, 0), mil = series.reduce((a, p) => a + p.military, 0);
  const W = 960, H = 220, L = 50, B = 24, T = 18, peak = Math.max(...series.map(p => p.economic + p.military));
  const step = [1e9, 2e9, 2.5e9, 5e9].find(s => peak / s <= 4) || 1e10, top = Math.ceil(peak / step) * step;
  const y = v => T + (H - T - B) * (1 - v / top), slot = (W - L) / series.length, bw = Math.max(1, slot * .72);
  const grid = Array.from({length: top / step + 1}, (_, i) => i * step).map(v => `<line x1="${L}" x2="${W}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="var(--rule-2)"/><text x="${L - 6}" y="${y(v).toFixed(1)}" dy=".32em" text-anchor="end">${v ? usd(v) : '0'}</text>`).join('');
  const marks = {1962: 'Alliance for Progress', 1985: 'Central American wars', 2000: 'Plan Colombia', 2010: 'Haiti earthquake'};
  const bars = series.map((p, i) => {
    const x = L + i * slot + (slot - bw) / 2;
    return `<g><title>${esc(`FY${p.year}: economic ${usd(p.economic)}, military ${usd(p.military)}`)}</title>
      <rect x="${x.toFixed(1)}" y="${y(p.economic + p.military).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y(p.economic) - y(p.economic + p.military)).toFixed(1)}" fill="var(--t-aid)"/>
      <rect x="${x.toFixed(1)}" y="${y(p.economic).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H - B - y(p.economic)).toFixed(1)}" fill="var(--ink-3)" fill-opacity=".55"/>
      ${p.year % 10 === 0 ? `<text x="${(x + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${p.year}</text>` : ''}
      ${marks[p.year] ? `<text class="mk" x="${(x + bw / 2).toFixed(1)}" y="${(y(p.economic + p.military) - 6).toFixed(1)}" text-anchor="middle">${marks[p.year]}</text>` : ''}</g>`;
  }).join('');
  const ranked = g.countries.map(c => ({name: norm(c.country), total: c.total_all_years, mil: c.total_military, peak: c.peak_year})).sort((a, b) => b.total - a.total).slice(0, 10);
  return `
    <section class="section" aria-labelledby="hist-h">
      <div class="sec-head"><h2 id="hist-h">Seventy years of US assistance</h2><span class="kicker">FY${first}–${last} · constant dollars</span></div>
      <div class="hist-grid">
        <div>
          <div class="act-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`US economic and military assistance to the monitored countries by fiscal year, ${first} to ${last}`)}">${grid}${bars}</svg></div>
          <div class="aid-legend"><span><i style="background:var(--t-aid)"></i>Military</span><span><i style="background:var(--ink-3);opacity:.55"></i>Economic, including narcotics control</span></div>
          <p class="note">${usd(total)} in total to the ${g.countries.length} monitored countries, ${(mil / total * 100).toFixed(0)}% of it military. The USAID Greenbook counts narcotics-control funding as economic aid, which understates the security share; the current series above groups it with security. The file has no data after fiscal ${last}. Source: USAID Greenbook.</p>
        </div>
        <div class="tbl-scroll"><table class="tbl">
          <thead><tr><th>Largest recipients</th><th class="num">Total</th><th class="num">Military</th><th class="num">Peak year</th></tr></thead>
          <tbody>${ranked.map(r => { const m = model.byName[r.name]; return `<tr><td>${m ? `<a href="${countryUrl(ctx, m)}">${esc(r.name)}</a>` : esc(r.name)}</td><td class="num mono">${usd(r.total)}</td><td class="num mono">${usd(r.mil)} <small>${(r.mil / r.total * 100).toFixed(0)}%</small></td><td class="num mono">${r.peak}</td></tr>`; }).join('')}</tbody>
        </table></div>
      </div>
    </section>`;
}

function caribbean(content) {
  const k = content.caribbean;
  const month = d => fmtDate(d + '-01', {month: 'short', year: 'numeric'});
  return `
    <section class="section ed focus" aria-labelledby="car-h">
      <div class="sec-head"><h2 id="car-h">${esc(k.title)}</h2><span class="kicker">${esc(k.kicker)}</span></div>
      <div class="focus-grid">
        <div>
          <div class="prose">${para(k.intro)}</div>
          <div class="assess instr"><div class="panel-title"><span>SENTINEL assessment</span><span class="mono">analysis</span></div>${para(k.assessment)}</div>
        </div>
        <ol class="ed-tl">${k.timeline.map(t => `<li><span class="mono">${month(t.date)}</span><div><b>${esc(t.title)}</b><p>${esc(t.text)}${cite(t.sources)}</p></div></li>`).join('')}</ol>
      </div>
    </section>`;
}

export function renderUsSecurity(model, ctx) {
  const content = model.topics.us;
  const mentions = e => US_WORDS.test(`${e.title} ${e.summary}`) || (e.coding?.actors || []).some(a => /United States|U\.S\.|Estados Unidos|\bUS\b/.test(a.name || ''));
  const isUs = e => e.content_type === 'event' && mentions(e) && (US_TYPES.has(e.type) || e.coding?.subtype === 'direct_foreign_operation' || (e.sal === 'high' && US_WORDS.test(e.title)));
  const year = model.events.filter(e => isUs(e) && within(model, e, 365));
  const recent = year.filter(e => within(model, e, 60)).sort((a, b) => SAL[a.sal] - SAL[b.sal] || b.date.localeCompare(a.date));
  const aid = model.assistance;
  let aidBlock = '', table = '', channels = '', cards = content ? [...content.figures] : [];
  if (aid) {
    const years = Array.from({length: 12}, (_, i) => aid.last_year - 11 + i);
    const region = years.map(y => { const p = {year: y}; for (const [g] of AID_GROUPS) p[g] = aid.countries.reduce((a, c) => a + Math.max(0, c.series.find(s => s.year === y)?.[g] || 0), 0); return p; });
    const full = [...years].reverse().find(y => !aid.partial_years.includes(y));
    const security = p => Math.max(0, p.military) + Math.max(0, p.counternarcotics);
    const ranked = aid.countries.map(c => ({c: model.byName[c.country], now: c.series.find(s => s.year === full), then: c.series.find(s => s.year === full - 5)}))
      .filter(r => r.c && r.now && r.now.total > 0).sort((a, b) => security(b.now) - security(a.now));
    const regionFull = region.find(p => p.year === full);
    const secSeries = region.filter(p => !aid.partial_years.includes(p.year)).map(security);
    cards = [{label: 'US security assistance', value: usd(security(regionFull)), year: `FY${full}`, from: 'ForeignAssistance.gov', series: secSeries.map(v => v / 1e6), note: `military and counternarcotics, ${years[0]}–${full}`}, ...cards];
    aidBlock = `
        <div class="sec-head"><h2>US assistance to the region</h2><span class="kicker">FY${years[0]}–${years.at(-1)}</span></div>
        <div class="aid-chart">${aidBars(region, aid.partial_years, 640, 190)}</div>
        <div class="aid-legend" style="max-width:420px">${AID_GROUPS.map(([g, label, color]) => `<span><i style="background:${color}"></i>${label} <b class="mono">${usd(regionFull[g])}</b></span>`).join('')}</div>
        <p class="note">Obligations to the ${model.countries.length} monitored countries in constant dollars; figures beside the legend are fiscal ${full}. ${aid.partial_years.length ? `Fiscal ${aid.partial_years.join(' and ')} (lighter) is incomplete. ` : ''}Grouped by funding account by SENTINEL. Source: ForeignAssistance.gov.</p>`;
    channels = channelTable(model, ctx, full);
    table = `
        <div class="sec-head section"><h2>Security assistance by country</h2><span class="kicker">Fiscal ${full}</span></div>
        <div class="tbl-scroll"><table class="tbl">
          <thead><tr><th>Country</th><th class="num">Military</th><th class="num">Counternarcotics</th><th class="num">Economic</th><th class="num">Security, FY${full - 5}</th></tr></thead>
          <tbody>${ranked.map(r => `<tr><td><a href="${countryUrl(ctx, r.c)}">${esc(r.c.name)}</a></td><td class="num mono">${usd(Math.max(0, r.now.military))}</td><td class="num mono">${usd(Math.max(0, r.now.counternarcotics))}</td><td class="num mono">${usd(Math.max(0, r.now.other))}</td><td class="num mono">${r.then ? usd(security(r.then)) : '—'}</td></tr>`).join('')}</tbody>
        </table></div>
        <p class="note">Ranked by military plus counternarcotics obligations in fiscal ${full}. The last column is the same sum five years earlier.</p>`;
  }
  const align = model.countries.map(c => ({c, m: c.monitors.find(m => m.code === 'external_security_alignment'), n: year.filter(e => e.country === c.name).length}))
    .filter(r => r.n).sort((a, b) => b.n - a.n).slice(0, 12);
  const access = content?.access;
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>US security</span></div>
    <section class="c-head" style="align-items:start">
      <div><div class="kicker">Topic monitor · ${model.countries.length} countries</div><h1 style="margin-top:8px;font-size:clamp(38px,5vw,64px)">US security in the region</h1>
        <p class="dek">${esc(content?.lede || 'US involvement in the region\'s civil–military relations runs through aid, officer training, basing and logistics, counternarcotics deployments, and at times direct action.')}</p></div>
      <dl class="facts">
        <dt>Events, 12 months</dt><dd class="mono">${year.length}</dd>
        <dt>Past 60 days</dt><dd class="mono">${recent.length}</dd>
        <dt>Countries</dt><dd class="mono">${new Set(year.map(e => e.country)).size}</dd>
        <dt>What counts</dt><dd>Events that name the United States or a US agency and are coded as aid, cooperation, exercise, procurement or a direct foreign operation, plus high-salience events that name it in the headline. Matched automatically.</dd>
      </dl>
    </section>
    ${cards.length ? figureStrip(cards) : ''}
    ${content ? caribbean(content) : ''}
    <div class="two section" style="padding-top:var(--s-6)">
      <div>
        ${aidBlock}${channels}${table}
        <div class="sec-head section"><h2>Past 60 days</h2><a href="${ctx.url('feed/?t=coop&p=90')}">Security cooperation in the feed →</a></div>
        ${storyList(recent, model, ctx, 14)}
      </div>
      <aside>
        <div class="sec-head"><h2>Events per month</h2><span class="kicker">Region</span></div>
        <div class="act-chart tight">${monthBars(monthsOf(year, model.asof), 'var(--t-coop)')}</div>
        <p class="note">${COLLECTION_NOTE}</p>
        <div class="sec-head section"><h2>Where the events are</h2><span class="kicker">Past 12 months</span></div>
        <ul class="missions">${align.map(r => `<li><span><a href="${countryUrl(ctx, r.c)}" style="text-decoration:none">${esc(r.c.name)}</a>${r.m?.trend ? `<small class="grp-c">external alignment: ${esc(r.m.trend)}</small>` : ''}</span><span class="mono">${r.n}</span></li>`).join('')}</ul>
        <p class="note">Events involving the United States, by country. "External alignment" is the trend of the country monitor that tracks foreign security ties.</p>
        ${access ? `<div class="sec-head section"><h2>${esc(access.title)}</h2></div>
        <ul class="missions access">${access.rows.map(([site, where, role, status]) => `<li><span>${esc(site)}<small class="grp-c">${esc(where)} · ${esc(role)}</small></span><span class="mono ms-${/^Active|^React/.test(status) ? 'active' : 'routine'}">${esc(status)}</span></li>`).join('')}</ul>
        <p class="note">${esc(access.note)} Sources ${cite(access.sources)}</p>` : ''}
      </aside>
    </div>
    ${greenbookHistory(model, ctx)}
    ${content ? sourceList(content) : ''}
  </div>`;
  return layout(ctx, {title: 'US security in the region', description: `US security assistance, the 2025–26 Caribbean campaign and US-related security events across ${model.countries.length} countries in Latin America and the Caribbean.`, nav: 'us', body});
}
