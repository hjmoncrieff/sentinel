// Headlines collected while automatic coding was unavailable: shown as reports, not as coded events.
// Written by scripts/publish/pending_headlines.py; removed by the next run that codes normally.

import {esc, fmtDate} from '../lib/html.mjs';
import {layout} from './layout.mjs';

export const PENDING_NOTE = 'Automatic coding is paused, so these reports have been collected and keyword-filtered but not yet read, coded or checked. Countries are guessed from the headline. They will be coded, and appear in the feed, when coding resumes.';

// One headline as a link to the publisher; the shared row for the front page and this page.
export function pendingItem(h, model, {country = true} = {}) {
  const c = h.country && model.byName[h.country];
  return `<li><span class="mono">${esc(fmtDate(h.date, {day: 'numeric', month: 'short'}))}${country ? ` · ${c ? esc(c.iso3) : '—'}` : ''}</span><a href="${esc(h.url)}" target="_blank" rel="noopener">${esc(h.title)} <span aria-hidden="true">↗</span></a><small>${esc(h.source)}</small></li>`;
}

export function renderHeadlines(model, ctx) {
  const p = model.pending;
  const days = {};
  for (const h of p?.headlines || []) (days[h.date] ||= []).push(h);
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>Not yet coded</span></div>
    <section class="c-head" style="align-items:start">
      <div><div class="kicker">Collected, not yet coded</div><h1 style="margin-top:8px;font-size:clamp(34px,4.5vw,56px)">Headlines waiting to be coded</h1>
        <p class="dek">${p ? esc(PENDING_NOTE) : 'Coding is running normally; nothing is waiting. Every collected report is coded before it appears in the live feed.'}</p></div>
      ${p ? `<dl class="facts"><dt>Headlines</dt><dd class="mono">${p.headlines.length}</dd><dt>Collected</dt><dd class="mono">${esc(fmtDate(p.generated_at.slice(0, 10)))}</dd><dt>Last coded data</dt><dd class="mono">${esc(fmtDate(model.generated_at.slice(0, 10)))}</dd></dl>` : ''}
    </section>
    ${p ? Object.entries(days).map(([d, hs]) => `
    <section class="section" aria-label="${esc(fmtDate(d))}">
      <div class="sec-head"><h2>${esc(fmtDate(d, {weekday: 'long', day: 'numeric', month: 'long'}))}</h2><span class="kicker">${hs.length} headline${hs.length > 1 ? 's' : ''}</span></div>
      <ul class="pend-list">${hs.map(h => pendingItem(h, model)).join('')}</ul>
    </section>`).join('') : `<p style="margin:var(--s-6) 0"><a href="${ctx.url('feed/')}">Go to the live feed →</a></p>`}
  </div>`;
  return layout(ctx, {title: 'Headlines not yet coded', description: 'Reports SENTINEL has collected but not yet coded, shown while automatic coding is paused.', body});
}
