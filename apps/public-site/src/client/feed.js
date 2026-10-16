// Live feed: filter, stream, and a right pane that shows the map until a record is picked.
// State lives in the URL so any view can be shared.

import {esc, fmtDate, tLabel, tColor, corroboration, plainActor, daysBetween, ago} from '../lib/html.mjs';

const $ = (s, el = document) => el.querySelector(s);
const page = $('.feed-page');
const PAGE_SIZE = 150;

const DEFAULTS = {country: 'all', type: 'all', sal: 'all', conf: 'all', period: 90, content: 'event', rev: 'all', sel: null};
const KEYS = {c: 'country', t: 'type', s: 'sal', k: 'conf', p: 'period', ct: 'content', r: 'rev', e: 'sel'};
const F = {...DEFAULTS};
let D = null, ISO = {}, shown = PAGE_SIZE, view = 'map';

function readState() {
  Object.assign(F, DEFAULTS);
  new URLSearchParams(location.search).forEach((v, k) => { if (KEYS[k]) F[KEYS[k]] = KEYS[k] === 'period' ? +v : v; });
  // A link to a record that was merged into another opens the record that replaced it.
  if (D?.aliases?.[F.sel]) F.sel = D.aliases[F.sel];
}
function writeState() {
  const q = new URLSearchParams();
  for (const [k, f] of Object.entries(KEYS)) if (F[f] !== DEFAULTS[f] && F[f] != null) q.set(k, F[f]);
  const next = `${location.pathname}${q.toString() ? '?' + q : ''}`;
  if (next !== location.pathname + location.search) history.replaceState(null, '', next);
}
const days = d => daysBetween(D.asof, d);
const iso = name => ISO[name] || (name === 'Regional' ? 'REG' : '—');

// Per-viewer convenience only: mark what is new since the last visit.
const LAST_VISIT = (() => { try { return localStorage.getItem('sentinel.feed.lastVisit'); } catch { return null; } })();

function matches(e) {
  return (F.country === 'all' || e.country === F.country) && (F.type === 'all' || e.type === F.type)
    && (F.sal === 'all' || e.sal === F.sal) && (F.conf === 'all' || e.conf === F.conf)
    && (!F.period || days(e.date) <= F.period)
    && (F.rev === 'all' || e.reviewed)
    && (F.content === 'all' || (F.content === 'event' ? e.content_type === 'event' : e.content_type !== 'event'));
}

function syncControls() {
  document.querySelectorAll('.fchip[data-f]').forEach(b => b.setAttribute('aria-pressed', String(F[b.dataset.f]) === b.dataset.v));
  $('#f-country').value = F.country;
}

function draw(scrollToSel) {
  const all = D.events.filter(matches), inView = new Set(all.map(e => e.id));
  // Records of one story fold under its lead record, unless the lead is filtered out
  // or the folded record is the one selected.
  const items = all.filter(e => !e.story || !inView.has(e.story) || e.id === F.sel);
  const folded = all.length - items.length;
  // A deep link to a record outside the current filters still opens it.
  const linked = F.sel && !items.some(e => e.id === F.sel) ? D.events.find(e => e.id === F.sel) : null;
  // Nothing is selected until the reader picks a record (or a link names one): the map shows instead.
  if (F.sel && !D.events.some(e => e.id === F.sel)) F.sel = null;
  if (!F.sel) view = 'map';
  const hidden = D.events.filter(e => (!F.period || days(e.date) <= F.period) && e.content_type !== 'event').length;
  const countries = new Set(items.map(e => e.country)).size, high = items.filter(e => e.sal === 'high').length;
  $('#f-count').textContent = `${items.length.toLocaleString('en')} record${items.length === 1 ? '' : 's'}${folded ? ` · ${folded} more of the same stories` : ''}`;
  $('#f-sum').textContent = `${F.country === 'all' ? `${countries} countries` : F.country} · ${F.period ? `${F.period} days` : 'all dates'} · ${high} high${F.content === 'event' && hidden ? ` · ${hidden} analysis hidden` : ''}`;
  const active = ['country', 'type', 'sal', 'conf', 'rev', 'period', 'content'].filter(k => F[k] !== DEFAULTS[k]).length;
  $('#f-active').hidden = !active; $('#f-active').textContent = active;

  let html = '', day = null, dividerDone = false;
  if (linked) html += `<div class="new-div"><span>Linked record, outside the current filters</span></div>${row(linked)}`;
  for (const e of items.slice(0, shown)) {
    if (!dividerDone && LAST_VISIT && e.date <= LAST_VISIT && html) { html += `<div class="new-div"><span>Earlier than your last visit (${fmtDate(LAST_VISIT, {day: 'numeric', month: 'short'})})</span></div>`; dividerDone = true; }
    if (e.date !== day) { day = e.date; html += `<div class="day-h">${fmtDate(e.date, {weekday: 'long', day: 'numeric', month: 'long', year: e.date.slice(0, 4) === D.asof.slice(0, 4) ? undefined : 'numeric'})}<span>${ago(D.asof, e.date)}</span></div>`; }
    html += row(e);
  }
  if (items.length > shown) html += `<button type="button" class="more" id="f-more">Show ${Math.min(PAGE_SIZE, items.length - shown)} more of ${(items.length - shown).toLocaleString('en')}</button>`;
  $('#f-list').innerHTML = html || '<p style="padding:24px;color:var(--i-dim)">Nothing matches these filters. Widen the period or clear a filter.</p>';
  writeState();
  drawMap(items);
  detail(D.events.find(e => e.id === F.sel));
  showView();
  if (scrollToSel) $('#f-list .ev[aria-selected="true"]')?.scrollIntoView({block: 'nearest'});
}

function row(e) {
  const [cl, cw] = corroboration(e);
  return `
    <div class="ev" role="option" tabindex="-1" data-id="${e.id}" aria-selected="${e.id === F.sel}">
      <div class="when">${fmtDate(e.date, {day: '2-digit', month: 'short'})}<small>${ago(D.asof, e.date)}</small></div>
      <span class="tb" style="background:${tColor(e.type)}"></span>
      <span class="iso">${iso(e.country)}</span>
      <div>${e.content_type !== 'event' ? `<span class="ctype">${esc(e.content_type)}</span>` : ''}
        <div class="hd">${esc(e.title)}</div><div class="sm">${esc(e.summary)}</div>
        <div class="tags"><span>${tLabel(e.type)}</span><span>${e.n_sources} source${e.n_sources > 1 ? 's' : ''}</span>${e.story_n ? `<span class="more-n">+${e.story_n} more record${e.story_n > 1 ? 's' : ''}</span>` : ''}${e.precision === 'country' ? '<span>country-level location</span>' : ''}<span class="ai-tag">${e.reviewed ? 'Analyst-reviewed' : 'Machine-coded · unreviewed'}</span></div></div>
      <div class="right"><span class="sal ${e.sal}">${e.sal}</span><span class="corr ${cl}" title="${cw}">${cw}</span></div>
    </div>`;
}

const STOP = new Set('about after against their there where which while with from into that this have been were will would could said says over under between during government gobierno contra para desde sobre entre como tras ante según'.split(' '));
const words = t => new Set((t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').match(/[a-z]{5,}/g)?.filter(w => !STOP.has(w)) || []);
function related(e, n = 4) {
  const w = words(e.title + ' ' + e.summary);
  return D.events.filter(x => x.id !== e.id && x.country === e.country && Math.abs(days(x.date) - days(e.date)) <= 30)
    .map(x => { let k = 0; words(x.title + ' ' + x.summary).forEach(t => { if (w.has(t)) k++; }); return [k + (x.type === e.type ? .5 : 0), x]; })
    .filter(([k]) => k >= 1.5).sort((a, b) => b[0] - a[0]).slice(0, n).map(([, x]) => x);
}

const METHOD = {rss: 'RSS feed', google_news_rss: 'Google News search', google_news_window: 'Google News search', newsapi: 'NewsAPI', wordpress_archive: 'Publisher archive', gdelt: 'GDELT', backfilled_from_event_store: 'Publisher link', manual_web_audit: 'Manual audit'};
const pretty = v => String(v || '').replaceAll('_', ' ');

function detail(e) {
  const el = $('#f-rec');
  if (!e) { el.innerHTML = ''; return; }
  const k = e.coding, rel = related(e);
  const lead = e.story || (e.story_n ? e.id : null);
  const story = lead ? D.events.filter(x => x.id !== e.id && (x.id === lead || x.story === lead)) : [];
  const dated = k?.date_precision === 'day' ? 'day reported' : k?.date_precision === 'month' ? 'month reported; shown by publication date' : k ? 'dated by publication' : null;
  el.innerHTML = `
    <div>
      <div class="kicker" style="display:flex;gap:10px;flex-wrap:wrap"><span style="color:${tColor(e.type)};filter:brightness(1.6)">■</span>${tLabel(e.type)} · ${esc(e.country)} · ${fmtDate(e.date)}</div>
      ${e.content_type !== 'event' ? `<span class="ctype" style="margin-top:8px">${esc(e.content_type)} · dated by publication</span>` : ''}<h2 style="margin-top:8px">${esc(e.title)}</h2>
      <p style="color:var(--i-ink);margin:10px 0 0;font-family:var(--f-display);font-size:17px;line-height:1.5">${esc(e.summary)}</p>
      <p style="color:var(--i-dim);margin:8px 0 0;font-size:13px">Coded as ${esc(tLabel(e.type).toLowerCase())}${e.location ? ` in ${esc(e.location)}` : ''}, ${esc(e.sal)} salience, ${esc(e.conf)} coding confidence${e.actor ? `; initiated by ${esc(plainActor(e.actor))}${e.target ? ` against ${esc(plainActor(e.target))}` : ''}` : ''}.</p>
    </div>
    <div><div class="panel-title" style="margin-bottom:8px"><span>Coding</span><span class="mono">${k ? `codebook v${esc(k.codebook_version)}` : 'taxonomy v2 · legacy'}</span></div>
      <dl class="dl">
        <dt>Type</dt><dd>${k?.type ? `${esc(pretty(k.type))}${k.subtype ? ` · ${esc(pretty(k.subtype))}` : ''}` : tLabel(e.type)}</dd>
        <dt>Salience</dt><dd>${esc(e.sal)}</dd>
        <dt>Confidence</dt><dd>${esc(e.conf)}</dd>
        ${k?.deed_category ? `<dt>DEED category</dt><dd>${esc(pretty(k.deed_category))}</dd>` : e.deed ? `<dt>DEED role</dt><dd>${esc(e.deed)}</dd>` : ''}
        ${k?.actors?.length ? `<dt>Actors</dt><dd>${k.actors.map(a => `${esc(a.name)} <span class="prec">${esc(pretty(a.role))}</span>`).join('<br>')}</dd>` : e.actor ? `<dt>Actor → target</dt><dd>${esc(pretty(e.actor))} → ${esc(pretty(e.target || '—'))}</dd>` : ''}
        ${e.location ? `<dt>Location</dt><dd>${esc(e.location)} <span class="prec">${e.precision === 'place' ? 'mapped to place' : 'country-level point'}</span></dd>` : ''}
        ${dated ? `<dt>Date</dt><dd>${esc(dated)}</dd>` : ''}
        <dt>Corroboration</dt><dd>${corroboration(e)[1]} · ${e.n_sources} source${e.n_sources > 1 ? 's' : ''}</dd>
      </dl></div>
    ${k?.evidence?.length ? `<div><div class="panel-title" style="margin-bottom:2px"><span>Evidence for the coding</span><span class="mono">quoted from the report</span></div>
      ${k.evidence.map(q => `<blockquote class="src-x" style="margin:10px 0 0">${esc(q)}</blockquote>`).join('')}</div>` : ''}
    <div><div class="panel-title" style="margin-bottom:2px"><span>What the sources report</span><span class="mono">${e.sources.length} linked</span></div>
      ${e.sources.map(s => `<div class="src">
        <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a><span class="m">${s.tier ? 'tier ' + s.tier : ''}</span>
        ${s.headline && s.headline !== e.title ? `<span class="src-h">${esc(s.headline)}</span>` : ''}
        ${s.excerpt ? `<blockquote class="src-x">${esc(s.excerpt)}</blockquote>` : '<span class="src-none">No excerpt stored for this report.</span>'}
        <span class="m" style="grid-column:1/-1">${esc(METHOD[s.method] || pretty(s.method))}${s.method ? ' · ' : ''}<a href="${esc(s.url)}" target="_blank" rel="noopener" style="color:var(--i-amber)">Read at source ↗</a></span></div>`).join('')}</div>
    ${story.length ? `<div><div class="panel-title" style="margin-bottom:4px"><span>Other records of this story</span><span class="mono">${story.length}</span></div>
      ${story.map(x => `<a class="rel" href="?e=${x.id}" data-id="${x.id}"><span class="m">${fmtDate(x.date, {day: 'numeric', month: 'short'})}</span><span>${esc(x.title)}<small>${esc(x.sources[0]?.name || '')} · ${tLabel(x.type)}</small></span></a>`).join('')}</div>` : ''}
    <div><div class="panel-title" style="margin-bottom:4px"><span>Related coverage</span><span class="mono">${esc(e.country)} · ±30 days</span></div>
      ${rel.length ? rel.map(x => `<a class="rel" href="?e=${x.id}" data-id="${x.id}"><span class="m">${fmtDate(x.date, {day: 'numeric', month: 'short'})}</span><span>${esc(x.title)}<small>${tLabel(x.type)} · ${x.n_sources} source${x.n_sources > 1 ? 's' : ''}</small></span></a>`).join('')
        : '<p style="margin:4px 0 0;font-size:13px;color:var(--i-faint)">No closely related events within a month.</p>'}</div>
    ${e.analysis ? `<div class="ai-box"><div class="panel-title"><span>Interpretation</span><span class="mono">${e.ai ? 'AI-assisted' : 'automated · rule-based'}</span></div>${esc(e.analysis).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n\n/g, '<br><br>')}</div>` : ''}
    <div><div class="panel-title" style="margin-bottom:4px"><span>Provenance</span><span class="mono">record ${esc(e.id)}</span></div>
      <ul class="prov">
        <li class="done"><i></i>Collected from ${e.n_sources} report${e.n_sources > 1 ? 's' : ''}<span class="m">${fmtDate(e.date, {day: 'numeric', month: 'short'})}</span></li>
        <li class="done"><i></i>${k ? `Coded against codebook v${esc(k.codebook_version)} by ${esc(k.coded_by || 'Claude')}` : 'Classified with the v2 prompt (Claude Haiku)'}<span class="m">auto</span></li>
        <li class="done"><i></i>Merged with same-incident reports<span class="m">auto</span></li>
        <li class="${e.reviewed ? 'done' : 'pend'}"><i></i>Analyst review<span class="m">${e.reviewed ? 'reviewed' : 'not reviewed'}</span></li>
        <li class="done"><i></i>Published to the public layer<span class="m">nightly</span></li>
      </ul></div>
    <p class="mono" style="font-size:11px;color:var(--i-faint);margin:0">Permanent page, with citation · <a href="${page.dataset.base}events/${esc(e.id)}/" style="color:var(--i-amber)">${esc(location.origin + page.dataset.base)}events/${esc(e.id)}/</a></p>`;
  $('#f-detail').scrollTop = 0;
}

function select(id, scroll) { F.sel = id; view = 'record'; draw(scroll); }

/* ── Map pane ── */

const svgNS = 'http://www.w3.org/2000/svg';
const fm = $('#fm');
const P = fm ? JSON.parse(fm.dataset.proj) : null;
const CENTROID = fm ? JSON.parse(fm.dataset.centroids) : {};
const mercY = lat => Math.log(Math.tan(Math.PI / 4 + (Math.max(-85, Math.min(85, lat)) * Math.PI / 180) / 2));
// The build's Mercator projection (lib/geo.mjs fitMercator), so dots land where the base map puts places.
const projectXY = ([lat, lon]) => [P.pad + (lon - P.x0) * Math.PI / 180 * P.k, P.pad + (P.y1 - mercY(lat)) * P.k];
const node = (tag, attrs, text) => { const n = document.createElementNS(svgNS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text != null) n.textContent = text; return n; };

function drawMap(items) {
  if (!fm) return;
  const events = items.filter(e => e.content_type === 'event');
  const by = {};
  for (const e of events) {
    const c = (by[e.country] ||= {n: 0, high: 0, types: {}});
    c.n++; if (e.sal === 'high') c.high++; c.types[e.type] = (c.types[e.type] || 0) + 1;
  }
  const max = Math.max(1, ...Object.values(by).map(c => c.n));
  const bubbles = $('#fm-bubbles'), dots = $('#fm-dots'), sel = $('#fm-sel');
  bubbles.replaceChildren(); dots.replaceChildren(); sel.replaceChildren();
  fm.querySelectorAll('.fm-c').forEach(p => {
    const name = p.dataset.name;
    p.classList.toggle('on', F.country === name);
    p.classList.toggle('dim', F.country !== 'all' && F.country !== name);
    p.classList.toggle('has', !!by[name]);
  });
  for (const e of events) {
    if (!e.coords || e.precision !== 'place') continue;
    const [x, y] = projectXY(e.coords);
    const dot = node('circle', {cx: x.toFixed(1), cy: y.toFixed(1), r: e.sal === 'high' ? 3.6 : 2.4, fill: tColor(e.type), stroke: 'var(--olive)', 'stroke-width': .8, class: 'fm-dot', 'data-id': e.id, tabindex: 0, role: 'button'});
    dot.append(node('title', {}, `${e.location || e.country} · ${fmtDate(e.date, {day: 'numeric', month: 'short'})} · ${e.title}`));
    dots.append(dot);
  }
  for (const [name, c] of Object.entries(by).sort((a, b) => b[1].n - a[1].n)) {
    const at = CENTROID[name];
    if (!at) continue;
    const dom = Object.entries(c.types).sort((a, b) => b[1] - a[1])[0][0];
    const r = 7 + Math.sqrt(c.n / max) * 15;
    const g = node('g', {class: `fm-b${F.country === name ? ' on' : ''}`, transform: `translate(${at[0]},${at[1]})`, 'data-name': name, tabindex: 0, role: 'button', 'aria-label': `${name}: ${c.n} records in view. Filter the list to ${name}.`});
    g.append(node('title', {}, `${name}: ${c.n} record${c.n === 1 ? '' : 's'} in view${c.high ? `, ${c.high} high salience` : ''}; mostly ${tLabel(dom).toLowerCase()}`));
    g.append(node('circle', {r: r.toFixed(1), fill: tColor(dom), 'fill-opacity': .88, stroke: c.high ? 'var(--st-crisis-i)' : 'var(--olive)', 'stroke-width': c.high ? 1.6 : 1}));
    g.append(node('text', {'text-anchor': 'middle', dy: '.35em'}, c.n));
    bubbles.append(g);
  }
  const s = F.sel && D.events.find(e => e.id === F.sel);
  if (s) {
    const at = s.coords && s.precision === 'place' ? projectXY(s.coords) : CENTROID[s.country];
    if (at) sel.append(node('circle', {cx: (+at[0]).toFixed(1), cy: (+at[1]).toFixed(1), r: 9, fill: 'none', stroke: 'var(--i-amber)', 'stroke-width': 2, class: 'fm-ring'}));
  }
  const period = F.period ? `past ${F.period} days` : 'all dates';
  $('#f-maplbl').textContent = `${events.length.toLocaleString('en')} events · ${period}`;
  $('#f-top').innerHTML = Object.entries(by).sort((a, b) => b[1].n - a[1].n).slice(0, 8).map(([name, c]) =>
    `<li><button type="button" data-name="${esc(name)}" aria-pressed="${F.country === name}"><span>${esc(name)}</span><span class="bar"><i style="width:${(c.n / max * 100).toFixed(0)}%"></i></span><b class="mono">${c.n}</b></button></li>`).join('')
    || '<li class="none">No events in view.</li>';
}

function showView() {
  const rec = view === 'record' && F.sel;
  $('#f-map').hidden = !!rec; $('#f-rec').hidden = !rec;
  $('#t-map').setAttribute('aria-selected', String(!rec)); $('#t-rec').setAttribute('aria-selected', String(!!rec));
  $('#t-rec').disabled = !F.sel;
  $('#f-hint').hidden = !!F.sel;
}

const toggleCountry = name => { F.country = F.country === name ? 'all' : name; shown = PAGE_SIZE; syncControls(); draw(); };

async function start() {
  readState();
  syncControls();
  try {
    D = await (await fetch(page.dataset.feed)).json();
  } catch {
    $('#f-count').textContent = 'The event data could not be loaded. Reload the page to try again.';
    return;
  }
  ISO = Object.fromEntries(D.countries.map(c => [c.name, c.iso3]));
  if (D.aliases?.[F.sel]) F.sel = D.aliases[F.sel];
  try { localStorage.setItem('sentinel.feed.lastVisit', D.asof); } catch { /* storage is optional */ }
  if (F.sel) view = 'record';
  draw(true);

  const panel = $('#f-panel');
  const setOpen = open => { panel.classList.toggle('open', open); $('#f-toggle').setAttribute('aria-expanded', open); };
  $('#f-toggle').addEventListener('click', () => setOpen(!panel.classList.contains('open')));
  $('#f-close').addEventListener('click', () => setOpen(false));
  $('#f-country').addEventListener('change', e => { F.country = e.target.value; shown = PAGE_SIZE; draw(); });
  panel.addEventListener('click', e => {
    const b = e.target.closest('[data-f]'); if (!b) return;
    F[b.dataset.f] = b.dataset.f === 'period' ? +b.dataset.v : b.dataset.v;
    shown = PAGE_SIZE; syncControls(); draw();
  });
  $('#f-list').addEventListener('click', e => {
    if (e.target.closest('#f-more')) { shown += PAGE_SIZE; draw(); return; }
    const r = e.target.closest('.ev'); if (r) select(r.dataset.id);
  });
  $('#f-detail').addEventListener('click', e => {
    const a = e.target.closest('a.rel');
    if (a) { e.preventDefault(); select(a.dataset.id, true); return; }
    const tab = e.target.closest('[data-view]');
    if (tab && !tab.disabled) { view = tab.dataset.view; showView(); return; }
    const zoom = e.target.closest('[data-zoom]');
    if (zoom) {
      fm.setAttribute('viewBox', JSON.parse(fm.dataset.zooms)[zoom.dataset.zoom].join(' '));
      document.querySelectorAll('[data-zoom]').forEach(b => b.setAttribute('aria-pressed', String(b === zoom)));
      return;
    }
    const dot = e.target.closest('.fm-dot');
    if (dot) { select(dot.dataset.id, true); return; }
    const place = e.target.closest('.fm-b, .fm-c, .fm-top button');
    if (place) toggleCountry(place.dataset.name);
  });
  $('#f-detail').addEventListener('keydown', e => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const t = e.target.closest('.fm-dot, .fm-b');
    if (!t) return;
    e.preventDefault();
    t.classList.contains('fm-dot') ? select(t.dataset.id, true) : toggleCountry(t.dataset.name);
  });
  document.addEventListener('keydown', ev => {
    if (ev.target.closest('input, select, textarea') || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (ev.key !== 'j' && ev.key !== 'k') return;
    const rows = [...document.querySelectorAll('#f-list .ev')];
    if (!rows.length) return;
    const i = rows.findIndex(r => r.getAttribute('aria-selected') === 'true');
    select(rows[Math.min(rows.length - 1, Math.max(0, i + (ev.key === 'j' ? 1 : -1)))].dataset.id, true);
    ev.preventDefault();
  });
  window.addEventListener('popstate', () => { readState(); view = F.sel ? 'record' : 'map'; syncControls(); draw(true); });
  const setChrome = () => document.documentElement.style.setProperty('--chrome', (page.getBoundingClientRect().top + window.scrollY) + 'px');
  setChrome(); window.addEventListener('resize', setChrome);
}
start();
