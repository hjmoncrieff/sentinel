// About and methodology. The codebook tables are generated from
// config/taxonomy/codebook_v3.json, so this page cannot drift from what the coder uses.

import {esc, fmtDate, TYPE} from '../lib/html.mjs';
import {layout} from './layout.mjs';

const SECTIONS = [
  ['what', 'What SENTINEL is'],
  ['record', 'How a record is made'],
  ['codebook', 'The codebook'],
  ['fields', 'Salience, confidence and corroboration'],
  ['labels', 'What the labels mean'],
  ['monitors', 'Country monitors'],
  ['limits', 'Limitations'],
  ['cite', 'Citing and reusing'],
];

export function renderAbout(model, ctx) {
  const cb = model.codebook;
  const field = name => cb.field_groups.flatMap(g => g.fields).find(f => f.name === name)?.rule || '';
  const v3 = model.events.filter(e => e.coding).length, reviewed = model.events.filter(e => e.reviewed).length;
  const single = model.events.filter(e => e.n_sources === 1).length, placed = model.events.filter(e => e.precision === 'place').length;
  // Nine in ten records fall after this date; a few archive records go back much further.
  const bulkStart = model.events[Math.floor(model.events.length * 0.9)]?.date || model.first_date;
  const pct = n => `${Math.round(n / model.events.length * 100)}%`;
  const types = cb.domains.map(d => `
      <tr class="grp"><td colspan="3">${esc(d.label)}</td></tr>${d.types.map(t => `
      <tr><td><b>${esc(t.label)}</b><span class="mono code">${esc(t.code)}</span></td><td>${esc(t.definition)}</td><td>${esc((t.subtypes || []).map(s => s.replaceAll('_', ' ')).join(' · '))}</td></tr>`).join('')}`).join('');
  const h = (id, n) => `<h2 id="${id}">${esc(SECTIONS.find(s => s[0] === id)[1])}</h2>`;
  const body = `
  <div class="wrap">
    <div class="crumbs" style="padding-top:18px"><a href="${ctx.url('')}">Home</a><span>›</span><span>About and methodology</span></div>
    <section class="c-head" style="align-items:start">
      <div><div class="kicker">About · Methodology · Codebook v${esc(cb.version)}</div><h1 style="margin-top:8px;font-size:clamp(38px,5vw,64px)">How SENTINEL works</h1>
        <p style="margin:14px 0 0;color:var(--ink-2);max-width:62ch">SENTINEL monitors civil–military relations, political stability and security in ${model.countries.length} countries of Latin America and the Caribbean. It reads the news every night, codes what happened against a published codebook, and shows each record with its sources. This page says how, and where the method is weak.</p></div>
      <dl class="facts">
        <dt>Records</dt><dd class="mono">${model.events.length.toLocaleString('en')}</dd>
        <dt>Coverage</dt><dd>Mostly ${fmtDate(bulkStart, {month: 'short', year: 'numeric'})} to ${fmtDate(model.asof)}</dd>
        <dt>Sources</dt><dd class="mono">${model.sources_total}</dd>
        <dt>Coded with v${esc(cb.version)}</dt><dd class="mono">${v3.toLocaleString('en')} · ${pct(v3)}</dd>
        <dt>Analyst-reviewed</dt><dd class="mono">${reviewed.toLocaleString('en')} · ${pct(reviewed)}</dd>
      </dl>
    </section>
    <div class="about-grid section" style="padding-top:var(--s-6)">
      <nav class="about-toc" aria-label="On this page"><div class="kicker">On this page</div>${SECTIONS.map(([id, label]) => `<a href="#${id}">${esc(label)}</a>`).join('')}</nav>
      <article class="about">
        ${h('what')}
        <p>SENTINEL is a research monitor. Its subject is who commands the coercive apparatus of the state and on what terms: civilian control of the armed forces, coup-proofing, the military's institutional autonomy, security-sector reform, democratic backsliding with a security dimension, and the interaction of organized crime with state forces. It also follows foreign security cooperation, above all with the United States.</p>
        <p>It is built for people who need to check what they read: each record links to the reports behind it, shows how it was coded, and says whether a person has reviewed it. The code and the public data are in the <a href="https://github.com/hjmoncrieff/sentinel">project repository</a>.</p>

        ${h('record')}
        <ol class="steps">
          <li><b>Collection.</b> Every night the pipeline reads RSS feeds, Google News searches restricted to named publishers, and a news API. Publishers range from wire services and national papers to specialist outlets on defence and organized crime, in English, Spanish and Portuguese.</li>
          <li><b>Keyword filter.</b> A broad keyword list in three languages keeps anything that might be relevant. It is tuned to miss little, not to be precise.</li>
          <li><b>Headline gate.</b> A small language model (Claude Haiku 4.5) screens headlines and drops reports that are clearly out of scope. It is told that missing a relevant report costs more than passing an irrelevant one.</li>
          <li><b>Opening text.</b> Where a report arrives as a bare headline, the pipeline fetches the publisher's opening paragraphs if the publisher allows it. No paywall or login is bypassed; blocked reports are coded from the headline alone.</li>
          <li><b>Coding.</b> A larger model (Claude Sonnet 5.5) codes one report at a time against the full codebook. Its answer must fit a fixed schema, and it must quote the phrases that support the type and the date.</li>
          <li><b>Merging.</b> Reports of the same incident in a country are merged into one record. Records with an identical headline within three days are folded together.</li>
          <li><b>Checks and review.</b> Automatic checks flag suspect records. Analysts review records in a private console; a reviewed record is marked as such. Most records have not been reviewed.</li>
          <li><b>Publication.</b> The public layer is rebuilt nightly. It carries the record, its sources, its coding and its review state, and nothing from the private review notes.</li>
        </ol>
        <p><b>What is in scope.</b> ${esc(cb.unit.relevance)}</p>
        <p><b>Events and analysis.</b> ${esc(cb.unit.event)} ${esc(cb.unit.analysis)}</p>

        ${h('codebook')}
        <p>Codebook version ${esc(cb.version)} has ${cb.domains.reduce((a, d) => a + d.types.length, 0)} event types in ${cb.domains.length} domains. Coup follows the Colpus definition and purge follows the Military Purges in Dictatorships dataset. Each event is also coded for its role in democratic erosion with the DEED/ACE codebook (v7), using the 35 categories that concern the security sector.</p>
        <div class="tbl-scroll"><table class="tbl codebook">
          <thead><tr><th>Type</th><th>Definition</th><th>Subtypes</th></tr></thead>
          <tbody>${types}</tbody>
        </table></div>
        <p>Records coded before October 2026 used an earlier taxonomy of ${Object.keys(TYPE).length} families and a smaller model. They are marked "taxonomy v2 · legacy" on their record page. Every newer record also carries its legacy family, which is what the type filters and colours on this site use, so the two generations can be read together. They are not fully comparable: the older coding rated about four in ten events as high salience, against a target of 10–15% now.</p>

        ${h('fields')}
        <dl class="defs">
          <dt>Salience</dt><dd>${esc(field('salience'))}</dd>
          <dt>Coding confidence</dt><dd>${esc(field('certainty'))}</dd>
          <dt>Corroboration</dt><dd>Computed, never asked of the model. <i>Corroborated</i>: three or more sources, or two with at least one top-tier source. <i>One strong source</i>: two sources, or a single top-tier one. <i>Single source</i>: one report from a lower-tier source. Each source has a tier from 1 (most trusted) to 3.</dd>
          <dt>Date</dt><dd>The day the event happened when the report states it; otherwise the publication date, and the record says so.</dd>
          <dt>Location</dt><dd>A town or region when the report names one that the place list knows; otherwise the record sits at country level and is not drawn on maps. ${pct(placed)} of records have a place.</dd>
        </dl>
        <p>Before choosing the coding model, three models coded the same 300 reports. All three agreed on the event type for 64% of reports and on salience for 58%. These are agreement figures between models, not accuracy figures: the disagreements were not settled by a human, and a human-adjudicated test set is still to come.</p>

        ${h('labels')}
        <dl class="defs">
          <dt>Machine-coded · unreviewed</dt><dd>The record was coded by the model and no analyst has checked it.</dd>
          <dt>Analyst-reviewed</dt><dd>An analyst has checked the record and corrected it where needed.</dd>
          <dt>AI-assisted</dt><dd>Text written by a language model: some event interpretations, and country summaries that were researched with web search. Each such text carries this label and its date.</dd>
          <dt>Automated rule-based</dt><dd>Text assembled by fixed rules from the data, with no language model. The country "Assessment" paragraphs are of this kind.</dd>
          <dt>Under review</dt><dd>New reporting suggests a reference fact (an officeholder, an election date) has changed. The page keeps the last confirmed value until an analyst decides.</dd>
          <dt>Needs revision</dt><dd>A hand-written section predates a change of government.</dd>
        </dl>

        ${h('monitors')}
        <p><b>Civil–military status</b> is an analyst judgement in four classes. <i>Stable</i>: robust civilian control and no acute tension. <i>Strained</i>: friction within institutional bounds. <i>Crisis</i>: an active breach of civilian-control norms. <i>Authoritarian</i>: civil–military fusion, with the military a pillar of the regime.</p>
        <p><b>The 90-day outlook</b> comes from a risk model that combines structural indicators with recent coded events into three readings: regime vulnerability, militarization and security fragmentation. It is shown as a level from low to severe. The numeric scores are withheld because the model has not been validated against outcomes. Under each reading the page lists recent events that count toward it.</p>
        <p><b>Structural indicators</b> are taken from V-Dem (version 16), the World Bank's Worldwide Governance Indicators and World Development Indicators. The year is shown beside each value; some lag by two years or more. The regional median is the median of the ${model.countries.length} monitored countries.</p>
        <p><b>Officeholders and commanders</b> are researched with web search by a language model, with a source for each name. A proposed change is not shown until an analyst approves it.</p>
        <p><b>US assistance</b> is obligations by funding account from ForeignAssistance.gov, in constant dollars. SENTINEL groups the accounts itself: military (Foreign Military Financing, IMET, peacekeeping, excess defense articles, all Defense Department accounts), counternarcotics and law enforcement (State Department narcotics control and anti-terrorism funding), and everything else. This differs from the official Greenbook, which counts narcotics control as economic aid.</p>

        ${h('limits')}
        <ul>
          <li><b>Most records are unreviewed.</b> ${pct(model.events.length - reviewed)} of records are machine-coded only. Treat a single record as a lead to its sources, not as a finding.</li>
          <li><b>Coverage over time is uneven.</b> Collection started in March 2026 and was irregular until October 2026, when the nightly run became reliable. Earlier dates come from archive searches and hold fewer records, so a rising count in a chart is partly an artefact of collection.</li>
          <li><b>Coverage across countries is uneven.</b> Large countries with many outlets are better covered than small Caribbean and Central American ones.</li>
          <li><b>Many records rest on one report.</b> ${pct(single)} of records have a single source.</li>
          <li><b>Two coding generations.</b> ${pct(model.events.length - v3)} of records still carry the older coding. Salience is the field most affected.</li>
          <li><b>News is not the world.</b> The monitor sees what is reported. Quiet purges, unreported abuses and events in places without press freedom are under-counted.</li>
          <li><b>The outlook is not a forecast.</b> It is an unvalidated summary of pressure, shown as a label.</li>
        </ul>

        ${h('cite')}
        <p>Each record has a permanent page with a suggested citation. To cite the monitor as a whole: <span class="cite">SENTINEL: Civil–Military Monitor for Latin America and the Caribbean. ${esc(ctx.origin + ctx.url(''))}</span></p>
        <p>The public data files and the code are in the <a href="https://github.com/hjmoncrieff/sentinel">repository</a>, which is also the place to report an error: open an issue with the record number. See also the <a href="${ctx.legacy}privacy.html">privacy notice</a> and <a href="${ctx.legacy}terms.html">terms</a>.</p>
      </article>
    </div>
  </div>`;
  return layout(ctx, {title: 'About and methodology', description: 'How SENTINEL collects, codes, reviews and publishes security events, the full codebook, and the limits of the method.', nav: 'about', body});
}
