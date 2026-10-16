// Live feed shell. The stream and detail pane are rendered in the browser from
// data/feed.json (see client/feed.js), because filtering is the point of the page.

import {esc, tLabel} from '../lib/html.mjs';
import {layout} from './layout.mjs';
import {feedMap, ZOOM_LABELS} from './maps.mjs';

export function renderFeed(model, ctx) {
  const types = [...new Set(model.events.map(e => e.type))];
  const chips = (key, opts, current) => opts.map(([v, l]) => `<button class="fchip" type="button" data-f="${key}" data-v="${v}" aria-pressed="${String(v) === String(current)}">${l}</button>`).join('');
  const body = `
  <div class="instr feed-page" data-feed="${ctx.url('data/feed.json')}" data-base="${ctx.url('')}">
    <h1 class="visually-hidden">Live feed</h1>
    ${model.pending ? `<div class="feed-pending" role="note">Coding is paused: ${model.pending.headlines.length} newer headlines have been collected but not yet coded. <a href="${ctx.url('headlines/')}">See them →</a></div>` : ''}
    <div class="feed-grid">
      <aside class="filters" aria-label="Feed filters" id="f-panel">
        <button class="f-rail" type="button" aria-controls="f-body" aria-expanded="false" id="f-toggle">
          <svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 3.5h11l-4.2 4.6v3.1l-2.6 1.3V8.1z" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>
          <span class="lbl">Filters</span><span class="cnt" id="f-active" hidden></span>
        </button>
        <div class="f-body" id="f-body">
          <button class="f-close" type="button" id="f-close">Close filters</button>
          <div class="fgroup" role="group" aria-label="Show"><div class="panel-title" aria-hidden="true">Show</div><div class="fchips">${chips('content', [['event', 'Events'], ['analysis', 'Analysis & profiles'], ['all', 'Everything']], 'event')}</div></div>
          <div class="fgroup"><label class="panel-title" for="f-country">Country</label>
            <select class="fselect" id="f-country"><option value="all">All ${model.countries.length} countries</option>${model.countries.map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join('')}<option value="Regional">Regional</option></select></div>
          <div class="fgroup" role="group" aria-label="Period"><div class="panel-title" aria-hidden="true">Period</div><div class="fchips">${chips('period', [[7, '7 days'], [30, '30 days'], [90, '90 days'], [365, '1 year'], [0, 'All']], 90)}</div></div>
          <div class="fgroup" role="group" aria-label="Salience"><div class="panel-title" aria-hidden="true">Salience</div><div class="fchips">${chips('sal', [['all', 'All'], ['high', 'High'], ['medium', 'Medium'], ['low', 'Low']], 'all')}</div></div>
          <div class="fgroup" role="group" aria-label="Coding confidence"><div class="panel-title" aria-hidden="true">Coding confidence</div><div class="fchips">${chips('conf', [['all', 'All'], ['high', 'High'], ['medium', 'Medium'], ['low', 'Low']], 'all')}</div></div>
          <div class="fgroup" role="group" aria-label="Event type"><div class="panel-title" aria-hidden="true">Event type</div><div class="fchips">${chips('type', [['all', 'All'], ...types.map(t => [t, tLabel(t)])], 'all')}</div></div>
          <div class="fgroup" role="group" aria-label="Review state"><div class="panel-title" aria-hidden="true">Review state</div><div class="fchips">${chips('rev', [['all', 'All'], ['reviewed', 'Analyst-reviewed']], 'all')}</div></div>
          <p style="margin:0;font-size:12px;color:var(--i-faint)">The address bar keeps your filters and selection, so any view can be shared or cited. Keys: j / k to move.</p>
        </div>
      </aside>
      <section class="stream" aria-label="Event stream" id="f-stream"><div class="stream-head"><span id="f-count">Loading events…</span><span id="f-sum"></span></div><div id="f-list" role="listbox" aria-label="Events"></div></section>
      <section class="detail" id="f-detail" tabindex="-1">
        <div class="pane-tabs" role="tablist" aria-label="Right pane">
          <button type="button" role="tab" id="t-map" data-view="map" aria-selected="true">Map</button>
          <button type="button" role="tab" id="t-rec" data-view="record" aria-selected="false" disabled>Record</button>
          <span class="pane-hint" id="f-hint">Select an event to open its record</span>
        </div>
        <div id="f-map" class="fmap" role="tabpanel" aria-labelledby="t-map">
          <div class="panel-title"><span>Country pressure surface</span><span class="mono" id="f-maplbl"></span></div>
          <div class="fm-zoom" role="group" aria-label="Zoom to a subregion">${ZOOM_LABELS.map(([k, l], i) => `<button type="button" data-zoom="${k}" aria-pressed="${i === 0}">${l}</button>`).join('')}</div>
          <div class="fm-wrap">${feedMap(model)}</div>
          <div class="map-legend fm-legend"><span><i class="lg-b"></i>Events in view, by country; colour is the most common type</span><span><i class="lg-d"></i>Event placed at a town or region</span><span><i class="lg-s"></i>Selected record</span></div>
          <p class="fm-help">Click a country or its bubble to filter the list; click again to clear. Click a dot to open its record.</p>
          <div class="panel-title" style="margin-top:6px"><span>Most active in view</span><span class="mono">records</span></div>
          <ol class="fm-top" id="f-top"></ol>
        </div>
        <div id="f-rec" role="tabpanel" aria-labelledby="t-rec" aria-live="polite" hidden></div>
      </section>
    </div>
    <noscript><p style="padding:24px">The live feed needs JavaScript to filter events. The <a href="${ctx.url('countries/')}">country monitors</a> list recent events without it.</p></noscript>
  </div>`;
  return layout(ctx, {title: 'Live feed', description: 'Every coded civil–military and security event, with sources, coding and review state.', nav: 'feed', body, scripts: ['feed.js'], app: true});
}
