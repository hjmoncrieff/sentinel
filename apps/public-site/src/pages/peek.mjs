// Hover cards and the year strip, shared by the topic pages and the country monitors.
// A page collects the cards it needs while it renders; they ship once, as <template>s at the foot
// of the page, and client/peek.js shows them on hover, keyboard focus or tap. client/topic.js
// filters the strip and the story list together.

import {esc, fmtDate, tColor, tLabel} from '../lib/html.mjs';
import {eventUrl} from './event.mjs';

export const SAL = {high: 0, medium: 1, low: 2};
export const COLLECTION_NOTE = 'Counts reflect how much was collected as well as what happened: collection started in March 2026 and was irregular until October 2026, and earlier dates come from archive searches.';

export const trim = (s, n) => s.length > n ? `${s.slice(0, n).replace(/\s+\S*$/, '')}…` : s;
export const shiftDay = (d, n) => new Date(Date.parse(`${d.length === 7 ? `${d}-01` : d}T00:00:00Z`) + n * 864e5).toISOString().slice(0, 10);
const SAL_WORD = {high: 'High', medium: 'Medium', low: 'Low'};

export function peekBook(model, ctx) {
  const cards = new Map();
  const day = d => fmtDate(d, {day: 'numeric', month: 'short', year: 'numeric'});
  const rec = e => `<li><a href="${eventUrl(ctx, e.id)}"><span class="mono">${fmtDate(e.date, {day: 'numeric', month: 'short', year: '2-digit'})} · ${esc(model.byName[e.country]?.iso3 || e.country)}</span>${esc(e.title)}</a></li>`;
  const records = (list, total, empty) => list.length
    ? `<div class="pk-sub">In the SENTINEL archive · ${total} record${total > 1 ? 's' : ''}</div><ul class="pk-recs">${list.map(rec).join('')}</ul>`
    : `<div class="pk-sub">In the SENTINEL archive</div><p class="pk-none">${esc(empty)}</p>`;
  return {
    model, ctx, records,
    event(e) {
      const k = `e-${e.id}`;
      if (!cards.has(k)) {
        const actors = [...new Set((e.coding?.actors || []).map(a => a.name).filter(Boolean))].slice(0, 5);
        cards.set(k, `<div class="pk-kick"><i class="pk-dot" style="background:${tColor(e.type)}"></i>${tLabel(e.type)} · ${esc(e.country)} · ${day(e.date)}</div>
          <div class="pk-title">${esc(e.title)}</div>${e.summary && e.summary !== e.title ? `<p>${esc(trim(e.summary, 300))}</p>` : ''}
          ${actors.length ? `<div class="pk-actors">${actors.map(a => `<span>${esc(a)}</span>`).join('')}</div>` : ''}
          <div class="pk-foot"><span>${SAL_WORD[e.sal] || ''} salience · ${e.n_sources} source${e.n_sources > 1 ? 's' : ''}${e.sources[0] ? ` · ${esc(e.sources[0].name)}` : ''}</span><a href="${eventUrl(ctx, e.id)}">Open record →</a></div>`);
      }
      return ` data-peek="${k}"`;
    },
    add(k, html) { cards.set(k, html); return ` data-peek="${esc(k)}"`; },
    html: () => `<div hidden>${[...cards].map(([k, h]) => `<template id="pk-${esc(k)}">${h}</template>`).join('')}</div>`,
  };
}

// A year of events on one strip per lane, with dated milestones above. Every dot and marker opens a card.
export function pulseStrip(model, ctx, book, events, lanes, milestones, {label, pick = 'a kind of event'}) {
  const to = model.asof, from = shiftDay(to, -364), span = 364;
  const W = 960, L = 178, R = 12, TOP = 30, LH = 30, B = 22, H = TOP + LH * lanes.length + B;
  const x = d => L + (W - L - R) * Math.min(1, Math.max(0, (Date.parse(`${d}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 864e5 / span));
  const hash = s => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  const laneOf = e => lanes.find(l => l.test(e)) || lanes.at(-1);
  const placed = events.filter(e => e.date >= from && e.date <= to).map(e => ({e, l: laneOf(e)}));
  const counts = Object.fromEntries(lanes.map(l => [l.key, placed.filter(p => p.l === l).length]));
  const months = Array.from({length: 12}, (_, i) => new Date(Date.UTC(+to.slice(0, 4), +to.slice(5, 7) - 12 + i, 1)).toISOString().slice(0, 10)).filter(d => d >= from);
  const mLabel = d => `${new Date(`${d}T00:00:00Z`).toLocaleDateString('en-GB', {timeZone: 'UTC', month: 'short'})}${d.slice(5, 7) === '01' ? ` ${d.slice(0, 4)}` : ''}`;
  // A month that starts too close to the right edge keeps its gridline but not its label.
  const grid = months.map(d => `<line x1="${x(d).toFixed(1)}" x2="${x(d).toFixed(1)}" y1="${TOP - 4}" y2="${H - B}" stroke="var(--rule-2)"/>${x(d) > W - R - 34 ? '' : `<text x="${(x(d) + 3).toFixed(1)}" y="${H - 7}">${mLabel(d)}</text>`}`).join('');
  const rows = lanes.map((l, i) => `<g class="pl-row" data-ln="${l.key}"><line x1="${L}" x2="${W - R}" y1="${TOP + LH * i + LH / 2}" y2="${TOP + LH * i + LH / 2}" stroke="var(--rule)"/>
    <text class="pl-lbl" x="0" y="${TOP + LH * i + LH / 2}" dy=".32em">${esc(l.label)}</text><text x="${L - 8}" y="${TOP + LH * i + LH / 2}" dy=".32em" text-anchor="end">${counts[l.key]}</text></g>`).join('');
  const dots = placed.sort((a, b) => SAL[b.e.sal] - SAL[a.e.sal]).map(({e, l}) => {
    const i = lanes.indexOf(l), cy = TOP + LH * i + LH / 2 + ((hash(e.id) % 17) - 8) * .9, r = e.sal === 'high' ? 5 : e.sal === 'medium' ? 3.6 : 2.6;
    return `<a class="pl-dot" data-ln="${l.key}" href="${eventUrl(ctx, e.id)}"${book.event(e)} aria-label="${esc(`${e.date}, ${e.country}: ${e.title}`)}"><circle cx="${x(e.date).toFixed(1)}" cy="${cy.toFixed(1)}" r="${r}" fill="${l.color}" fill-opacity="${e.sal === 'high' ? .95 : .6}"/></a>`;
  }).join('');
  let last = -99, tier = 0;
  const marks = milestones.filter(m => m.key && m.at >= from && m.at <= to).sort((a, b) => a.at.localeCompare(b.at)).map(m => {
    const mx = x(m.at); tier = mx - last < 14 ? (tier + 1) % 2 : 0; last = mx;
    const my = 8 + tier * 10;
    return `<g class="pl-ms" tabindex="0" role="button" aria-label="${esc(`Milestone: ${m.title}`)}" data-peek="${m.key}"><line x1="${mx.toFixed(1)}" x2="${mx.toFixed(1)}" y1="${my + 5}" y2="${H - B}" stroke="var(--amber)" stroke-dasharray="2 3" stroke-opacity=".55"/><circle cx="${mx.toFixed(1)}" cy="${my}" r="10" fill="transparent"/><path d="M${mx.toFixed(1)},${my - 5}l5,5l-5,5l-5,-5z" fill="var(--paper)" stroke="var(--amber)" stroke-width="1.5"/></g>`;
  }).join('');
  return `
    <div class="pl-chips" role="group" aria-label="${esc(`Show ${pick}`)}">${lanes.map(l => `<button type="button" class="pl-chip" data-ln="${l.key}" aria-pressed="false"><i style="background:${l.color}"></i>${esc(l.label)} <b class="mono">${counts[l.key]}</b></button>`).join('')}</div>
    <div class="plstrip tbl-scroll"><svg viewBox="0 0 ${W} ${H}" role="group" aria-label="${esc(label)}">${grid}${rows}${dots}${marks}</svg></div>
    <p class="note">Each dot is one record, sized by salience; hover or tab to a dot for the record${marks ? ', or to a ◆ milestone for what happened and the records around it' : ''}. Choose ${pick} to filter the strip and the list below. ${COLLECTION_NOTE}</p>`;
}

