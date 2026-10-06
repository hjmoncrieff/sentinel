// One page per event record: a stable address to cite, complete without scripts.

import {esc, fmtDate, tLabel, tColor, corroboration, plainActor} from '../lib/html.mjs';
import {layout} from './layout.mjs';

const METHOD = {rss: 'RSS feed', google_news_rss: 'Google News search', google_news_window: 'Google News search', newsapi: 'NewsAPI', wordpress_archive: 'Publisher archive', gdelt: 'GDELT', backfilled_from_event_store: 'Publisher link', manual_web_audit: 'Manual audit'};
const pretty = v => String(v || '').replaceAll('_', ' ');
export const eventUrl = (ctx, id) => ctx.url(`events/${id}/`);

export function renderEvent(e, model, ctx) {
  const k = e.coding, c = model.byName[e.country];
  const [, corrWord] = corroboration(e);
  const dated = k?.date_precision === 'day' ? 'day reported' : k?.date_precision === 'month' ? 'month reported; shown by publication date' : k ? 'dated by publication' : null;
  const address = ctx.origin + eventUrl(ctx, e.id);
  const sameStory = model.events.filter(x => x.id !== e.id && (x.story === e.id || (e.story && (x.id === e.story || x.story === e.story))));
  const status = e.reviewed ? 'Analyst-reviewed' : 'Machine-coded · not reviewed';
  const body = `
  <div class="wrap ev-page">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><a href="${ctx.url('feed/')}">Live feed</a><span>›</span><span>Record ${esc(e.id)}</span></div>
    <header class="ev-head">
      <div class="kicker"><span style="color:${tColor(e.type)}">■</span> ${tLabel(e.type)} · ${c ? `<a href="${ctx.url(`countries/${c.iso3.toLowerCase()}/`)}">${esc(e.country)}</a>` : esc(e.country)} · ${fmtDate(e.date)}${e.content_type !== 'event' ? ` · ${esc(e.content_type)}` : ''}</div>
      <h1>${esc(e.title)}</h1>
      ${e.summary ? `<p class="ev-sum">${esc(e.summary)}</p>` : ''}
      <p class="ev-line"><span class="label-ai">${status}</span> Coded as ${esc(tLabel(e.type).toLowerCase())}${e.location ? ` in ${esc(e.location)}` : ''}, ${esc(e.sal)} salience, ${esc(e.conf)} coding confidence${e.actor ? `; initiated by ${esc(plainActor(e.actor))}${e.target ? ` against ${esc(plainActor(e.target))}` : ''}` : ''}.</p>
    </header>
    <div class="ev-grid">
      <section class="instr ev-panel" aria-label="Sources">
        <div class="panel-title"><span>What the sources report</span><span class="mono">${e.sources.length} linked</span></div>
        ${e.sources.map(s => `<div class="src">
          <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a><span class="m">${s.tier ? 'tier ' + s.tier : ''}</span>
          ${s.headline && s.headline !== e.title ? `<span class="src-h">${esc(s.headline)}</span>` : ''}
          ${s.excerpt ? `<blockquote class="src-x">${esc(s.excerpt)}</blockquote>` : '<span class="src-none">No excerpt stored for this report.</span>'}
          <span class="m" style="grid-column:1/-1">${esc(METHOD[s.method] || pretty(s.method))}${s.method ? ' · ' : ''}<a href="${esc(s.url)}" target="_blank" rel="noopener" style="color:var(--i-amber)">Read at source ↗</a></span></div>`).join('')}
        ${k?.evidence?.length ? `<div class="panel-title" style="margin-top:20px"><span>Evidence for the coding</span><span class="mono">quoted from the report</span></div>
          ${k.evidence.map(q => `<blockquote class="src-x" style="margin:10px 0 0">${esc(q)}</blockquote>`).join('')}` : ''}
        ${e.analysis ? `<div class="ai-box" style="margin-top:20px"><div class="panel-title"><span>Interpretation</span><span class="mono">${e.ai ? 'AI-assisted' : 'automated · rule-based'}</span></div>${esc(e.analysis).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n\n/g, '<br><br>')}</div>` : ''}
      </section>
      <section class="instr ev-panel" aria-label="Coding and provenance">
        <div class="panel-title" style="margin-bottom:8px"><span>Coding</span><span class="mono">${k ? `codebook v${esc(k.codebook_version)}` : 'taxonomy v2 · legacy'}</span></div>
        <dl class="dl">
          <dt>Type</dt><dd>${k?.type ? `${esc(pretty(k.type))}${k.subtype ? ` · ${esc(pretty(k.subtype))}` : ''}` : tLabel(e.type)}</dd>
          <dt>Salience</dt><dd>${esc(e.sal)}</dd>
          <dt>Confidence</dt><dd>${esc(e.conf)}</dd>
          ${k?.deed_category ? `<dt>DEED category</dt><dd>${esc(pretty(k.deed_category))}</dd>` : e.deed ? `<dt>DEED role</dt><dd>${esc(e.deed)}</dd>` : ''}
          ${k?.actors?.length ? `<dt>Actors</dt><dd>${k.actors.map(a => `${esc(a.name)} <span class="prec">${esc(pretty(a.role))}</span>`).join('<br>')}</dd>` : e.actor ? `<dt>Actor → target</dt><dd>${esc(pretty(e.actor))} → ${esc(pretty(e.target || '—'))}</dd>` : ''}
          ${e.location ? `<dt>Location</dt><dd>${esc(e.location)} <span class="prec">${e.precision === 'place' ? 'mapped to place' : 'country-level point'}</span></dd>` : ''}
          ${dated ? `<dt>Date</dt><dd>${esc(dated)}</dd>` : ''}
          <dt>Corroboration</dt><dd>${corrWord} · ${e.n_sources} source${e.n_sources > 1 ? 's' : ''}</dd>
        </dl>
        <div class="panel-title" style="margin:20px 0 4px"><span>Provenance</span><span class="mono">record ${esc(e.id)}</span></div>
        <ul class="prov">
          <li class="done"><i></i>Collected from ${e.n_sources} report${e.n_sources > 1 ? 's' : ''}<span class="m">${fmtDate(e.date, {day: 'numeric', month: 'short'})}</span></li>
          <li class="done"><i></i>${k ? `Coded against codebook v${esc(k.codebook_version)} by ${esc(k.coded_by || 'Claude')}` : 'Classified with the v2 prompt (Claude Haiku)'}<span class="m">auto</span></li>
          <li class="done"><i></i>Merged with same-incident reports<span class="m">auto</span></li>
          <li class="${e.reviewed ? 'done' : 'pend'}"><i></i>Analyst review<span class="m">${e.reviewed ? 'reviewed' : 'not reviewed'}</span></li>
          <li class="done"><i></i>Published to the public layer<span class="m">nightly</span></li>
        </ul>
      </section>
    </div>
    ${sameStory.length ? `<section class="section"><div class="sec-head"><h2>Other records of this story</h2></div>
      <div class="cevents">${sameStory.map(x => `<div class="cev"><span class="d">${fmtDate(x.date, {day: 'numeric', month: 'short'})}</span><span class="b" style="background:${tColor(x.type)}"></span><div><a href="${eventUrl(ctx, x.id)}" style="text-decoration:none">${esc(x.title)}</a><small>${esc(x.sources[0]?.name || '')} · ${tLabel(x.type)} · ${x.sal} salience</small></div></div>`).join('')}</div></section>` : ''}
    <section class="section ev-cite">
      <div class="sec-head"><h2>Cite this record</h2><a href="${ctx.url(`feed/?e=${e.id}&p=0`)}">Open in the live feed →</a></div>
      <p class="cite">SENTINEL. “${esc(e.title)}.” Event record ${esc(e.id)}, ${fmtDate(e.date)}. ${k ? `Coded with codebook v${esc(k.codebook_version)}` : 'Coded with taxonomy v2'}; ${e.reviewed ? 'analyst-reviewed' : 'machine-coded, not reviewed'}. ${esc(address)}</p>
      <p class="note">The record number is permanent. This address will change once, when the redesigned site leaves preview, so include the record number. The coding can change after analyst review; cite the date you retrieved it. How records are made is described in the <a href="${ctx.url('about/')}">methodology</a>.</p>
    </section>
  </div>`;
  return layout(ctx, {
    title: e.title.length > 70 ? e.title.slice(0, 68).trimEnd() + '…' : e.title,
    description: `${tLabel(e.type)} · ${e.country} · ${fmtDate(e.date)}. ${e.summary || ''}`.slice(0, 300),
    nav: 'feed', body,
  });
}

/** A folded duplicate's old address: forwards to the record that replaced it. */
export function renderEventRedirect(target, ctx) {
  const to = eventUrl(ctx, target);
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Record moved · SENTINEL</title><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url=${esc(to)}"><link rel="canonical" href="${esc(to)}"></head><body><p>This record was merged with a duplicate. <a href="${esc(to)}">Open the current record</a>.</p></body></html>\n`;
}
