// Topic pages: organized crime and US security. Both are computed from the published
// events and the structural layer; the framing paragraph on each is written by hand.

import {esc, fmtDate, tColor, tLabel, lvl, dir, daysBetween, usd, aidBars, AID_GROUPS} from '../lib/html.mjs';
import {layout} from './layout.mjs';
import {regionMap} from './maps.mjs';
import {eventUrl} from './event.mjs';

const countryUrl = (ctx, c) => ctx.url(`countries/${c.iso3.toLowerCase()}/`);
const within = (model, e, d) => { const n = daysBetween(model.asof, e.date); return n >= 0 && n <= d; };
const SAL = {high: 0, medium: 1, low: 2};

function eventList(events, model, ctx, n) {
  if (!events.length) return '<p class="note">No matching events in this period.</p>';
  return `<div class="cevents">${events.slice(0, n).map(e => `
    <div class="cev"><span class="d">${fmtDate(e.date, {day: 'numeric', month: 'short'})}</span><span class="b" style="background:${tColor(e.type)}"></span>
      <div><a href="${eventUrl(ctx, e.id)}" style="text-decoration:none">${esc(e.title)}</a><small>${esc(e.country)} · ${tLabel(e.type)} · ${e.sal} salience · ${e.n_sources} source${e.n_sources > 1 ? 's' : ''}</small></div></div>`).join('')}</div>`;
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
const COLLECTION_NOTE = 'Counts reflect how much was collected as well as what happened: collection started in March 2026 and was irregular until October 2026, and earlier dates come from archive searches.';

/* ───────────── Organized crime ───────────── */

export function renderOrganizedCrime(model, ctx) {
  const isOc = e => e.content_type === 'event' && (e.type === 'oc' || (e.type === 'conflict' && [e.actor, e.target].includes('armed_non_state_actor')));
  const year = model.events.filter(e => isOc(e) && within(model, e, 365));
  const recent = year.filter(e => within(model, e, 30)).sort((a, b) => SAL[a.sal] - SAL[b.sal] || b.date.localeCompare(a.date));
  const map = regionMap(model, year, 'Organized crime and armed-group events, past 12 months');
  const rows = model.countries.map(c => {
    const evs = year.filter(e => e.country === c.name), frag = c.constructs.find(k => k.code === 'security_fragmentation');
    return {c, n: evs.length, n30: evs.filter(e => within(model, e, 30)).length, high: evs.filter(e => e.sal === 'high').length, frag, last: evs[0]?.date};
  }).filter(r => r.n || r.frag).sort((a, b) => b.n - a.n);
  const groups = {};
  for (const e of year) for (const a of e.coding?.actors || []) if (['criminal_org', 'insurgent_group', 'paramilitary_militia'].includes(a.group) && a.name) {
    const g = (groups[a.name] ||= {n: 0, countries: new Set()}); g.n++; g.countries.add(e.country);
  }
  const named = Object.entries(groups).filter(([, g]) => g.n >= 2).sort((a, b) => b[1].n - a[1].n).slice(0, 12);
  const coded = year.filter(e => e.coding).length;
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>Organized crime</span></div>
    <section class="c-head" style="align-items:start">
      <div><div class="kicker">Topic monitor · ${model.countries.length} countries</div><h1 style="margin-top:8px;font-size:clamp(38px,5vw,64px)">Organized crime and the state</h1>
        <p style="margin:14px 0 0;color:var(--ink-2);max-width:62ch">SENTINEL treats organized crime as a force inside civil–military relations, not as a separate crime beat. The question is where illicit economies are changing who governs, who coerces, and who bargains with force: military deployments against cartels, gang control of territory and prisons, and criminal capture of police and officials.</p></div>
      <dl class="facts">
        <dt>Events, 12 months</dt><dd class="mono">${year.length}</dd>
        <dt>Past 30 days</dt><dd class="mono">${recent.length}${recent.filter(e => e.sal === 'high').length ? ` · ${recent.filter(e => e.sal === 'high').length} high salience` : ''}</dd>
        <dt>Countries</dt><dd class="mono">${new Set(year.map(e => e.country)).size}</dd>
        <dt>What counts</dt><dd>Events coded as organized crime, and armed-conflict events that involve a non-state armed actor.</dd>
      </dl>
    </section>
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
        ${eventList(recent, model, ctx, 12)}
      </div>
      <aside>
        <div class="sec-head"><h2>Where</h2><span class="kicker">Past 12 months</span></div>
        <div class="cmap instr">${map.svg}</div>
        <p class="note">${map.n} of ${year.length} events are placed at a town or region (${map.places} places). Red marks include a high-salience event. Country-level events are not drawn.</p>
        ${named.length >= 5 ? `<div class="sec-head section"><h2>Groups named most often</h2></div>
        <ul class="missions">${named.map(([name, g]) => `<li><span>${esc(name)}<small class="grp-c">${esc([...g.countries].join(', '))}</small></span><span class="mono">${g.n}</span></li>`).join('')}</ul>
        <p class="note">Names as written by the coder in ${coded} of ${year.length} events (those coded since October 2026). Spelling variants are not merged, so counts are a floor.</p>` : ''}
        <div class="sec-head section"><h2>Background</h2></div>
        <p style="font-size:14px;color:var(--ink-2);margin:0">The longer essay on cocaine, fentanyl, illicit mining and transnational gangs is still on the <a href="${ctx.legacy}#transnational">current site</a> until it is revised.</p>
      </aside>
    </div>
  </div>`;
  return layout(ctx, {title: 'Organized crime and the state', description: `Organized crime and armed-group events across ${model.countries.length} countries: ${year.length} in the past 12 months, with security-fragmentation readings by country.`, nav: 'oc', body});
}

/* ───────────── US security ───────────── */

const US_WORDS = /(?<![\w])(US|U\.S\.|United States|EE\.? ?UU\.?|Estados Unidos|EUA|SOUTHCOM|Southern Command|Comando Sur|Pentagon|Pentágono|DEA|JIATF)(?![\w])/;
const US_TYPES = new Set(['aid', 'coop', 'exercise', 'procurement']);

export function renderUsSecurity(model, ctx) {
  const mentions = e => US_WORDS.test(`${e.title} ${e.summary}`) || (e.coding?.actors || []).some(a => /United States|U\.S\.|Estados Unidos|\bUS\b/.test(a.name || ''));
  const isUs = e => e.content_type === 'event' && mentions(e) && (US_TYPES.has(e.type) || e.coding?.subtype === 'direct_foreign_operation' || (e.sal === 'high' && US_WORDS.test(e.title)));
  const year = model.events.filter(e => isUs(e) && within(model, e, 365));
  const recent = year.filter(e => within(model, e, 60)).sort((a, b) => SAL[a.sal] - SAL[b.sal] || b.date.localeCompare(a.date));
  const aid = model.assistance;
  let aidBlock = '', table = '';
  if (aid) {
    const years = Array.from({length: 12}, (_, i) => aid.last_year - 11 + i);
    const region = years.map(y => { const p = {year: y}; for (const [g] of AID_GROUPS) p[g] = aid.countries.reduce((a, c) => a + Math.max(0, c.series.find(s => s.year === y)?.[g] || 0), 0); return p; });
    const full = [...years].reverse().find(y => !aid.partial_years.includes(y));
    const security = p => Math.max(0, p.military) + Math.max(0, p.counternarcotics);
    const ranked = aid.countries.map(c => ({c: model.byName[c.country], now: c.series.find(s => s.year === full), then: c.series.find(s => s.year === full - 5)}))
      .filter(r => r.c && r.now && r.now.total > 0).sort((a, b) => security(b.now) - security(a.now));
    const regionFull = region.find(p => p.year === full);
    aidBlock = `
        <div class="sec-head"><h2>US assistance to the region</h2><span class="kicker">FY${years[0]}–${years.at(-1)}</span></div>
        <div class="aid-chart">${aidBars(region, aid.partial_years, 640, 190)}</div>
        <div class="aid-legend" style="max-width:420px">${AID_GROUPS.map(([g, label, color]) => `<span><i style="background:${color}"></i>${label} <b class="mono">${usd(regionFull[g])}</b></span>`).join('')}</div>
        <p class="note">Obligations to the ${model.countries.length} monitored countries in constant dollars; figures beside the legend are fiscal ${full}. ${aid.partial_years.length ? `Fiscal ${aid.partial_years.join(' and ')} (lighter) is incomplete. ` : ''}Grouped by funding account by SENTINEL: military is Foreign Military Financing, IMET, peacekeeping, excess defense articles and all Defense Department accounts; counternarcotics is State Department narcotics control and anti-terrorism funding. Source: ForeignAssistance.gov.</p>`;
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
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>US security</span></div>
    <section class="c-head" style="align-items:start">
      <div><div class="kicker">Topic monitor · ${model.countries.length} countries</div><h1 style="margin-top:8px;font-size:clamp(38px,5vw,64px)">US security in the region</h1>
        <p style="margin:14px 0 0;color:var(--ink-2);max-width:62ch">US involvement in the region's civil–military relations runs through aid, officer training, basing and logistics, counternarcotics deployments, and at times direct action. This page reads them together: what Washington funds, and what the coded events show it doing.</p></div>
      <dl class="facts">
        <dt>Events, 12 months</dt><dd class="mono">${year.length}</dd>
        <dt>Past 60 days</dt><dd class="mono">${recent.length}</dd>
        <dt>Countries</dt><dd class="mono">${new Set(year.map(e => e.country)).size}</dd>
        <dt>What counts</dt><dd>Events that name the United States or a US agency and are coded as aid, cooperation, exercise, procurement or a direct foreign operation, plus high-salience events that name it in the headline. Matched automatically.</dd>
      </dl>
    </section>
    <div class="two section" style="padding-top:var(--s-6)">
      <div>
        ${aidBlock}${table}
        <div class="sec-head section"><h2>Past 60 days</h2><a href="${ctx.url('feed/?t=coop&p=90')}">Security cooperation in the feed →</a></div>
        ${eventList(recent, model, ctx, 14)}
      </div>
      <aside>
        <div class="sec-head"><h2>Events per month</h2><span class="kicker">Region</span></div>
        <div class="act-chart tight">${monthBars(monthsOf(year, model.asof), 'var(--t-coop)')}</div>
        <p class="note">${COLLECTION_NOTE}</p>
        <div class="sec-head section"><h2>Where the events are</h2><span class="kicker">Past 12 months</span></div>
        <ul class="missions">${align.map(r => `<li><span><a href="${countryUrl(ctx, r.c)}" style="text-decoration:none">${esc(r.c.name)}</a>${r.m?.trend ? `<small class="grp-c">external alignment: ${esc(r.m.trend)}</small>` : ''}</span><span class="mono">${r.n}</span></li>`).join('')}</ul>
        <p class="note">Events involving the United States, by country. "External alignment" is the trend of the country monitor that tracks foreign security ties.</p>
        <div class="sec-head section"><h2>Background</h2></div>
        <p style="font-size:14px;color:var(--ink-2);margin:0">The longer account of the 2025–26 Caribbean operations, basing and detention is still on the <a href="${ctx.legacy}#us">current site</a> until it is revised.</p>
      </aside>
    </div>
  </div>`;
  return layout(ctx, {title: 'US security in the region', description: `US security assistance and US-related security events across ${model.countries.length} countries in Latin America and the Caribbean.`, nav: 'us', body});
}
