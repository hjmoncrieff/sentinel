// Front page: weekly lede, region map, coverage figures, sections, in-depth monitors.

import {esc, fmtDate, tColor, tLabel, chip, lvl, daysBetween} from '../lib/html.mjs';
import {layout} from './layout.mjs';
import {heroMap} from './maps.mjs';

const WEEKLY_MAX_AGE_DAYS = 10;

const cite = ctx => ([text, id]) => id
  ? `${esc(text)}<sup class="rb-fn"><a href="${ctx.url(`feed/?e=${id}`)}" aria-label="Source record">↗</a></sup>`
  : esc(text);

function monthBars(monthly) {
  const w = 300, h = 64, n = monthly.length, bw = w / n, max = Math.max(1, ...monthly.map(m => m[1]));
  const bars = monthly.map(([m, v], i) => {
    const bh = Math.max(1.5, v / max * (h - 16));
    return `<rect x="${(i * bw + 1).toFixed(1)}" y="${(h - 14 - bh).toFixed(1)}" width="${(bw - 2).toFixed(1)}" height="${bh.toFixed(1)}" fill="${i === n - 1 ? 'var(--amber)' : 'var(--ink-2)'}"><title>${m}: ${v} events</title></rect>`;
  }).join('');
  const lab = (i, anchor) => `<text x="${(i * bw + (anchor === 'end' ? bw - 1 : 1)).toFixed(1)}" y="${h - 2}" text-anchor="${anchor}" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--ink-3)">${fmtDate(monthly[i][0] + '-01', {month: 'short', year: '2-digit'})}</text>`;
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="Coded events per month over the past ${n} months"><line x1="0" x2="${w}" y1="${h - 13.5}" y2="${h - 13.5}" stroke="var(--rule)"/>${bars}${lab(0, 'start')}${lab(n - 1, 'end')}</svg>`;
}

const firstSentence = t => ((t || '').match(/[^.!?]+[.!?]+/) || [t || ''])[0].trim();

// The lede comes from an editor-approved weekly file when one is current. Otherwise it is
// an automatic pick from the week's coded events, and says so.
function weeklyBlock(model, ctx) {
  const w = model.weekly;
  const current = w && w.approved_by && daysBetween(model.asof, w.week) <= WEEKLY_MAX_AGE_DAYS;
  const c = cite(ctx);
  if (current) {
    return {
      label: `Weekly note · approved ${esc(w.approved_by)}`,
      head: w.lede.head.map(c).join(''),
      dek: w.lede.dek.map(c).join(''),
      side: w.watch?.length ? `
        <section class="ov-watch" aria-labelledby="ov-watch-h">
          <div class="ov-watch-h"><span class="kicker" id="ov-watch-h">Watch calendar</span><span class="mono">dated triggers from the reporting</span></div>
          <ol>${w.watch.map(x => `
            <li><span class="w-when"><b>${esc(x.when)}</b><small>${esc(x.rel || '')}</small></span>
              <span class="w-what"><span class="w-iso">${esc(x.iso)}</span>${esc(x.what)}<small>${esc(x.note || '')}${(x.ids || []).length ? ' · ' + x.ids.map((id, i) => `<a href="${ctx.url(`feed/?e=${id}`)}">source ${i + 1}</a>`).join(', ') : ''}</small></span></li>`).join('')}
          </ol>
        </section>` : '',
    };
  }
  const week = model.recent(7).filter(e => e.content_type === 'event' && model.byName[e.country]);
  const rank = e => (e.sal === 'high' ? 4 : e.sal === 'medium' ? 2 : 0) + Math.min(e.n_sources, 3);
  const top = [...week].sort((a, b) => rank(b) - rank(a) || b.date.localeCompare(a.date)).slice(0, 3);
  const active = [...model.countries].filter(x => x.n7).sort((a, b) => b.n7 - a.n7).slice(0, 4);
  return {
    label: 'Automatic selection from this week’s coded events',
    head: top[0] ? c([top[0].title, top[0].id]) : 'No new events were coded this week',
    dek: top.slice(1).map(e => c([' ' + firstSentence(e.summary || e.title), e.id])).join('').trim(),
    side: active.length ? `
        <section class="ov-watch" aria-labelledby="ov-watch-h">
          <div class="ov-watch-h"><span class="kicker" id="ov-watch-h">Most active this week</span><span class="mono">coded events, past 7 days</span></div>
          <ol>${active.map(x => `
            <li><span class="w-when"><b>${x.n7} event${x.n7 === 1 ? '' : 's'}</b><small>${x.high30 ? `${x.high30} high · 30d` : 'past 7 days'}</small></span>
              <span class="w-what"><span class="w-iso">${x.iso3}</span><a href="${ctx.url(`countries/${x.iso3.toLowerCase()}/`)}" style="text-decoration:none">${esc(x.name)}</a><small>${esc(x.cmr_status)} · outlook ${esc(x.outlook.level || 'not modeled')}${x.outlook.leading ? ` · ${esc(x.outlook.leading.toLowerCase())}` : ''}</small></span></li>`).join('')}
          </ol>
        </section>` : '',
  };
}

export function renderFront(model, ctx) {
  const recent = model.recent(30).filter(e => model.byName[e.country]);
  const recentEvents = recent.filter(e => e.content_type === 'event');
  const latest = recentEvents.slice(0, 4);
  const oc = recent.filter(e => e.type === 'oc').length;
  const us = recent.filter(e => e.type === 'coop' || e.type === 'aid' || e.type === 'exercise').length;
  const inDepth = model.countries.filter(c => c.in_depth);
  const map = heroMap(model, recentEvents, ctx);
  const wk = weeklyBlock(model, ctx);
  const n = v => v.toLocaleString('en');

  const body = `
  <div class="wrap ov">
    <section class="ov-hero" aria-labelledby="ov-title">
      <div class="ov-hero-main">
        <div class="ov-week"><span class="kicker">This week · ${fmtDate(model.asof, {day: 'numeric', month: 'long', year: 'numeric'})}</span><span class="label-ai">${wk.label}</span></div>
        <h1 id="ov-title" class="ov-lede">${wk.head}</h1>
        ${wk.dek ? `<p class="ov-dek">${wk.dek}</p>` : ''}
        ${wk.side}
        <div class="ov-signals">
          <span class="ov-signal"><b>${n(model.events.length)}</b> coded events</span>
          <span class="ov-signal"><span class="pulse" aria-hidden="true"></span>Updated nightly</span>
        </div>
        <div class="ov-ctas">
          <a class="btn-primary" href="${ctx.url('feed/')}">Open the live feed <span aria-hidden="true">→</span></a>
          <a class="btn-secondary" href="${ctx.url('countries/')}">Country monitors</a>
        </div>
      </div>
      <figure class="ov-map instr" aria-labelledby="ov-map-h">
        <div class="panel-title"><span id="ov-map-h">The region today</span>
          <span class="hm-layers" role="radiogroup" aria-label="Map layer">${[['status', 'Status'], ['outlook', 'Outlook'], ['activity', 'Activity']].map(([k, l]) => `<button type="button" role="radio" data-layer="${k}" aria-checked="${k === 'status'}">${l}</button>`).join('')}</span></div>
        <div class="hm-zooms" role="group" aria-label="Zoom to subregion">${[['all', 'Region'], ['north', 'Mexico & Central America'], ['Caribbean', 'Caribbean'], ['Andean', 'Andean'], ['south', 'Brazil & Southern Cone']].map(([k, l]) => `<button type="button" data-zoom="${k}" aria-pressed="${k === 'all'}">${l}</button>`).join('')}</div>
        <div class="ov-map-stage">${map.svg}<div class="hm-card" id="hm-card" hidden></div></div>
        <div class="map-legend" id="hm-legend">${map.legends.status}${map.marks}</div>
        <ol class="ov-strip">${latest.map(e => `
          <li data-iso="${model.byName[e.country].iso3}"><span class="tb" style="background:${tColor(e.type)}"></span>
            <span class="m">${model.byName[e.country].iso3} · ${fmtDate(e.date, {day: 'numeric', month: 'short'})}${e.sal === 'high' ? ' · <b>high</b>' : ''}</span>
            <a class="t" href="${ctx.url(`feed/?e=${e.id}`)}">${esc(e.title)}</a></li>`).join('')}
        </ol>
        <a class="ov-latest-more" href="${ctx.url('feed/?p=30')}">All ${recentEvents.length} events this month →</a>
        <script type="application/json" id="hm-data">${JSON.stringify({cards: map.cards, legends: map.legends, marks: map.marks}).replace(/</g, '\\u003c')}</script>
      </figure>
    </section>

    <section class="ov-stats" aria-label="Coverage">
      <div><b>${model.countries.length}</b><span>Countries tracked</span></div>
      <div><b>${n(model.events.length)}</b><span>Events in the archive</span></div>
      <div><b>${recent.length}</b><span>Events, past 30 days</span></div>
      <div><b>${model.sources_total}</b><span>Sources in the archive</span></div>
      <div class="ov-chart"><span class="kicker">Coded events per month</span>${monthBars(model.monthly)}</div>
    </section>

    <section class="ov-section" aria-labelledby="ov-cards-h">
      <div class="kicker ov-sec-k" id="ov-cards-h">Explore SENTINEL</div>
      <div class="ov-cards">
        <a class="ov-card" href="${ctx.url('feed/')}"><span class="kicker">Live feed</span><h3>Events</h3><p>Every coded event with its sources, coding and review state. Filter by country, type, salience and confidence.</p><span class="ov-card-n">${recent.length} this month</span></a>
        <a class="ov-card" href="${ctx.url('countries/')}"><span class="kicker">${model.countries.length} countries</span><h3>Country monitors</h3><p>Civil–military status, 90-day outlook, drivers, key positions and structural data. In-depth timelines for ${inDepth.length} countries.</p><span class="ov-card-n">${model.countries.filter(c => c.n30).length} active this month</span></a>
        <a class="ov-card" href="${ctx.legacy}#transnational"><span class="kicker">Transnational security</span><h3>Organized crime</h3><p>Cartel–state nexus, gang expansion and illicit economies, and how they reshape police and military power.</p><span class="ov-card-n">${oc} events this month</span></a>
        <a class="ov-card" href="${ctx.legacy}#us"><span class="kicker">SOUTHCOM · Greenbook</span><h3>US–Latin America</h3><p>Security cooperation, aid flows since 1946, training, basing and deployments.</p><span class="ov-card-n">${us} events this month</span></a>
      </div>
    </section>

    <section class="ov-section" aria-labelledby="ov-mon-h">
      <div class="kicker ov-sec-k">In-depth country monitors</div><h2 id="ov-mon-h" class="ov-h2">Deep analytical coverage</h2>
      <div class="ov-monitors">
        ${inDepth.map(c => `
        <a class="ov-mon" href="${ctx.url(`countries/${c.iso3.toLowerCase()}/`)}" style="--st:var(--st-${c.cmr_class === 'authoritarian' ? 'auth' : c.cmr_class})">
          <span class="ov-mon-name">${esc(c.name)}</span>
          <span class="ov-mon-sub">${esc(c.in_depth.subtitle)}</span>
          <span class="ov-mon-meta">${chip(c)}${lvl(c.outlook.level, '--amber')}<span class="mono">${c.n30} events · 30d</span></span>
          <span class="ov-mon-arrow" aria-hidden="true">›</span>
        </a>`).join('')}
      </div>
    </section>

    <section class="ov-section ov-sub" aria-labelledby="ov-sub-h">
      <div><div class="kicker ov-sec-k">Weekly brief</div><h2 id="ov-sub-h" class="ov-h2">Stay current on Latin American security</h2>
        <p>A curated summary of high-salience civil–military events, every Monday morning.</p></div>
      <form class="ov-sub-form" action="${ctx.formEndpoint}" method="POST">
        <label for="ov-email" class="visually-hidden">Email address</label>
        <input id="ov-email" name="email" type="email" required placeholder="you@university.edu" autocomplete="email">
        <input type="hidden" name="_subject" value="SENTINEL weekly brief signup">
        <button type="submit">Subscribe</button>
        <span class="note">We use your email only to send the brief. <a href="${ctx.legacy}privacy.html">Privacy policy</a></span>
      </form>
    </section>

    <section class="ov-section" aria-labelledby="ov-hood-h">
      <div class="kicker ov-sec-k" id="ov-hood-h">Under the hood</div>
      <div class="ov-hood">
        <div><p class="ov-body" style="margin:0 0 14px">SENTINEL tracks where civilian control is holding, where coercive institutions are being repurposed, and where security fragmentation is changing political risk across the hemisphere.</p>
        <ul class="ov-focus">
          <li><span>Track</span>civilian control, executive–military bargaining and command stress.</li>
          <li><span>Watch</span>organized crime, armed conflict and emergency rule as accelerants of coercion.</li>
          <li><span>Compare</span>country monitors, live events and long-run data in one place.</li>
        </ul>
        <p style="margin-top:14px">Events are collected every night from curated news feeds, publisher archives and structured datasets. A headline screen removes out-of-scope reports, then each remaining report is coded against the SENTINEL codebook by Claude, merged per incident, and published as static files. Each event record lists its sources, the evidence behind its coding, and whether an analyst has reviewed it. Machine-written text is always labeled.</p></div>
        <div class="ov-badges">${['InSight Crime', 'Reuters', 'AP', 'AFP', 'EFE', 'NACLA', 'Americas Quarterly', 'SOUTHCOM', 'NewsAPI', 'World Bank WDI/WGI', 'V-Dem v16', 'USAID Greenbook', 'ACLED index', 'Claude · Anthropic'].map(b => `<span>${b}</span>`).join('')}</div>
        <a class="ov-card-n" style="color:var(--amber)" href="${ctx.legacy}#about">About · methodology, sources and data →</a>
      </div>
    </section>
  </div>`;
  return layout(ctx, {title: '', nav: 'front', body, scripts: ['hero-map.js']});
}
