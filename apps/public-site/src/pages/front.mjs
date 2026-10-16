// Front page, laid out as an edition: dateline, lead story, the week's other stories, the
// map as a captioned figure, the regional brief, features from the topic pages, the in-depth
// monitors with a pull quote, figures, the weekly brief and a colophon.
// Every story is a coded record and links to it; nothing on the page is written for the day.

import {esc, fmtDate, tColor, tLabel, chip, lvl, daysBetween, corroboration} from '../lib/html.mjs';
import {layout} from './layout.mjs';
import {heroMap} from './maps.mjs';
import {regionalBrief} from './countries.mjs';
import {eventUrl} from './event.mjs';
import {groupStories} from '../lib/model.mjs';

const WEEKLY_MAX_AGE_DAYS = 10;

function monthBars(monthly) {
  const w = 300, h = 64, n = monthly.length, bw = w / n, max = Math.max(1, ...monthly.map(m => m[1]));
  const bars = monthly.map(([m, v], i) => {
    const bh = Math.max(1.5, v / max * (h - 16));
    return `<rect x="${(i * bw + 1).toFixed(1)}" y="${(h - 14 - bh).toFixed(1)}" width="${(bw - 2).toFixed(1)}" height="${bh.toFixed(1)}" fill="${i === n - 1 ? 'var(--amber)' : 'var(--ink-2)'}"><title>${m}: ${v} events</title></rect>`;
  }).join('');
  const lab = (i, anchor) => `<text x="${(i * bw + (anchor === 'end' ? bw - 1 : 1)).toFixed(1)}" y="${h - 2}" text-anchor="${anchor}" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--ink-3)">${fmtDate(monthly[i][0] + '-01', {month: 'short', year: '2-digit'})}</text>`;
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="Coded events per month over the past ${n} months"><line x1="0" x2="${w}" y1="${h - 13.5}" y2="${h - 13.5}" stroke="var(--rule)"/>${bars}${lab(0, 'start')}${lab(n - 1, 'end')}</svg>`;
}

const firstSentence = t => ((t || '').match(/^.+?[.!?](?=\s+[A-Z"“]|$)/) || [t || ''])[0].trim();
const day = d => fmtDate(d, {day: 'numeric', month: 'short'});

// The week's stories: an editor's pick when a weekly note is current, otherwise the week's
// coded events ranked by salience and sourcing, one per story.
function edition(model) {
  const week = model.recent(7).filter(e => e.content_type === 'event' && model.byName[e.country]);
  const pool = week.length >= 4 ? week : model.recent(30).filter(e => e.content_type === 'event' && model.byName[e.country]);
  const rank = e => (e.sal === 'high' ? 4 : e.sal === 'medium' ? 2 : 0) + Math.min(e.n_sources, 3) + (e.summary ? .5 : 0);
  const stories = groupStories(pool).map(g => g.lead).sort((a, b) => rank(b) - rank(a) || b.date.localeCompare(a.date));
  // One story per country in the top slots, so the edition reads across the region.
  const picked = [], seen = new Set();
  for (const e of stories) { if (seen.has(e.country)) continue; seen.add(e.country); picked.push(e); if (picked.length === 5) break; }
  const w = model.weekly, approved = w && w.approved_by && daysBetween(model.asof, w.week) <= WEEKLY_MAX_AGE_DAYS;
  return {lead: picked[0], more: picked.slice(1, 5), approved: approved ? w : null, span: pool === week ? 'this week' : 'the past 30 days'};
}

function leadStory(e, ed, model, ctx) {
  if (!e) return '<h1 class="fp-h">No events were coded this week</h1>';
  const c = model.byName[e.country];
  const head = ed.approved ? ed.approved.lede.head.map(([t]) => esc(t)).join('') : esc(e.title);
  const dek = ed.approved ? ed.approved.lede.dek.map(([t]) => esc(t)).join('') : esc(e.summary || '');
  return `
      <div class="fp-kick"><a href="${ctx.url(`countries/${c.iso3.toLowerCase()}/`)}">${esc(c.name)}</a><span>${esc(tLabel(e.type))}</span><span>${day(e.date)}</span></div>
      <h1 class="fp-h" id="fp-lead-h"><a href="${eventUrl(ctx, e.id)}">${head}</a></h1>
      ${dek ? `<p class="fp-dek">${dek}</p>` : ''}
      <p class="fp-by">${ed.approved ? `Chosen by ${esc(ed.approved.approved_by)}` : `Selected automatically from the coded events of ${ed.span}`} · ${esc(corroboration(e)[1].toLowerCase())}, ${e.n_sources} source${e.n_sources > 1 ? 's' : ''} · ${e.sal} salience · <a href="${eventUrl(ctx, e.id)}">Read the record →</a></p>`;
}

function alsoStories(list, model, ctx) {
  return `<div class="fp-also">${list.map(e => {
    const c = model.byName[e.country];
    return `<article><div class="fp-kick sm"><span style="color:${tColor(e.type)};filter:saturate(1.3)">■</span><a href="${ctx.url(`countries/${c.iso3.toLowerCase()}/`)}">${esc(c.name)}</a><span>${day(e.date)}</span></div>
      <h3><a href="${eventUrl(ctx, e.id)}">${esc(e.title)}</a></h3>
      ${e.summary ? `<p>${esc(firstSentence(e.summary))}</p>` : ''}
      <small>${esc(tLabel(e.type))} · ${e.sal} salience · ${e.n_sources} source${e.n_sources > 1 ? 's' : ''}</small></article>`;
  }).join('')}</div>`;
}

// Features: the topic pages and the country board, each led by one sourced figure.
function features(model, ctx) {
  const oc = model.topics.oc, us = model.topics.us;
  const elevated = model.countries.filter(c => ['high', 'severe'].includes(c.outlook.level));
  // The card is a link, so the figure names its source instead of linking to it; the page lists it.
  const fig = f => f ? `<div class="fp-fig"><b>${esc(f.value)}</b><span>${esc(f.label)}</span><small>${esc(f.year)}${f.source != null ? ` · source ${f.source + 1} on the page` : ''}</small></div>` : '';
  const items = [
    {url: ctx.url('countries/'), kicker: 'Country monitors', title: 'The region at a glance', dek: `Civil–military status, the 90-day outlook and recent activity for all ${model.countries.length} countries.`,
      figure: {value: `${elevated.length} of ${model.countries.length}`, label: 'countries with a high or severe 90-day outlook', year: fmtDate(model.asof)}},
    oc && {url: ctx.url('organized-crime/'), kicker: 'Organized crime', title: 'Organized crime and the state', dek: firstSentence(oc.lede), figure: oc.figures.find(f => /terrorist/.test(f.label)) || oc.figures[0]},
    us && {url: ctx.url('us-security/'), kicker: 'US security', title: 'The Caribbean campaign', dek: firstSentence(us.lede), figure: us.figures[0]},
  ].filter(Boolean);
  return `<div class="fp-feats">${items.map(f => `
    <a class="fp-feat" href="${f.url}"><span class="kicker">${esc(f.kicker)}</span><h3>${esc(f.title)}</h3><p>${esc(f.dek)}</p>${fig(f.figure)}<span class="fp-more">Read →</span></a>`).join('')}</div>`;
}

function inDepth(model, ctx) {
  return `<div class="fp-deep">${model.countries.filter(c => c.in_depth).map(c => `
    <a class="fp-col" href="${ctx.url(`countries/${c.iso3.toLowerCase()}/`)}">
      <span class="kicker">${esc(c.in_depth.subtitle)}</span>
      <h3>${esc(c.name)}</h3>
      <blockquote>${esc(firstSentence(c.in_depth.brief))}</blockquote>
      <span class="fp-col-meta">${chip(c)}${lvl(c.outlook.level, '--amber')}</span>
      <small>${c.n30} events in 30 days · timeline from ${c.in_depth.timeline_start}</small></a>`).join('')}</div>`;
}

// Old dashboard links (#events, #profiles, …) land here; send them to the page that replaced the tab.
const LEGACY_REDIRECT = `<script>(function(){var m={events:'feed/',profiles:'countries/',transnational:'organized-crime/',us:'us-security/',about:'about/',explore:'explore/',timeline:'explore/'};var h=location.hash.slice(1);if(m[h])location.replace(m[h]);})();</script>`;

export function renderFront(model, ctx) {
  const recent = model.recent(30).filter(e => model.byName[e.country]);
  const recentEvents = recent.filter(e => e.content_type === 'event');
  const map = heroMap(model, recentEvents, ctx);
  const ed = edition(model);
  const n = v => v.toLocaleString('en');
  const active = [...model.countries].filter(x => x.n7).sort((a, b) => b.n7 - a.n7).slice(0, 5);
  const today = new Date(model.asof + 'T00:00:00Z');
  const weekNo = Math.ceil(((today - Date.UTC(today.getUTCFullYear(), 0, 1)) / 864e5 + new Date(Date.UTC(today.getUTCFullYear(), 0, 1)).getUTCDay() + 1) / 7);

  const body = `
  ${ctx.live ? LEGACY_REDIRECT : ''}
  <div class="wrap fp">
    <div class="fp-dateline" role="note">
      <span>${fmtDate(model.asof, {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'})}</span>
      <span>Week ${weekNo}</span>
      <span>${model.countries.length} countries · ${n(model.events.length)} coded events</span>
      <span><span class="pulse" aria-hidden="true"></span>Updated nightly</span>
    </div>

    <section class="fp-front" aria-labelledby="fp-lead-h">
      <div class="fp-main">
        ${leadStory(ed.lead, ed, model, ctx)}
        <div class="fp-rule"><span class="kicker">Also ${ed.span}</span></div>
        ${alsoStories(ed.more, model, ctx)}
        <a class="fp-feedlink" href="${ctx.url('feed/')}">Every coded event, with its sources, in the live feed →</a>
      </div>
      <figure class="fp-map">
        <div class="ov-map instr">
          <div class="panel-title"><span>The region today</span>
            <span class="hm-layers" role="radiogroup" aria-label="Map layer">${[['status', 'Status'], ['outlook', 'Outlook'], ['activity', 'Activity']].map(([k, l]) => `<button type="button" role="radio" data-layer="${k}" aria-checked="${k === 'status'}">${l}</button>`).join('')}</span></div>
          <div class="hm-zooms" role="group" aria-label="Zoom to subregion">${[['all', 'Region'], ['north', 'Mexico & Central America'], ['Caribbean', 'Caribbean'], ['Andean', 'Andean'], ['south', 'Brazil & Southern Cone']].map(([k, l]) => `<button type="button" data-zoom="${k}" aria-pressed="${k === 'all'}">${l}</button>`).join('')}</div>
          <div class="ov-map-stage">${map.svg}<div class="hm-card" id="hm-card" hidden></div></div>
          <div class="map-legend" id="hm-legend">${map.legends.status}${map.marks}</div>
          <script type="application/json" id="hm-data">${JSON.stringify({cards: map.cards, legends: map.legends, marks: map.marks}).replace(/</g, '\\u003c')}</script>
        </div>
        <figcaption><b>The region today.</b> Civil–military status by country, with the past 30 days of coded events: dots where an event is placed at a town, counts where it is recorded for the country. Hover or tap a country for its card.</figcaption>
        ${active.length ? `<div class="fp-active"><div class="kicker">Most active this week</div><ol>${active.map(x => `
          <li><a href="${ctx.url(`countries/${x.iso3.toLowerCase()}/`)}">${esc(x.name)}</a><span class="mono">${x.n7}</span><small>${esc(x.cmr_status)} · outlook ${esc(x.outlook.level || 'not modeled')}</small></li>`).join('')}</ol></div>` : ''}
      </figure>
    </section>

    <section class="fp-sec fp-brief" aria-label="The regional brief">
      ${regionalBrief(model, ctx)}
    </section>

    <section class="fp-sec" aria-labelledby="fp-feat-h">
      <div class="fp-head"><h2 id="fp-feat-h">Features</h2><span class="kicker">Topic monitors, with sourced background</span></div>
      ${features(model, ctx)}
    </section>

    <section class="fp-sec" aria-labelledby="fp-deep-h">
      <div class="fp-head"><h2 id="fp-deep-h">In depth</h2><span class="kicker">Four countries with long-run timelines</span></div>
      ${inDepth(model, ctx)}
    </section>

    <section class="fp-sec fp-numbers" aria-labelledby="fp-num-h">
      <div class="fp-head"><h2 id="fp-num-h">By the numbers</h2><span class="kicker">The archive behind the edition</span></div>
      <div class="ov-stats">
        <div><b>${model.countries.length}</b><span>Countries tracked</span></div>
        <div><b>${n(model.events.length)}</b><span>Events in the archive</span></div>
        <div><b>${recent.length}</b><span>Events, past 30 days</span></div>
        <div><b>${model.sources_total}</b><span>Sources in the archive</span></div>
        <div class="ov-chart"><span class="kicker">Coded events per month</span>${monthBars(model.monthly)}</div>
      </div>
    </section>

    <section class="fp-sec fp-letter" aria-labelledby="fp-sub-h">
      <div><span class="kicker">Newsletter</span><h2 id="fp-sub-h">The Monday Brief</h2>
        <p>The week's high-salience civil–military events across the region, with links to every record, each Monday morning.</p></div>
      <form class="ov-sub-form" action="${ctx.formEndpoint}" method="POST">
        <label for="ov-email" class="visually-hidden">Email address</label>
        <input id="ov-email" name="email" type="email" required placeholder="you@university.edu" autocomplete="email">
        <input type="hidden" name="_subject" value="SENTINEL weekly brief signup">
        <button type="submit">Subscribe</button>
        <span class="note">We use your email only to send the brief. <a href="${ctx.legacy}privacy.html">Privacy policy</a></span>
      </form>
    </section>

    <section class="fp-sec fp-colophon" aria-labelledby="fp-col-h">
      <div class="fp-head"><h2 id="fp-col-h">About this monitor</h2></div>
      <div class="fp-colo">
        <p class="fp-colo-lede">SENTINEL tracks where civilian control is holding, where coercive institutions are being repurposed, and where security fragmentation is changing political risk across the hemisphere.</p>
        <p>Every night it collects reporting from news wires, specialist outlets, official sources and publisher archives. It screens out what is out of scope, codes the rest against the SENTINEL codebook with Claude, merges reports of the same incident, and publishes the result. Each record lists its sources and the evidence behind its coding, and says whether an analyst has reviewed it. Machine-written text is always labeled.</p>
        <p><a href="${ctx.url('about/')}">Method, codebook and sources →</a> · <a href="${ctx.url('explore/')}">Explore the data →</a></p>
      </div>
    </section>
  </div>`;
  return layout(ctx, {title: '', nav: 'front', body, scripts: ['hero-map.js']});
}
