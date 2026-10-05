// Countries index (regional brief + situation board) and the per-country monitor page.

import {esc, fmtDate, tColor, tLabel, chip, lvl, pips, dir, ago, daysBetween, sparkBars, lineSpark} from '../lib/html.mjs';
import {layout} from './layout.mjs';
import {boardMap, timeline} from './maps.mjs';

const WEEKLY_MAX_AGE_DAYS = 10;
const countryUrl = (ctx, c) => ctx.url(`countries/${c.iso3.toLowerCase()}/`);

// An editor-approved brief with numbered citations when one is current; otherwise a
// plain factual line computed from the data, labelled as automatic.
function regionalBrief(model, ctx) {
  const w = model.weekly;
  const recent = model.recent(30).filter(e => model.byName[e.country]);
  if (w?.brief?.paras?.length && w.approved_by && daysBetween(model.asof, w.week) <= WEEKLY_MAX_AGE_DAYS) {
    const cited = [];
    const text = w.brief.paras.map(([t, id]) => {
      if (!id) return esc(t);
      cited.push(id);
      return `${esc(t)}<sup class="rb-fn"><a href="${ctx.url(`feed/?e=${id}`)}" aria-label="Source ${cited.length}">${cited.length}</a></sup>`;
    }).join('');
    const refs = cited.map((id, i) => {
      const e = model.events.find(x => x.id === id);
      return e ? `<li><span class="mono">${i + 1}</span><a href="${ctx.url(`feed/?e=${id}`)}">${esc(e.title)}</a> <span class="rb-src">${esc(e.sources.map(x => x.name).join(', '))} · ${fmtDate(e.date, {day: 'numeric', month: 'short'})}</span></li>` : '';
    }).join('');
    return `
    <section class="rb" aria-labelledby="rb-h">
      <div class="rb-meta"><span class="kicker" id="rb-h">Regional brief · week of ${fmtDate(w.week, {day: 'numeric', month: 'long', year: 'numeric'})}</span><span class="label-ai">Approved by ${esc(w.approved_by)}</span></div>
      <p class="rb-body">${text}</p>
      <details class="rb-refs"><summary>${cited.length} coded events cited</summary><ol>${refs}</ol></details>
    </section>`;
  }
  const high = recent.filter(e => e.sal === 'high').length;
  const ranked = [...model.countries].filter(c => c.n30).sort((a, b) => b.n30 - a.n30);
  const top = ranked.slice(0, 3).map(c => `<a href="${countryUrl(ctx, c)}">${esc(c.name)}</a> (${c.n30})`);
  const elevated = model.countries.filter(c => ['high', 'severe'].includes(c.outlook.level)).map(c => `<a href="${countryUrl(ctx, c)}">${esc(c.name)}</a>`);
  return `
    <section class="rb" aria-labelledby="rb-h">
      <div class="rb-meta"><span class="kicker" id="rb-h">The past 30 days · to ${fmtDate(model.asof, {day: 'numeric', month: 'long', year: 'numeric'})}</span><span class="label-ai">Computed from coded events</span></div>
      <p class="rb-body">${recent.length} events were coded across ${ranked.length} of ${model.countries.length} countries, ${high} of them rated high salience.${top.length ? ` The most active were ${top.join(', ')}.` : ''}${elevated.length ? ` The 90-day outlook is high or severe in ${elevated.join(', ')}.` : ''}</p>
    </section>`;
}

export function renderCountries(model, ctx) {
  const max = Math.max(1, ...model.countries.flatMap(c => c.spark));
  const rows = model.subregions.map(s => {
    const members = model.countries.filter(c => c.subregion === s);
    return `<tr class="grp"><td colspan="7">${s}</td></tr>` + members.map(c => `
      <tr class="row" data-iso="${c.iso3}">
        <td class="iso">${c.iso3}</td>
        <td><a class="cname" href="${countryUrl(ctx, c)}">${esc(c.name)}</a>${c.in_depth ? '<span class="sm-flag" title="In-depth monitor">IN-DEPTH</span>' : ''}</td>
        <td>${chip(c)}</td><td>${lvl(c.outlook.level)}</td><td>${dir(c.outlook.trend)}</td>
        <td>${sparkBars(c.spark, max)}</td><td class="ago ${c.last && daysBetween(model.asof, c.last) > 60 ? 'stale' : ''}">${ago(model.asof, c.last)}</td>
      </tr>`).join('');
  }).join('');
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>Countries</span></div>
    <section class="c-head" style="grid-template-columns:minmax(0,1.4fr) minmax(0,1fr)">
      <div><div class="kicker">Country monitors · ${model.countries.length} countries</div><h1 style="margin-top:8px;font-size:clamp(38px,5vw,64px)">The region at a glance</h1></div>
      <p style="margin:0;color:var(--ink-2)">Civil–military status, 90-day outlook and recent activity for every country. Select a row or a country on the map to open its monitor. ${model.countries.filter(c => c.in_depth).length} countries carry an in-depth monitor with a long-run timeline.</p>
    </section>
    ${regionalBrief(model, ctx)}
    <div style="height:24px"></div>
    <section class="board instr" aria-labelledby="board-h">
      <div class="board-grid">
        <div class="board-map">
          <div class="panel-title"><span id="board-h">Situation board</span><span class="mono">CMR status by country</span></div>
          ${boardMap(model, ctx)}
          <div class="map-legend">
            <span><i style="background:var(--st-stable-i)"></i>Stable</span><span><i style="background:var(--st-strained-i)"></i>Strained</span>
            <span><i style="background:var(--st-crisis-i)"></i>Crisis</span><span><i style="background:var(--st-auth-i)"></i>Authoritarian</span>
            <span><i style="background:transparent;outline:1.5px solid var(--i-amber)"></i>In-depth monitor</span>
          </div>
        </div>
        <div class="board-table">
          <table class="status">
            <thead><tr><th>ISO</th><th>Country</th><th>CMR status</th><th>90-day outlook</th><th>Direction</th><th>Events · 60 days</th><th>Last</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
      <div class="board-foot"><span>Outlook = labelled level from the country risk model; numeric scores are withheld until the model is validated.</span><span>Amber bars = last 7 days · all bars on one scale</span></div>
    </section>
  </div>`;
  return layout(ctx, {title: 'Country monitors', description: 'Civil–military status, 90-day outlook and recent activity for 25 countries in Latin America and the Caribbean.', nav: 'countries', body, scripts: ['board.js']});
}

/* ───────────── Country monitor ───────────── */

function outlookPanel(c) {
  const o = c.outlook;
  return `
  <section class="outlook instr" aria-label="90-day outlook">
    <div class="outlook-grid">
      <div class="ol-main">
        <div class="panel-title"><span>90-day outlook</span><span class="mono">country risk model</span></div>
        <div class="ol-level">${esc(o.level || 'Not modeled')}</div>
        <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">${pips(o.level)}${dir(o.trend)}</div>
        <div style="font-size:13px;color:var(--i-dim)">Leading pressure: <b style="color:var(--i-ink);font-weight:500">${esc(o.leading || '—')}</b></div>
        <div class="withheld">Shown as a level. Numeric scores are withheld until the model is validated.</div>
      </div>
      <div class="ol-cons">${c.constructs.map(k => `
        <div class="con"><div class="kicker">${esc(k.code.replaceAll('_', ' '))}</div><h3>${esc(k.label)}</h3>
          <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">${lvl(k.level)}${dir(k.trend)}</div>
          <ul>${k.drivers.map(d => `<li>${esc(d)}</li>`).join('')}</ul></div>`).join('')}
      </div>
    </div>
    <div class="watch"><b>Watch</b><span>${o.watch.map(esc).join(' · ') || '—'}</span></div>
  </section>`;
}

function inDepth(c, model) {
  const sm = c.in_depth;
  const tl = timeline(c, model.events.filter(e => e.country === c.name && e.content_type === 'event'), model.asof);
  return `
    <section class="section" aria-labelledby="deep-h">
      <div class="sec-head"><h2 id="deep-h">In-depth monitor · ${esc(sm.subtitle)}</h2><span class="kicker">${esc((sm.meta || []).map(m => m.value.split('\n')[0]).join(' · '))}</span></div>
      <div class="sm-lede" style="padding-block:0 24px">
        <div class="prose"><p>${esc(sm.brief)}</p></div>
        <aside><div class="keydata">${(sm.key_data || []).map(k => `<div><b>${esc(k.value)}</b><span>${esc(k.name)}</span><small>${esc(k.sub)}</small></div>`).join('')}</div></aside>
      </div>
      <div class="tl-wrap instr">
        <div style="padding:14px 16px 0" class="panel-title"><span>Timeline · ${sm.timeline_start} to today</span><span class="mono">■ curated milestone · ● coded event</span></div>
        <div class="tl-scroll">${tl.svg}</div>
        <div class="tl-read" id="tl-read" aria-live="polite">${tl.initial}</div>
      </div>
    </section>`;
}

function eventMix(c) {
  if (!c.type_mix.length) return '';
  const max = c.type_mix[0][1], total = c.type_mix.reduce((a, [, n]) => a + n, 0);
  return `
    <div class="sec-head section"><h2>Event mix · past 12 months</h2><span class="kicker">${total} coded events</span></div>
    <div class="mix" role="img" aria-label="${esc(c.type_mix.map(([t, n]) => `${tLabel(t)} ${n}`).join(', '))}">${c.type_mix.map(([t, n]) => `
      <div class="mix-row"><span class="mix-l">${esc(tLabel(t))}</span><span class="mix-bar"><span style="width:${(n / max * 100).toFixed(1)}%;background:${tColor(t)}"></span></span><span class="mix-n mono">${n}</span></div>`).join('')}
    </div>`;
}

function recentEvents(c, model, ctx, n = 8) {
  const evs = model.events.filter(e => e.country === c.name).slice(0, n);
  if (!evs.length) return '<p class="note">No coded events yet. Coverage for smaller countries depends on regional and wire reporting.</p>';
  return `<div class="cevents">${evs.map(e => `
    <div class="cev"><span class="d">${fmtDate(e.date, {day: 'numeric', month: 'short', year: e.date.slice(0, 4) === model.asof.slice(0, 4) ? undefined : '2-digit'})}</span><span class="b" style="background:${tColor(e.type)}"></span>
      <div><a href="${ctx.url(`feed/?e=${e.id}`)}" style="text-decoration:none">${esc(e.title)}</a><small>${tLabel(e.type)} · ${e.sal} salience · ${e.n_sources} source${e.n_sources > 1 ? 's' : ''}${e.content_type !== 'event' ? ` · ${e.content_type}` : ''}</small></div></div>`).join('')}</div>`;
}

// Sentence split that does not break inside initialisms such as "U.S.".
const firstSentences = (t, n = 2) => (t || '').split(/(?<=[.!?])\s+(?=[A-Z"“])/).reduce((out, part) => {
  if (out.length && /\b(?:[A-Z]\.)+$/.test(out[out.length - 1])) out[out.length - 1] += ' ' + part; else out.push(part);
  return out;
}, []).slice(0, n).join(' ').trim();
// Where the reference data stands. A proposed change never shows its new values here:
// the page keeps the current ones and says which are under review, until an analyst decides.
const underReview = c => `<span class="stale-flag">Under review · change detected ${esc(fmtDate(c.proposed.date, {day: 'numeric', month: 'short'}))}</span>`;
const refState = c => c.proposed
  ? underReview(c)
  : c.reviewed
    ? `<span class="mono ref-ok">Reviewed ${esc(fmtDate(c.reviewed))}${c.reviewed_by ? ` · ${esc(c.reviewed_by)}` : ''}</span>`
    : c.auto_updated
      ? `<span class="mono ref-auto">Auto-updated ${esc(fmtDate(c.auto_updated))} · awaiting review</span>`
      : '<span class="stale-flag">Not yet reviewed</span>';
const proposedOfficial = (c, post) => (c.proposed?.record?.officials || []).find(o => o.post === post && o.name && o.source_url);
const leaderChanged = c => { const p = proposedOfficial(c, 'head_of_government') || proposedOfficial(c, 'head_of_state'); return !!(p && p.name !== c.head_of_government); };
const electionChanged = c => { const e = c.proposed?.record?.next_election; return !!(e?.date && e.date !== c.election?.date); };
const flag = on => on ? ' <span class="stale-flag">Under review</span>' : '';
const official = (c, post) => (c.officials || []).find(o => o.post === post);
const since = o => o?.since ? ` <span class="prec">since ${esc(/^\d{4}-\d{2}$/.test(o.since) ? fmtDate(o.since + '-01', {month: 'short', year: 'numeric'}) : o.since)}</span>` : '';
const named = o => o?.name ? `${esc(o.name)}${since(o)}` : '<span class="unconf">Not confirmed</span>';
const electionText = e => e ? `${esc(e.type || '')}${e.date ? `, ${esc(/^\d{4}-\d{2}-\d{2}$/.test(e.date) ? fmtDate(e.date) : /^\d{4}-\d{2}$/.test(e.date) ? fmtDate(e.date + '-01', {month: 'long', year: 'numeric'}) : e.date)}` : ''}` : '—';

function positions(c) {
  if (!(c.officials || []).length) {
    return `<dl class="positions">${(c.positions || []).map(p => `<dt>${esc(p.t)}</dt><dd>${esc(p.n)}</dd>`).join('') || '<dt>—</dt><dd>Not recorded</dd>'}</dl>`;
  }
  return `<dl class="positions officials">${c.officials.map(o => `
    <dt>${esc(o.title)}</dt>
    <dd>${named(o)}${o.source_url ? ` <a class="src-link" href="${esc(o.source_url)}" target="_blank" rel="noopener" aria-label="Source for ${esc(o.title)}">source ↗</a>` : ''}${o.note ? `<small>${esc(o.note)}</small>` : ''}</dd>`).join('')}</dl>
    <p class="note">${c.reviewed ? `Researched with web search by Claude; reviewed by ${esc(c.reviewed_by || 'an analyst')} on ${esc(fmtDate(c.reviewed))}.` : `Researched with web search by Claude on ${esc(fmtDate(c.auto_updated))}; each name links to the page that supports it. Awaiting analyst review.`}</p>`;
}

export function renderCountry(c, model, ctx) {
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><a href="${ctx.url('countries/')}">Countries</a><span>›</span>
      <label class="visually-hidden" for="c-pick">Choose a country</label>
      <select id="c-pick">${model.countries.map(x => `<option value="${countryUrl(ctx, x)}" ${x.iso3 === c.iso3 ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select></div>
    <section class="c-head">
      <div><div class="kicker">${c.iso3} · ${esc(c.subregion)} · Country monitor${c.in_depth ? ' · <span style="color:var(--amber)">In-depth</span>' : ''}</div><h1 style="margin-top:8px">${esc(c.name)}</h1>
        <p style="margin:14px 0 0;color:var(--ink-2);max-width:62ch">${esc(c.auto_updated ? c.note : firstSentences(c.note))}</p>
        ${c.auto_updated ? `<p class="mono ref-auto" style="margin:8px 0 0">AI-assisted summary · ${esc(fmtDate(c.auto_updated))}</p>` : ''}
        ${c.proposed ? `<p class="note" style="margin:8px 0 0">New reporting suggests some of the reference details on this page have changed. They are shown as last confirmed until an analyst reviews the update.</p>` : ''}</div>
      <dl class="facts">
        <dt>CMR status</dt><dd>${chip(c)}</dd>
        <dt>${esc(official(c, 'head_of_state')?.title?.replace(/ \(.*\)$/, '') || 'Government')}</dt><dd>${official(c, 'head_of_state') ? named(official(c, 'head_of_state')) : esc(c.head_of_government || '—')}${flag(leaderChanged(c))}</dd>
        ${official(c, 'head_of_government') ? `<dt>${esc(official(c, 'head_of_government').title)}</dt><dd>${named(official(c, 'head_of_government'))}</dd>` : ''}
        ${official(c, 'vice_president') ? `<dt>Vice President</dt><dd>${named(official(c, 'vice_president'))}</dd>` : ''}
        ${official(c, 'defence_minister') ? `<dt>Defence minister</dt><dd>${named(official(c, 'defence_minister'))}</dd>` : ''}
        <dt>Regime</dt><dd>${esc(c.regime || '—')}</dd>
        <dt>Next election</dt><dd>${electionText(c.election)}${flag(electionChanged(c))}</dd>
        ${c.last_election ? `<dt>Last election</dt><dd>${electionText(c.last_election)}</dd>` : ''}
      </dl>
    </section>
    ${c.structural.length ? `<section class="struct-strip" aria-label="Structural indicators">${c.structural.map(s => `
      <div class="sstat"><div class="l">${esc(s.label)}</div><div class="sstat-v"><span class="v">${esc(s.value)}</span>${lineSpark(s.series, 72, 24)}</div><div class="y">${s.year} · ${esc(s.source)}</div></div>`).join('')}</section>` : ''}
    ${outlookPanel(c)}
    ${c.in_depth ? inDepth(c, model) : ''}
    <div class="two section">
      <div>
        <div class="sec-head"><h2>Assessment</h2><span class="label-ai">Automated rule-based summary · not reviewed</span></div>
        <div class="prose"><p>${esc(c.outlook.summary || 'No model summary for this country yet.')}</p>${c.constructs.slice(0, 1).map(k => k.summary ? `<p>${esc(k.summary)}</p>` : '').join('')}</div>
        <div class="sec-head section"><h2>Recent events</h2><a href="${ctx.url(`feed/?c=${encodeURIComponent(c.name)}&p=0`)}">All ${c.total} in the feed →</a></div>
        ${recentEvents(c, model, ctx)}
        ${eventMix(c)}
      </div>
      <aside>
        <div class="sec-head"><h2>Key positions</h2>${refState(c)}</div>
        ${positions(c)}
        ${c.watch ? `<div class="sec-head section"><h2>${c.auto_updated ? 'Watch note' : 'Analyst watch note'}</h2>${c.auto_updated ? '<span class="mono ref-auto">AI-assisted</span>' : ''}</div><p style="font-size:14px;color:var(--ink-2);margin:0">${esc(c.watch)}</p>` : ''}
        ${c.missions?.length ? `<div class="sec-head section"><h2>Military roles</h2></div>
        <ul class="missions">${c.missions.map(m => `<li><span>${esc(m.role)}</span><span class="mono ms-${esc(m.status)}">${esc(m.status)}</span></li>`).join('')}</ul>` : ''}
      </aside>
    </div>
  </div>`;
  return layout(ctx, {
    title: `${c.name} · Country monitor`,
    description: `${c.name}: civil–military status ${c.cmr_status}, 90-day outlook ${c.outlook.level || 'not modeled'}, ${c.total} coded events.`,
    nav: 'countries', body, scripts: ['country.js'],
  });
}
