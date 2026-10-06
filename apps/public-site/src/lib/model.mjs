// Build-time data model. Reads only public layers: data/published/, the structural file
// data/cleaned/us_assistance.json, and the site's own reference and content files.

import fs from 'node:fs';
import path from 'node:path';
import {daysBetween} from './html.mjs';

const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const readOptional = file => (fs.existsSync(file) ? readJson(file) : null);

const STRUCTURAL_SOURCE = {
  polyarchy: 'V-Dem v16', mil_constrain: 'V-Dem v16', mil_exec: 'V-Dem v16',
  wgi_rule_of_law: 'World Bank WGI', mil_exp_pct_gdp: 'World Bank WDI', inflation_consumer_prices_pct: 'World Bank WDI',
};

function toEvent(e) {
  const sources = (e.linked_reports || []).map(r => ({
    name: r.source_name, url: r.url, headline: r.headline, excerpt: r.description || null,
    tier: r.source_tier ?? null, method: r.source_method || null,
  })).filter(s => s.name);
  if (!sources.length && e.source_primary) sources.push({name: e.source_primary, url: e.url_primary, headline: null, excerpt: null, tier: null, method: null});
  const initiator = (e.actors || []).find(a => a.actor_role_in_event === 'initiator' || a.actor_role_in_event === 'primary');
  const target = (e.actors || []).find(a => a.actor_role_in_event === 'target');
  return {
    id: e.event_id,
    date: e.event_date,
    country: e.country,
    type: e.event_type || 'other',
    subtype: e.event_subtype || null,
    sal: e.salience || 'low',
    conf: e.confidence || 'medium',
    title: (e.headline || '').trim(),
    summary: e.summary || '',
    location: e.subnational_location || null,
    coords: e.latitude != null && e.longitude != null ? [e.latitude, e.longitude] : null,
    precision: e.location_precision || 'country',
    content_type: e.content_type || 'event',
    sources,
    n_sources: Math.max(sources.length, (e.source_all || []).length, 1),
    deed: e.deed_type || null,
    actor: initiator?.actor_canonical_group || initiator?.actor_group || null,
    target: target?.actor_canonical_group || target?.actor_group || null,
    constructs: e.event_construct_destinations || [],
    coding: e.public_coding || null,
    analysis: e.public_analysis || null,
    ai: !!e.public_ai_generated,
    reviewed: !!(e.human_validated || e.provenance_summary?.reviewed_by_human),
  };
}

function countryModel(ref, monitor, dossier, events, asof) {
  const mine = events.filter(e => e.country === ref.name);
  const spark = Array.from({length: 60}, () => 0);
  for (const e of mine) { const n = daysBetween(asof, e.date); if (n >= 0 && n < 60) spark[59 - n]++; }
  const within = d => mine.filter(e => { const n = daysBetween(asof, e.date); return n >= 0 && n <= d; });
  const ps = monitor?.predictive_summary || {};
  const typeMix = {};
  for (const e of within(365)) if (e.content_type === 'event') typeMix[e.type] = (typeMix[e.type] || 0) + 1;
  // Twelve calendar months ending with the "as of" month, counted by event family.
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const key = new Date(Date.UTC(+asof.slice(0, 4), +asof.slice(5, 7) - 1 - i, 1)).toISOString().slice(0, 7);
    const by = {};
    for (const e of mine) if (e.content_type === 'event' && e.date.startsWith(key)) by[e.type] = (by[e.type] || 0) + 1;
    months.push({key, by, total: Object.values(by).reduce((a, b) => a + b, 0)});
  }
  const salRank = {high: 0, medium: 1, low: 2};
  const evidence = code => within(90).filter(e => e.content_type === 'event' && e.constructs.includes(code))
    .sort((a, b) => salRank[a.sal] - salRank[b.sal] || a.constructs.length - b.constructs.length || b.date.localeCompare(a.date));
  return {
    ...ref,
    outlook: {
      level: ps.overall_risk_level || null,
      trend: ps.leading_trend || 'stable',
      leading: ps.leading_label || null,
      summary: ps.summary_text || dossier?.public_summary?.summary_text || null,
      watch: ps.watchpoints || [],
    },
    constructs: (monitor?.risk_constructs || []).map(k => ({
      code: k.code, label: k.label, level: k.level, trend: k.trend_label,
      drivers: (k.drivers || []).map(d => d.label), summary: k.summary_text, watch: k.watchpoints || [],
      evidence: evidence(k.code),
    })),
    monitors: (monitor?.monitors || []).map(m => ({code: m.code, label: m.label, goal: m.goal, trend: m.trend_label, signal: m.dominant_recent_signal})),
    structural: (dossier?.public_structural_cards || []).map(s => ({
      code: s.code, label: s.label, value: s.display_value, num: s.current_value, unit: s.unit, year: s.as_of_year,
      series: s.trend_series || [], source: STRUCTURAL_SOURCE[s.code] || '',
    })),
    structural_as_of: dossier?.public_freshness?.structural_as_of_year || null,
    spark,
    n7: within(7).length,
    n30: within(30).length,
    high30: within(30).filter(e => e.sal === 'high').length,
    n365: within(365).length,
    type_mix: Object.entries(typeMix).sort((a, b) => b[1] - a[1]),
    months,
    located: within(365).filter(e => e.content_type === 'event' && e.coords && e.precision === 'place'),
    last: mine[0]?.date || null,
    total: mine.length,
  };
}

export function loadModel(repoRoot, siteRoot) {
  const published = path.join(repoRoot, 'data', 'published');
  const eventsFile = readJson(path.join(published, 'events_public.json'));
  const monitors = readJson(path.join(published, 'country_monitors.json')).countries;
  const dossiers = readJson(path.join(published, 'country_dossiers.json')).countries;
  const reference = readJson(path.join(siteRoot, 'reference', 'countries.json'));
  const topology = readJson(path.join(siteRoot, 'reference', 'americas-topo.json'));
  const weekly = readOptional(path.join(siteRoot, 'content', 'weekly.json'));
  // Structural layer (public): US assistance by funding account, from ForeignAssistance.gov.
  const assistance = readOptional(path.join(repoRoot, 'data', 'cleaned', 'us_assistance.json'));
  const assistanceBy = Object.fromEntries((assistance?.countries || []).map(c => [c.country, c]));

  const events = eventsFile.events.map(toEvent).filter(e => e.id && e.date)
    .sort((a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id));
  // "As of" is the newest event date: every "n days ago" on the site counts from the data, not the build clock.
  const asof = events[0]?.date || eventsFile.generated_at.slice(0, 10);
  const monitorBy = Object.fromEntries(monitors.map(m => [m.country, m]));
  const dossierBy = Object.fromEntries(dossiers.map(d => [d.country, d]));
  const countries = reference.countries.map(ref => countryModel(ref, monitorBy[ref.name], dossierBy[ref.name], events, asof));
  for (const c of countries) c.us_assistance = assistanceBy[c.name] ? {...assistanceBy[c.name], partial_years: assistance.partial_years, groups: assistance.groups} : null;

  // Regional median for each structural indicator, written the way the country's own value is.
  const median = vals => { const v = [...vals].sort((a, b) => a - b), m = v.length >> 1; return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2; };
  for (const code of new Set(countries.flatMap(c => c.structural.map(s => s.code)))) {
    const cards = countries.map(c => c.structural.find(s => s.code === code)).filter(s => typeof s?.num === 'number');
    if (cards.length < 5) continue;
    const mid = median(cards.map(s => s.num));
    for (const s of cards) {
      const decimals = (String(s.value).match(/\.(\d+)/) || ['', ''])[1].length;
      s.median = mid.toFixed(decimals) + (String(s.value).endsWith('%') ? '%' : '');
      s.median_n = cards.length;
    }
  }

  const monthly = [];
  const start = new Date(asof.slice(0, 7) + '-01T00:00:00Z');
  for (let i = 23; i >= 0; i--) {
    const d = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() - i, 1));
    const key = d.toISOString().slice(0, 7);
    monthly.push([key, events.filter(e => e.date.startsWith(key)).length]);
  }
  return {
    asof,
    generated_at: eventsFile.generated_at,
    events,
    countries,
    byName: Object.fromEntries(countries.map(c => [c.name, c])),
    byIso: Object.fromEntries(countries.map(c => [c.iso3, c])),
    subregions: reference.subregions,
    topology,
    weekly,
    assistance,
    monthly,
    sources_total: new Set(events.flatMap(e => e.sources.map(s => s.name))).size,
    first_date: events[events.length - 1]?.date || asof,
    recent: d => events.filter(e => { const n = daysBetween(asof, e.date); return n >= 0 && n <= d; }),
  };
}

const STOP = new Set('para como sobre entre desde hasta contra tras ante este esta estos estas pero porque cuando donde quien that this with from have will after over into amid says said their about more than were been has had its his her the and for los las del una uno unos por con que sus son fue ser han mais das dos uma com nao nos nas pela pelo'.split(' '));
const titleWords = t => new Set(t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').split(/[^a-z0-9]+/).filter(w => w.length > 3 && !STOP.has(w)));

/** Group records that report the same story: within three days of each other and sharing most
 *  of their headline words. Deliberately strict, so two different incidents are never merged.
 *  Each group leads with its highest-salience, best-sourced record. */
export function groupStories(events) {
  const groups = [];
  for (const e of events) {
    const words = titleWords(e.title);
    const hit = groups.find(g => g.some(x => {
      if (Math.abs(daysBetween(x.e.date, e.date)) > 3) return false;
      let shared = 0;
      for (const w of words) if (x.words.has(w)) shared++;
      return shared >= 3 && shared / Math.min(words.size, x.words.size) >= 0.5;
    }));
    hit ? hit.push({e, words}) : groups.push([{e, words}]);
  }
  const rank = {high: 0, medium: 1, low: 2};
  return groups.map(g => {
    const [lead, ...others] = g.map(x => x.e).sort((a, b) => rank[a.sal] - rank[b.sal] || b.n_sources - a.n_sources);
    return {lead, others, date: g[0].e.date};
  });
}

// The slim event list the live feed loads in the browser.
export function feedPayload(model) {
  return {
    asof: model.asof,
    countries: model.countries.map(c => ({name: c.name, iso3: c.iso3})),
    events: model.events.map(({constructs, ...e}) => e),
  };
}
