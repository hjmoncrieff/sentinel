// ── TAB SWITCHING ───────────────────────────────────────────
function activateTabUI(id){
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.toggle('active', b.dataset.tab===id));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('active', p.id===id));
}

function runTabSideEffects(id){
  if(id==='events') ensureEventMap();
  if(id==='overview') {
    if(!document.querySelector('.ov-fade.visible')) {
      const ovObs = new IntersectionObserver(entries => {
        entries.forEach(e => { if(e.isIntersecting){ e.target.classList.add('visible'); ovObs.unobserve(e.target); } });
      }, { threshold: 0.07 });
      document.querySelectorAll('.ov-fade').forEach(el => ovObs.observe(el));
    }
  }
  if(id==='explore')  { exInitDots(); exSetScene(exCurrentScene); }
  if(id==='transnational') { renderTsEvents(); initSecurityMap(); }
  if(id==='us') { renderUsEvents(); initUsCoopMap(); }
  if(id==='profiles') {
    loadIndicatorData();
    setTimeout(renderCpRegionalMap,80);
  }
}

function switchTab(id){
  if(id==='timeline'){
    activateTabUI('explore');
    exInitDots();
    exSetScene(1);
    return;
  }
  activateTabUI(id);
  runTabSideEffects(id);
}

function handleSubscribe(e){
  e.preventDefault();
  const email=document.getElementById('sub-email').value.trim();
  const msg=document.getElementById('sub-msg');
  if(!email) return false;
  msg.textContent='✓ Subscribed — you will receive the next Monday digest.';
  msg.style.display='block';
  document.getElementById('sub-email').value='';
  return false;
}

document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',()=>switchTab(btn.dataset.tab));
});

// ── EVENT DATA ──────────────────────────────────────────────
const TC = {
  coup:'var(--coup)', purge:'var(--purge)', coup_proofing:'var(--coup-proofing)',
  conflict:'var(--conflict)', reform:'var(--reform)',
  aid:'var(--aid)', coop:'var(--coop)', exercise:'var(--exercise)',
  oc:'var(--oc)', protest:'var(--protest)', peace:'var(--peace)', other:'var(--other)'
};
const TC_HEX = {
  coup:'#a3372f', purge:'#bb6d2f', coup_proofing:'#6b4d7a',
  conflict:'#8c4630', reform:'#456d59',
  aid:'#235a8b', coop:'#326f7d', exercise:'#4a718f',
  oc:'#73514b', protest:'#7b5b3f', peace:'#4d7661', other:'#5f645c'
};
const TYPE_LABEL = {
  coup:'Coup', purge:'Purge', coup_proofing:'Coup-Proofing',
  conflict:'Conflict', reform:'Reform', oc:'Org. Crime',
  aid:'Mil. Aid', coop:'US Coop', exercise:'Exercise',
  protest:'Protest', peace:'Peace', other:'Other'
};
const EVENT_CATEGORY_LABEL = {
  political:'Political',
  military:'Military',
  security:'Security',
  international:'International',
  economic:'Economic'
};
const ANALYST_LENS_META = {
  military:{ label:'Military', className:'military' },
  political:{ label:'Political', className:'political' },
  security:{ label:'Security', className:'security' },
  international:{ label:'International', className:'international' },
  economist:{ label:'Economist', className:'economist' },
  cmr:{ label:'Military', className:'military' },
  political_risk:{ label:'Political', className:'political' },
  regional_security:{ label:'Security', className:'security' }
};
const PROVENANCE_STAGE_ORDER = {
  ingestion:10,
  normalization:20,
  classification:30,
  canonicalization:40,
  actor_coding:50,
  qa:60,
  duplicate_review:70,
  human_review:80,
  council_analysis:90,
  publication_decision:100,
  publication:110
};
let allEvents=[], filtered=[], selected=null;
let filters={type:'all',category:'all',signal:'all',subregion:'all',country:'all',conf:'all',salience:'all',range:'all',search:''};
let eventFilterPanelOpen=false;
let eventNavigatorMode='filters';
let councilById=new Map();
let eventTypeMeta=new Map();
let eventTypeOrder=[];
let publicCategoryMeta=new Map();
let eventSignalMeta=new Map();
let eventMapRendererMode='pressure';
let eventCountryOverlayOpen = false;
let ovSignalLayer = null;
let ovLabelLayer = null;
let ovCountryPathLayer = null;

const SR_MAP_VIEW={
  'all':         {center:[-10,-66],zoom:3},
  'brazil':      {center:[-14,-51],zoom:4},
  'south-andean':{center:[-5,-72], zoom:4},
  'south-cone':  {center:[-35,-62],zoom:4},
  'central':     {center:[14,-87], zoom:6},
  'caribbean':   {center:[17,-68], zoom:5},
  'mexico':      {center:[24,-102],zoom:5}
};
let tlFilter='all', tlCountry='all', tlSalience='all', tlYear='all', tlMonth='all', tlConf='all';
let map = null;
let eventsMapSvg = null;
let eventsMapWrap = null;
let eventsMapTooltip = null;
let eventsMapProjection = null;
let eventsMapPath = null;
let eventsMapResizeBound = false;
let countryMonitorsByCountry = new Map();
let countryDossiersByCountry = new Map();
let regionalMixChart = null;
let regionalLeadersChart = null;
let lastIngestionTimestamp = null;

const EVENT_SIGNAL_ORDER = {
  coup_and_command_break: 10,
  security_sector_reform_and_oversight: 20,
  state_repression_and_exceptional_rule: 30,
  armed_conflict_and_territorial_control: 40,
  organized_crime_and_transnational_security: 50,
  criminal_violence_and_illicit_economies: 60,
  external_security_support_and_alignment: 70,
  military_exercises_and_force_posture: 80,
  procurement_and_arms: 90,
  peace_process_and_ddr: 100,
  corruption_capture_and_judicial_pressure: 110,
  border_tension_and_sovereignty: 120
};

function openMobileNav(){
  document.getElementById('mobile-nav-overlay')?.classList.add('open');
}

function closeMobileNav(){
  document.getElementById('mobile-nav-overlay')?.classList.remove('open');
}

function updatePipelineAge(){
  const ageEl = document.getElementById('live-ingestion-age');
  if(!ageEl || !lastIngestionTimestamp) return;
  const diff = Math.max(0, Math.floor((Date.now() - lastIngestionTimestamp) / 1000));
  ageEl.textContent = diff < 60 ? `${diff}s ago` : `${Math.floor(diff / 60)}m ago`;
}

function getEventDateISO(ev){
  return String(ev?.date || ev?.event_date || '').trim();
}

function getAdaptiveEventRange(events){
  const dateValues = (events || []).map(ev => parseEventDateValue(getEventDateISO(ev))).filter(value => value != null);
  if(!dateValues.length) return 'all';
  const newest = Math.max(...dateValues);
  const ageDays = Math.floor((Date.now() - newest) / 86400000);
  if(ageDays <= 30) return '30d';
  if(ageDays <= 90) return '90d';
  return 'all';
}

// ── DATA LOADING ─────────────────────────────────────────────
function buildPublishedEventCouncil(pub){
  const classification = pub?.public_classification && typeof pub.public_classification === 'object'
    ? pub.public_classification
    : {};
  const takeaways = pub?.public_takeaways && typeof pub.public_takeaways === 'object'
    ? pub.public_takeaways
    : {};
  const hasCouncilData = !!(
    Object.keys(classification).length ||
    Object.keys(takeaways).length ||
    pub?.public_analysis ||
    pub?.public_risk_level ||
    pub?.public_ai_generated
  );
  if(!hasCouncilData) return null;
  return {
    analyses: {
      synthesis: {
        classification,
        public_takeaways: takeaways,
        assessment: pub.public_analysis || '',
        public_analysis: pub.public_analysis || '',
        risk_level: pub.public_risk_level || '',
        ai_generated: !!pub.public_ai_generated
      }
    }
  };
}

function normalizePublishedEvent(pub){
  const latitude = Number(pub?.latitude);
  const longitude = Number(pub?.longitude);
  const sourceList = Array.isArray(pub?.source_all)
    ? pub.source_all.filter(Boolean)
    : (pub?.source_primary ? [pub.source_primary] : []);
  const urlList = Array.isArray(pub?.url_all)
    ? pub.url_all.filter(Boolean)
    : (pub?.url_primary ? [pub.url_primary] : []);
  const linkedReports = Array.isArray(pub?.linked_reports) ? pub.linked_reports : [];
  const publicClassification = pub?.public_classification && typeof pub.public_classification === 'object'
    ? pub.public_classification
    : {};
  const confidence = String(pub?.confidence || '').trim().toLowerCase();
  const event = {
    id: String(pub?.event_id || ''),
    sentinel_id: String(pub?.event_id || ''),
    date: pub?.event_date || '',
    country: pub?.country || '',
    type: pub?.legacy_event_family || pub?.event_category_family || pub?.event_type || 'other',
    title: pub?.headline || 'Untitled',
    headline: pub?.headline || 'Untitled',
    summary: pub?.summary || '',
    source: pub?.source_primary || sourceList[0] || '',
    sources: sourceList,
    url: pub?.url_primary || urlList[0] || '',
    links: urlList,
    location: pub?.subnational_location || pub?.country || '',
    subnational_location: pub?.subnational_location || '',
    coords: Number.isFinite(latitude) && Number.isFinite(longitude) ? [latitude, longitude] : null,
    latitude: Number.isFinite(latitude) ? latitude : null,
    longitude: Number.isFinite(longitude) ? longitude : null,
    salience: pub?.salience || '',
    conf: confidence === 'high' ? 'green' : confidence === 'medium' ? 'yellow' : confidence === 'low' ? 'red' : '',
    confidence,
    review_status: pub?.review_status || null,
    review_priority: pub?.review_priority || null,
    human_validated: !!pub?.human_validated,
    event_type_domain: pub?.event_type_domain || pub?.event_category || null,
    event_category_family: pub?.event_category_family || pub?.event_type || null,
    event_category_label: pub?.event_category_label || null,
    event_category: pub?.event_category || null,
    event_subcategory: pub?.event_subcategory || null,
    event_construct_destinations: Array.isArray(pub?.event_construct_destinations) ? pub.event_construct_destinations : [],
    event_analyst_lenses: Array.isArray(pub?.event_analyst_lenses) ? pub.event_analyst_lenses : [],
    event_signal_families: Array.isArray(pub?.event_signal_families) ? pub.event_signal_families : [],
    event_signal_labels: Array.isArray(pub?.event_signal_labels) ? pub.event_signal_labels : [],
    public_category_key: pub?.public_category_key || null,
    public_category_label: pub?.public_category_label || null,
    public_category_rank: Number(pub?.public_category_rank) || 999,
    actors: Array.isArray(pub?.actors) ? pub.actors : [],
    deed_type: publicClassification.deed_type || pub?.deed_type || null,
    subtype: pub?.event_subtype || null,
    public_analysis: pub?.public_analysis || null,
    public_review: {
      review_status: pub?.review_status || pub?.provenance_summary?.review_status || null,
      review_priority: pub?.review_priority || null,
      human_validated: !!(pub?.human_validated || pub?.provenance_summary?.human_validated),
      reviewed_by_human: !!pub?.provenance_summary?.reviewed_by_human,
      provenance_summary: pub?.provenance_summary || {},
      provenance_timeline: Array.isArray(pub?.provenance_timeline) ? pub.provenance_timeline : [],
      linked_reports: linkedReports,
      headline: pub?.headline || 'Untitled',
      event_subtype: pub?.event_subtype || null,
      deed_type: publicClassification.deed_type || pub?.deed_type || null,
      actors: Array.isArray(pub?.actors) ? pub.actors : [],
      source_all: sourceList,
      url_all: urlList,
      ai_generated: !!pub?.public_ai_generated
    },
    council: buildPublishedEventCouncil(pub)
  };
  event.standard_title = getStandardizedEventTitle(event);
  event.display_country = getEventCountryLabel(event);
  return event;
}

async function loadEvents(){
  try {
    const [publishedRes, taxonomyRes, monitorsRes, dossiersRes] = await Promise.all([
      fetch('data/published/events_public.json?t='+Date.now()),
      fetch('config/taxonomy/event_types.json?t='+Date.now()).catch(()=>null),
      fetch('data/published/country_monitors.json?t='+Date.now()).catch(()=>null),
      fetch('data/published/country_dossiers.json?t='+Date.now()).catch(()=>null)
    ]);
    if(!publishedRes.ok) throw new Error('HTTP '+publishedRes.status);
    const published = await publishedRes.json();
    let taxonomy = null;
    let monitors = null;
    let dossiers = null;
    if(taxonomyRes && taxonomyRes.ok){
      taxonomy = await taxonomyRes.json();
    }
    if(monitorsRes && monitorsRes.ok){
      monitors = await monitorsRes.json();
    }
    if(dossiersRes && dossiersRes.ok){
      dossiers = await dossiersRes.json();
    }
    councilById = new Map();
    eventTypeMeta = new Map(((taxonomy?.event_types)||[]).map(item=>[String(item.code), item]));
    eventTypeOrder = ((taxonomy?.event_types)||[]).slice().sort((a,b)=>(b.precedence_rank||0)-(a.precedence_rank||0)).map(item=>item.code);
    countryMonitorsByCountry = new Map(((monitors?.countries)||[]).map(item=>[String(item.country), item]));
    countryDossiersByCountry = new Map(((dossiers?.countries)||[]).map(item=>[String(item.country), item]));
    publicCategoryMeta = new Map();
    eventSignalMeta = new Map();
    const publishedEvents = published?.events || [];
    let events = publishedEvents.map(normalizePublishedEvent);
    publishedEvents.forEach(pub => {
      if(pub.public_category_key){
        publicCategoryMeta.set(String(pub.public_category_key), {
          label: pub.public_category_label || String(pub.public_category_key),
          rank: Number(pub.public_category_rank) || 999
        });
      }
      const ids = Array.isArray(pub.event_signal_families) ? pub.event_signal_families : [];
      const labels = Array.isArray(pub.event_signal_labels) ? pub.event_signal_labels : [];
      ids.forEach((id, index)=>{
        if(!id) return;
        eventSignalMeta.set(String(id), labels[index] || normalizeKnowledgeLabel(id));
      });
    });
    const updatedStr = published?.generated_at || events[0]?.date || null;
    allEvents = events;
    filtered = events;
    filters.range = 'all';
    buildCountries();
    renderTypeFilterOptions();
    renderCategoryFilterOptions();
    renderSignalFilterOptions();
    document.getElementById('type-filter-select') && (document.getElementById('type-filter-select').value = filters.type);
    document.getElementById('category-filter-select') && (document.getElementById('category-filter-select').value = filters.category);
    document.getElementById('signal-filter-select') && (document.getElementById('signal-filter-select').value = filters.signal);
    document.getElementById('country-filter-select') && (document.getElementById('country-filter-select').value = filters.country);
    syncEventFilterPicker('type');
    syncEventFilterPicker('category');
    syncEventFilterPicker('signal');
    syncEventFilterPicker('country');
    document.getElementById('event-search-input') && (document.getElementById('event-search-input').value = filters.search);
    setActiveEventChips('event-range-chips','range',filters.range);
    setActiveEventChips('event-salience-chips','salience',filters.salience);
    setActiveEventChips('event-confidence-chips','conf',filters.conf);
    updateEventFilterSummary();
    applyFilters();
    computeCmrScores();
    renderRegionalMonitorSummary();
    ovRefreshMarkers();
    if(updatedStr){
      lastIngestionTimestamp = new Date(updatedStr).getTime();
      updatePipelineAge();
      const ago = Math.round((Date.now()-new Date(updatedStr))/60000);
      const agoStr = ago<60 ? ago+'m ago' : Math.round(ago/60)+'h ago';
      const policyBits = [];
      if((published?.withheld_count || 0) > 0){
        policyBits.push(`${published.withheld_count} withheld by publication policy`);
      }
      const pipelineText = document.getElementById('pipeline-status-text');
      if(pipelineText){
        pipelineText.innerHTML = `Pipeline running — ${events.length} public events loaded${policyBits.length ? ' · ' + policyBits.join(' · ') : ''} · last ingestion <span id="live-ingestion-age">${agoStr}</span>`;
      }
      document.querySelector('.log-txt')?.classList.add('ok');
    } else {
      const pipelineText = document.getElementById('pipeline-status-text');
      if(pipelineText) pipelineText.textContent = `Pipeline running — ${events.length} public events loaded`;
      document.querySelector('.log-txt')?.classList.add('ok');
    }
  } catch(e) {
    const pipelineText = document.getElementById('pipeline-status-text');
    if(pipelineText) pipelineText.textContent = 'Failed to load public dashboard artifacts — '+e.message+' · Rebuild data/published and serve via http-server';
    document.querySelector('.log-txt')?.classList.remove('ok');
  }
}

function getCountryMonitorEntry(country){
  return countryMonitorsByCountry.get(String(country)) || null;
}

function getCountryDossier(country){
  return countryDossiersByCountry.get(String(country)) || null;
}

function getCountryPublicContext(country){
  return getCountryDossier(country)?.public_context || null;
}

function getCountryMonitor(country, code){
  const entry = getCountryMonitorEntry(country);
  if(!entry) return null;
  return (entry.monitors || []).find(item => String(item.code) === String(code)) || null;
}

function getCountryRiskConstruct(country, code){
  const entry = getCountryMonitorEntry(country);
  if(!entry) return null;
  return (entry.risk_constructs || []).find(item => String(item.code) === String(code)) || null;
}

function getCountryPredictiveSummary(country){
  const monitorSummary = getCountryMonitorEntry(country)?.predictive_summary || null;
  const dossierSummary = getCountryDossier(country)?.public_summary || null;
  if(monitorSummary && dossierSummary){
    return {
      ...monitorSummary,
      ...dossierSummary,
      leading_construct_label: dossierSummary.leading_label || monitorSummary.leading_construct_label || monitorSummary.leading_label || '',
    };
  }
  if(dossierSummary){
    return {
      ...dossierSummary,
      leading_construct_label: dossierSummary.leading_label || '',
    };
  }
  return monitorSummary;
}

// ── CP v2 DATA HELPERS ─────────────────────────────────────────

function cpGetVdem(name) {
  if (!_vdemData) return null;
  return _vdemData.countries.find(c => c.country === name) || null;
}

function cpGetWb(name) {
  if (!_wbData) return null;
  return _wbData.countries.find(c => c.country === name) || null;
}

// Returns { regimeVuln, militarization, secFrag, democDeficit, physVuln, stateFrag }
// All 0-100, higher = more risk
function cpRadarScores(name) {
  const rv  = getCountryRiskConstruct(name, 'regime_vulnerability')?.score ?? 0;
  const mil = getCountryRiskConstruct(name, 'militarization')?.score ?? 0;
  const sf  = getCountryRiskConstruct(name, 'security_fragmentation')?.score ?? 0;

  const vd = cpGetVdem(name);
  const dem = vd ? Math.round((1 - (vd.polyarchy ?? 0.5)) * 100) : 0;
  const phys = vd ? Math.round((1 - (vd.physinteg ?? 0.5)) * 100) : 0;

  const wb = cpGetWb(name);
  const wgi = wb?.wgi_govt_effectiveness ?? 0;
  const frag = Math.min(100, Math.max(0, Math.round((1 - (wgi + 2) / 4) * 100)));

  return { regimeVuln: rv, militarization: mil, secFrag: sf, democDeficit: dem, physVuln: phys, stateFrag: frag };
}

// Returns rank (1 = highest risk) for each of the 6 axes across all 25 monitored countries
// Result shape: { regimeVuln: { [name]: rank }, militarization: {...}, ... }
function cpComputeRanks() {
  const COUNTRIES = Object.keys(COUNTRY_PROFILES);
  const axes = ['regimeVuln', 'militarization', 'secFrag', 'democDeficit', 'physVuln', 'stateFrag'];
  const allScores = {};
  COUNTRIES.forEach(c => { allScores[c] = cpRadarScores(c); });

  const ranks = {};
  axes.forEach(axis => {
    const sorted = [...COUNTRIES].sort((a, b) => (allScores[b][axis] ?? 0) - (allScores[a][axis] ?? 0));
    ranks[axis] = {};
    sorted.forEach((c, i) => { ranks[axis][c] = i + 1; });
  });
  return ranks;
}

function cpRankClass(rank) {
  if (rank <= 6)  return 'r-hi';
  if (rank <= 18) return 'r-md';
  return 'r-lo';
}

// Returns { score, delta, priorYear } for a V-Dem indicator (polyarchy or physinteg)
// delta is in risk-oriented direction: positive = more risk
function cpVdemDelta(name, field) {
  const vd = cpGetVdem(name);
  if (!vd) return { current: 0, delta: null, priorYear: null };
  const series = vd.series?.[field];
  if (!series?.length) return { current: Math.round((1 - (vd[field] ?? 0.5)) * 100), delta: null, priorYear: null };
  const sorted = [...series].sort((a, b) => b.year - a.year);
  const cur = sorted[0]; const prev = sorted[1];
  const curScore  = Math.round((1 - (cur.value  ?? 0.5)) * 100);
  const prevScore = prev ? Math.round((1 - (prev.value ?? 0.5)) * 100) : null;
  const delta = prevScore !== null ? +(curScore - prevScore).toFixed(1) : null;
  return { current: curScore, delta, priorYear: prev?.year ?? null };
}

// Returns { score, delta, priorYear } for WGI state fragility
function cpWgiDelta(name) {
  const wb = cpGetWb(name);
  if (!wb) return { current: 0, delta: null, priorYear: null };
  const series = wb.wgi_govt_effectiveness_series;
  if (!series?.length) {
    const wgi = wb.wgi_govt_effectiveness ?? 0;
    return { current: Math.min(100, Math.max(0, Math.round((1 - (wgi + 2) / 4) * 100))), delta: null, priorYear: null };
  }
  const sorted = [...series].filter(d => d.value != null).sort((a, b) => b.year - a.year);
  const cur = sorted[0]; const prev = sorted[1];
  const toFrag = v => Math.min(100, Math.max(0, Math.round((1 - (v + 2) / 4) * 100)));
  const curScore = toFrag(cur.value);
  const prevScore = prev ? toFrag(prev.value) : null;
  const delta = prevScore !== null ? +(curScore - prevScore).toFixed(1) : null;
  return { current: curScore, delta, priorYear: prev?.year ?? null };
}

// Returns { value, delta, priorYear } for GDP per capita (constant 2015 USD)
function cpGdpDelta(name) {
  const wb = cpGetWb(name);
  if (!wb) return { value: null, pct: null, priorYear: null };
  const series = (wb.gdp_per_capita_constant_2015_usd_series || []).filter(d => d.value != null);
  if (!series.length) return { value: null, pct: null, priorYear: null };
  const sorted = [...series].sort((a, b) => b.year - a.year);
  const cur = sorted[0]; const prev = sorted[1];
  const pct = prev ? +((cur.value - prev.value) / prev.value * 100).toFixed(1) : null;
  return { value: Math.round(cur.value), pct, priorYear: prev?.year ?? null };
}

function cpBuildRadarSection(name, safeId) {
  const scores = cpRadarScores(name);
  const ranks  = cpComputeRanks();
  const rv  = getCountryRiskConstruct(name, 'regime_vulnerability');
  const mil = getCountryRiskConstruct(name, 'militarization');
  const sf  = getCountryRiskConstruct(name, 'security_fragmentation');

  function rankBadge(axis, country) {
    const r = ranks[axis]?.[country] ?? 25;
    return `<span class="cp2-rank-badge ${cpRankClass(r)}">#${r} of 25</span>`;
  }
  function trendSpan(label) {
    const color = label === 'rising' ? 'var(--purge)' : label === 'easing' ? 'var(--reform)' : 'var(--text-muted)';
    return label ? `<span class="cp2-score-trend" style="color:${color};">${label}</span>` : '';
  }

  const constructRows = [
    { label: 'Regime Vulnerability', axis: 'regimeVuln', score: scores.regimeVuln, trend: rv?.trend_label },
    { label: 'Militarization',       axis: 'militarization', score: scores.militarization, trend: mil?.trend_label },
    { label: 'Security Fragmentation', axis: 'secFrag', score: scores.secFrag, trend: sf?.trend_label },
  ].map(r => `
    <div class="cp2-score-row">
      <span class="cp2-score-name">${r.label}</span>
      <span class="cp2-score-val">${Math.round(r.score)}/100</span>
      ${trendSpan(r.trend)}
      ${rankBadge(r.axis, name)}
    </div>`).join('');

  const indicatorRows = [
    { label: 'Democracy Deficit',     axis: 'democDeficit', score: scores.democDeficit },
    { label: 'Physical Vulnerability', axis: 'physVuln',    score: scores.physVuln },
    { label: 'State Fragility',        axis: 'stateFrag',   score: scores.stateFrag },
  ].map(r => `
    <div class="cp2-score-row">
      <span class="cp2-score-name">${r.label}</span>
      <span class="cp2-score-val">${Math.round(r.score)}/100</span>
      ${rankBadge(r.axis, name)}
    </div>`).join('');

  return `
    <div class="cp2-radar-section">
      <div class="cp2-radar-canvas-wrap">
        <canvas id="cp-radar-${safeId}" width="258" height="258"></canvas>
      </div>
      <div class="cp2-score-table">
        <div class="cp2-grp-lbl">Risk Constructs</div>
        ${constructRows}
        <div class="cp2-grp-lbl">Structural Indicators</div>
        ${indicatorRows}
      </div>
    </div>
    <div class="cp2-sources-band">
      <span class="cp2-sources-label">Sources</span>
      <span class="cp2-sources-sep">·</span>
      <span class="cp2-sources-item">Risk constructs — SENTINEL Monitor</span>
      <span class="cp2-sources-sep">·</span>
      <span class="cp2-sources-item">Democracy · Physical Integrity — V-Dem 2024</span>
      <span class="cp2-sources-sep">·</span>
      <span class="cp2-sources-item">State Fragility — WGI 2023</span>
    </div>`;
}

function cpInitRadar(name, safeId) {
  if (_cpRadarChart) { try { _cpRadarChart.destroy(); } catch(e){} _cpRadarChart = null; }
  const canvas = document.getElementById(`cp-radar-${safeId}`);
  if (!canvas) return;
  const scores = cpRadarScores(name);
  const data = [
    scores.regimeVuln,
    scores.militarization,
    scores.secFrag,
    scores.democDeficit,
    scores.physVuln,
    scores.stateFrag,
  ];
  _cpRadarChart = new Chart(canvas, {
    type: 'radar',
    data: {
      labels: [
        ['Regime', 'Vulnerability'],
        ['Militarization'],
        ['Security', 'Fragmentation'],
        ['Democracy', 'Deficit'],
        ['Physical', 'Vulnerability'],
        ['State', 'Fragility'],
      ],
      datasets: [{
        data,
        borderColor: 'rgba(184,50,50,0.7)',
        backgroundColor: 'rgba(180,50,50,0.10)',
        borderWidth: 1.5,
        pointRadius: 3,
        pointBackgroundColor: 'rgba(184,50,50,0.7)',
      }],
    },
    options: {
      responsive: false,
      maintainAspectRatio: false,
      layout: { padding: 10 },
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { display: false, stepSize: 25 },
          grid: { color: '#1e2230' },
          angleLines: { color: '#1e2230' },
          pointLabels: {
            color: '#6a6560',
            font: { size: 9, family: "'DM Mono', monospace" },
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => {
              const lbl = items[0].label;
              return Array.isArray(lbl) ? lbl.join(' ') : lbl;
            },
            label: item => `${item.raw.toFixed(1)} / 100`,
          },
        },
      },
    },
  });
}

function cpBuildPulseSection(name, safeId) {
  const now = new Date();
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push({ year: d.getFullYear(), month: d.getMonth(), label: d.toLocaleString('en', { month: 'short' }) });
  }
  const rangeLabel = `${months[0].label} ${months[0].year} – ${months[11].label} ${months[11].year}`;
  return `
    <div class="cp2-pulse-section">
      <div class="cp2-pulse-hdr">
        <span class="cp2-pulse-label">Event Pulse — ${rangeLabel}</span>
        <div class="cp2-pulse-legend">
          <div class="cp2-pulse-legend-item"><div class="cp2-pulse-swatch" style="background:rgba(168,64,0,0.5)"></div>Conflict / OC</div>
          <div class="cp2-pulse-legend-item"><div class="cp2-pulse-swatch" style="background:#2a2e3c"></div>Other</div>
        </div>
      </div>
      <div class="cp2-pulse-canvas-wrap">
        <canvas id="cp-pulse-${safeId}" style="width:100%;height:52px;"></canvas>
      </div>
    </div>`;
}

function cpInitPulse(name, safeId) {
  if (_cpPulseChart) { try { _cpPulseChart.destroy(); } catch(e){} _cpPulseChart = null; }
  const canvas = document.getElementById(`cp-pulse-${safeId}`);
  if (!canvas) return;

  const now = new Date();
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push({ year: d.getFullYear(), month: d.getMonth(), label: d.toLocaleString('en', { month: 'short' }) });
  }

  const hot   = months.map(() => 0);
  const other = months.map(() => 0);

  (allEvents || []).filter(e => matchesProfileCountryEvent(e, name)).forEach(ev => {
    const d = new Date(ev.date);
    const idx = months.findIndex(m => m.year === d.getFullYear() && m.month === d.getMonth());
    if (idx === -1) return;
    if (ev.type === 'conflict' || ev.type === 'oc') hot[idx]++;
    else other[idx]++;
  });

  const labels = months.map(m => m.label);
  _cpPulseChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Conflict/OC', data: hot,   backgroundColor: 'rgba(168,64,0,0.5)', stack: 's' },
        { label: 'Other',       data: other, backgroundColor: '#2a2e3c',             stack: 's' },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 8, family: "'DM Mono', monospace" }, color: '#b5ab9d' } },
        y: { stacked: true, display: false },
      },
    },
  });
}

const DOSSIER_STRUCTURAL_CARD_META = {
  polyarchy: { label: 'Electoral Democracy', color: '#1460b0' },
  mil_constrain: { label: 'Military Constraints', color: '#7a2e6e' },
  mil_exec: { label: 'Executive Entanglement', color: '#9b3f2a' },
  wgi_rule_of_law: { label: 'Rule of Law', color: '#157550' },
  mil_exp_pct_gdp: { label: 'Military Spending / GDP', color: '#c86010' },
  inflation_consumer_prices_pct: { label: 'Inflation', color: '#b83232' },
};

function cpBuildLegacyStructuralTrends(name) {
  const dem  = cpVdemDelta(name, 'polyarchy');
  const phys = cpVdemDelta(name, 'physinteg');
  const frag = cpWgiDelta(name);
  const gdp  = cpGdpDelta(name);

  function deltaSpan(delta, priorYear) {
    if (delta === null) return `<div class="cp2-trend-delta neutral">— no prior data</div>`;
    const cls = delta > 0 ? 'up' : delta === 0 ? 'neutral' : 'down';
    const sign = delta > 0 ? '+' : '';
    return `<div class="cp2-trend-delta ${cls}">${sign}${delta} vs ${priorYear}</div>`;
  }

  const demDelta  = deltaSpan(dem.delta,  dem.priorYear);
  const physDelta = deltaSpan(phys.delta, phys.priorYear);
  const fragDelta = deltaSpan(frag.delta, frag.priorYear);

  let gdpVal = '—', gdpDeltaHtml = `<div class="cp2-trend-delta neutral">—</div>`;
  if (gdp.value !== null) {
    gdpVal = '$' + gdp.value.toLocaleString();
    if (gdp.pct !== null) {
      const sign = gdp.pct > 0 ? '+' : '';
      const cls = gdp.pct > 0 ? 'down' : gdp.pct < 0 ? 'up' : 'neutral';
      gdpDeltaHtml = `<div class="cp2-trend-delta ${cls}">${sign}${gdp.pct}% vs ${gdp.priorYear}</div>`;
    }
  }

  return `
    <div class="cp2-trends-strip">
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">Democracy Deficit</div>
        <div class="cp2-trend-value">${dem.current}/100</div>
        ${demDelta}
      </div>
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">Physical Vulnerability</div>
        <div class="cp2-trend-value">${phys.current}/100</div>
        ${physDelta}
      </div>
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">State Fragility</div>
        <div class="cp2-trend-value">${frag.current}/100</div>
        ${fragDelta}
      </div>
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">GDP per Capita</div>
        <div class="cp2-trend-value">${gdpVal}</div>
        ${gdpDeltaHtml}
      </div>
    </div>`;
}

function cpBuildStructuralPoints(card) {
  const series = Array.isArray(card?.trend_series) ? card.trend_series : [];
  const endYear = Number(card?.as_of_year);
  if (!series.length || !Number.isFinite(endYear)) return [];
  const startYear = endYear - series.length + 1;
  return series
    .map((value, index) => ({ year: startYear + index, value: Number(value) }))
    .filter(point => Number.isFinite(point.year) && Number.isFinite(point.value));
}

function cpRenderDossierSparkline(points, color) {
  if (!Array.isArray(points) || points.length < 2) return '';
  return `<div class="cp2-trend-spark">${makeSvgSparkline(points, color, 132, 32)}</div>`;
}

function cpRenderSeriesRange(points, fallbackYear) {
  if (!Array.isArray(points) || !points.length) return fallbackYear ? `As of ${fallbackYear}` : 'No year range';
  const start = points[0]?.year;
  const end = points[points.length - 1]?.year;
  if (!Number.isFinite(start) || !Number.isFinite(end)) return fallbackYear ? `As of ${fallbackYear}` : 'No year range';
  if (start === end) return `As of ${end}`;
  return `${start}–${end}`;
}

function cpRenderDossierTrendDelta(points, fallbackYear) {
  if (!Array.isArray(points) || points.length < 2) {
    return `<div class="cp2-trend-delta neutral">${escapeHtml(cpRenderSeriesRange(points, fallbackYear))}</div>`;
  }
  const delta = points[points.length - 1].value - points[0].value;
  if (Math.abs(delta) < 0.001) {
    return `<div class="cp2-trend-delta neutral">Stable across ${escapeHtml(cpRenderSeriesRange(points, fallbackYear))}</div>`;
  }
  const cls = delta > 0 ? 'up' : 'down';
  const sign = delta > 0 ? '+' : '';
  return `<div class="cp2-trend-delta ${cls}">${sign}${delta.toFixed(2)} across ${escapeHtml(cpRenderSeriesRange(points, fallbackYear))}</div>`;
}

function cpTrendHoverLabel(text) {
  return `<div class="cp2-trend-hover-label">${escapeHtml(String(text || 'Hover for series'))}</div>`;
}

function cpTrendToggleButton(label) {
  const safeLabel = escapeHtml(String(label || 'View trend'));
  return `<button class="cp2-trend-toggle" type="button" aria-expanded="false" onclick="cpToggleTrendCard(this)">${safeLabel}</button>`;
}

function cpToggleTrendCard(button){
  const card = button?.closest?.('.cp2-trend-cell-hoverable');
  if(!card) return;
  const next = !card.classList.contains('is-open');
  card.classList.toggle('is-open', next);
  button.setAttribute('aria-expanded', next ? 'true' : 'false');
}

function cpBuildPredictiveTrendSeries(name) {
  const dossier = getCountryDossier(name);
  const seriesRows = Array.isArray(dossier?.public_predictive_series) ? dossier.public_predictive_series : [];
  if (!seriesRows.length) return '';
  const cardHtml = seriesRows.map(item => {
    const points = Array.isArray(item.trend_series)
      ? item.trend_series
          .map(point => ({
            year: Number(point?.year),
            value: Number(point?.score),
          }))
          .filter(point => Number.isFinite(point.year) && Number.isFinite(point.value))
      : [];
    const color = getConstructAccent(item.code);
    const delta = points.length >= 2 ? points[points.length - 1].value - points[0].value : 0;
    const deltaClass = delta > 0.2 ? 'up' : delta < -0.2 ? 'down' : 'neutral';
    const deltaPrefix = delta > 0.2 ? '+' : '';
    const deltaText = points.length >= 2
      ? `${deltaPrefix}${delta.toFixed(1)} across annualized series`
      : `Current trajectory ${String(item.trend_label || 'stable')}`;
    return `<div class="cp2-trend-cell cp2-trend-cell-hoverable" data-construct-code="${escapeHtml(String(item.code || ''))}">
      <div class="cp2-trend-kicker">${escapeHtml(String(item.label || getConstructLabel(item.code)))}</div>
      <div class="cp2-trend-value">${escapeHtml(String(item.display_score || 'n/a'))}</div>
      ${cpTrendHoverLabel(`Hover to inspect ${cpRenderSeriesRange(points, item.as_of_year)}`)}
      ${cpTrendToggleButton('View trend')}
      <div class="cp2-trend-hover-panel">
        <div class="cp2-trend-hover-range">${escapeHtml(cpRenderSeriesRange(points, item.as_of_year))}</div>
        <div class="cp2-trend-spark">${points.length >= 2 ? makeSvgSparkline(points, color, 132, 32) : ''}</div>
        <div class="cp2-trend-delta ${deltaClass}">${escapeHtml(deltaText)}</div>
      </div>
    </div>`;
  }).join('');
  return `
    <div class="cp2-trends-shell cp2-trends-shell-predictive">
      <div class="cp2-trends-header">
        <span class="cp2-col-kicker">Predictive Pressure Trajectories</span>
        <span class="cp2-trends-freshness">Annualized construct history</span>
      </div>
      <div class="cp2-trends-strip cp2-trends-strip-dossier">${cardHtml}</div>
    </div>`;
}

function cpBuildStructuralTrends(name) {
  const dossier = getCountryDossier(name);
  const cards = Array.isArray(dossier?.public_structural_cards) ? dossier.public_structural_cards : [];
  if (!cards.length) return cpBuildLegacyStructuralTrends(name);

  const freshnessYear = dossier?.public_freshness?.structural_as_of_year || '';
  const cardHtml = cards.map(card => {
    const meta = DOSSIER_STRUCTURAL_CARD_META[card.code] || {};
    const label = meta.label || card.label || card.code || 'Indicator';
    const color = meta.color || '#6a6560';
    const value = card.display_value || 'n/a';
    const points = cpBuildStructuralPoints(card);
    return `<div class="cp2-trend-cell cp2-trend-cell-hoverable" data-card-code="${escapeHtml(String(card.code || ''))}">
      <div class="cp2-trend-kicker">${escapeHtml(String(label))}</div>
      <div class="cp2-trend-value">${escapeHtml(String(value))}</div>
      ${cpTrendHoverLabel(`Hover for ${cpRenderSeriesRange(points, card.as_of_year)}`)}
      ${cpTrendToggleButton('View trend')}
      <div class="cp2-trend-hover-panel">
        <div class="cp2-trend-hover-range">${escapeHtml(cpRenderSeriesRange(points, card.as_of_year))}</div>
        ${cpRenderDossierSparkline(points, color)}
        ${cpRenderDossierTrendDelta(points, card.as_of_year)}
      </div>
    </div>`;
  }).join('');

  return `
    <div class="cp2-trends-shell">
      <div class="cp2-trends-header">
        <span class="cp2-col-kicker">Structural Context</span>
        <span class="cp2-trends-freshness">${freshnessYear ? `Updated through ${freshnessYear}` : 'Published dossier series'}</span>
      </div>
      <div class="cp2-trends-strip cp2-trends-strip-dossier">${cardHtml}</div>
    </div>`;
}

function cpTrimCopy(text, max = 180) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return '';
  if (clean.length <= max) return clean;
  return `${clean.slice(0, Math.max(0, max - 1)).trimEnd()}...`;
}

function cpFormatCompactUsd(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '—';
  const abs = Math.abs(num);
  if (abs >= 1e12) return `$${(num / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `$${(num / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(num / 1e6).toFixed(1)}M`;
  return `$${Math.round(num).toLocaleString()}`;
}

function cpFormatCompactCount(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '—';
  const abs = Math.abs(num);
  if (abs >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(num / 1e3).toFixed(0)}K`;
  return Math.round(num).toLocaleString();
}

function cpFormatCalendarDate(value) {
  if (!value) return 'Date pending';
  if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
    const dt = new Date(`${value}T00:00:00Z`);
    if (!Number.isNaN(dt.getTime())) {
      return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
    }
  }
  return String(value);
}

function cpGetStructuralCard(country, code) {
  const dossier = getCountryDossier(country);
  const cards = Array.isArray(dossier?.public_structural_cards) ? dossier.public_structural_cards : [];
  return cards.find(card => String(card?.code) === String(code)) || null;
}

function cpGetStructuralDisplayValue(country, code, fallback = '—') {
  const card = cpGetStructuralCard(country, code);
  return card?.display_value || fallback;
}

function cpGetEconomicSignal(name) {
  const wb = cpGetWb(name);
  const inflation = Number(wb?.inflation_consumer_prices_pct);
  const gdpPerCapita = Number(wb?.gdp_per_capita_constant_2015_usd);
  const militarySpendPct = Number(wb?.military_expenditure_pct_gdp);
  if (Number.isFinite(inflation) && inflation >= 15) {
    return {
      label: 'Inflation stress',
      note: `Consumer prices are running at ${inflation.toFixed(1)}%, which can tighten fiscal room and heighten social pressure.`,
    };
  }
  if (Number.isFinite(gdpPerCapita) && gdpPerCapita < 5000) {
    return {
      label: 'Low fiscal room',
      note: `GDP per capita is about ${cpFormatCompactUsd(gdpPerCapita)}, suggesting less room to absorb prolonged security shocks.`,
    };
  }
  if (Number.isFinite(militarySpendPct) && militarySpendPct >= 3) {
    return {
      label: 'Heavy defence load',
      note: `Military spending is ${militarySpendPct.toFixed(1)}% of GDP, keeping the defence burden high in the macro picture.`,
    };
  }
  return {
    label: 'Contained',
    note: `Inflation and defence spending remain within a more manageable public range, though the macro layer still conditions state capacity.`,
  };
}

function cpBuildHeroSection(name, summary, watchpoints, eventCount, latestEventDate) {
  const overallRiskScore = Number(summary?.overall_risk_score) || 0;
  const overallLevel = summary?.overall_risk_level || getOverallRiskBand(overallRiskScore);
  const leadingConstructLabel = summary?.leading_construct_label || summary?.leading_construct || 'Monitor loading';
  const leadingTrendLabel = summary?.leading_trend || 'steady';
  const economicSignal = cpGetEconomicSignal(name);
  const briefText = summary?.summary_text || 'No predictive summary is available yet.';
  const watchMarkup = watchpoints.slice(0, 2).map(item => `<div class="cp2-hero-watch-item">${escapeHtml(item)}</div>`).join('');
  const metricCards = [
    {
      label: 'Overall risk',
      value: formatMonitorValue(overallRiskScore) || '—',
      note: overallLevel,
      color: getMonitorScoreColor(overallRiskScore),
    },
    {
      label: 'Leading pressure',
      value: leadingConstructLabel,
      note: 'Current monitor driver',
      color: 'var(--slate)',
    },
    {
      label: 'Trajectory',
      value: String(leadingTrendLabel).toUpperCase(),
      note: '90-day direction',
      color: getMonitorTrendColor(leadingTrendLabel),
    },
    {
      label: 'Live field',
      value: String(eventCount),
      note: latestEventDate ? `Latest ${cpFormatCalendarDate(latestEventDate)}` : 'No live event yet',
      color: 'var(--slate)',
    },
    {
      label: 'Economic signal',
      value: economicSignal.label,
      note: cpTrimCopy(economicSignal.note, 92),
      color: 'var(--olive-mid)',
    },
  ].map(item => `
      <div class="cp2-kpi-card">
        <div class="cp2-kpi-label">${escapeHtml(item.label)}</div>
        <div class="cp2-kpi-value" style="color:${item.color};">${escapeHtml(String(item.value))}</div>
        <div class="cp2-kpi-note">${escapeHtml(String(item.note))}</div>
      </div>`).join('');

  return `
    <section class="cp2-hero-grid">
      <div class="cp2-hero-brief">
        <div class="cp2-summary-kicker">National Monitor Brief</div>
        <div class="cp2-summary-text">${escapeHtml(briefText)}</div>
        ${watchMarkup ? `<div class="cp2-hero-watchlist">${watchMarkup}</div>` : ''}
      </div>
      <div class="cp2-hero-metrics">${metricCards}</div>
    </section>`;
}

function cpBuildInstitutionalPanel(profileNote, watchpoints) {
  const note = profileNote || 'No institutional context is available yet.';
  const watchItems = watchpoints.length
    ? watchpoints.map(item => `<div class="cp2-watch-item">${escapeHtml(item)}</div>`).join('')
    : '<div class="cp2-watch-item">No watchpoints available yet.</div>';
  return `
    <section class="cp2-panel">
      <div class="cp2-col-kicker">Institutional Context</div>
      <div class="cp2-context-text">${escapeHtml(note)}</div>
      <div class="cp2-panel-subhead">What to watch</div>
      <div class="cp2-panel-list">${watchItems}</div>
    </section>`;
}

function cpBuildEconomyPanel(name, stats, prof) {
  const wb = cpGetWb(name);
  const economicSignal = cpGetEconomicSignal(name);
  const rows = [
    ['GDP per capita', cpFormatCompactUsd(wb?.gdp_per_capita_constant_2015_usd)],
    ['Inflation', cpGetStructuralDisplayValue(name, 'inflation_consumer_prices_pct', Number.isFinite(Number(wb?.inflation_consumer_prices_pct)) ? `${Number(wb.inflation_consumer_prices_pct).toFixed(1)}%` : '—')],
    ['Population', cpFormatCompactCount(wb?.population_total)],
    ['Military spending / GDP', cpGetStructuralDisplayValue(name, 'mil_exp_pct_gdp', prof?.gdpPct || '—')],
    ['Defence outlays', stats.spending || '—'],
    ['Rule of law', cpGetStructuralDisplayValue(name, 'wgi_rule_of_law', '—')],
    ['US aid FY25', stats.usAid || '—'],
  ];
  return `
    <section class="cp2-panel">
      <div class="cp2-col-kicker">Economy & State Capacity</div>
      <div class="cp2-panel-note">${escapeHtml(economicSignal.note)}</div>
      <div class="cp2-panel-stat-list">
        ${rows.map(([label, value]) => `
          <div class="cp2-panel-stat-row">
            <span class="cp2-ref-label">${escapeHtml(label)}</span>
            <span class="cp2-ref-val">${escapeHtml(String(value || '—'))}</span>
          </div>`).join('')}
      </div>
    </section>`;
}

function cpBuildLeadershipPanel(positions, election) {
  const leadershipItems = positions.slice(0, 5).map(item => `
      <div class="cp2-pos-item">
        <div class="cp2-pos-title">${escapeHtml(item.t || 'Position')}</div>
        <div class="cp2-pos-name">${escapeHtml(item.n || 'Name pending')}</div>
      </div>`).join('') || '<div class="cp2-ref-label">No position data.</div>';
  const electionDate = election?.date ? cpFormatCalendarDate(election.date) : 'Date pending';
  const electionType = election?.type || 'Election';
  const electionNote = election?.note ? cpTrimCopy(election.note, 140) : 'No election note is available yet.';
  return `
    <section class="cp2-panel">
      <div class="cp2-col-kicker">Leadership & Election Clock</div>
      <div class="cp2-panel-split">
        <div>
          <div class="cp2-panel-subhead">Key positions</div>
          <div class="cp2-panel-list">${leadershipItems}</div>
        </div>
        <div>
          <div class="cp2-panel-subhead">Next election</div>
          <div class="cp2-elect-type">${escapeHtml(electionType)}</div>
          <div class="cp2-elect-date">${escapeHtml(electionDate)}</div>
          <div class="cp2-elect-note">${escapeHtml(electionNote)}</div>
        </div>
      </div>
    </section>`;
}

function cpBuildDataWindowPanel(name, latestEventDate) {
  const dossier = getCountryDossier(name);
  const freshness = dossier?.public_freshness || {};
  const monitorGenerated = freshness.monitor_generated_at ? cpFormatCalendarDate(String(freshness.monitor_generated_at).slice(0, 10)) : 'Date pending';
  const structuralYear = freshness.structural_as_of_year ? `Through ${freshness.structural_as_of_year}` : 'Year pending';
  const eventsDate = freshness.events_as_of_date ? cpFormatCalendarDate(freshness.events_as_of_date) : cpFormatCalendarDate(latestEventDate);
  const coverageNote = freshness.series_coverage_note || 'Published dossier series plus current event reporting.';
  return `
    <section class="cp2-panel cp2-panel-muted">
      <div class="cp2-col-kicker">Data Window</div>
      <div class="cp2-panel-stat-list">
        <div class="cp2-panel-stat-row"><span class="cp2-ref-label">Monitor refresh</span><span class="cp2-ref-val">${escapeHtml(monitorGenerated)}</span></div>
        <div class="cp2-panel-stat-row"><span class="cp2-ref-label">Structural layer</span><span class="cp2-ref-val">${escapeHtml(structuralYear)}</span></div>
        <div class="cp2-panel-stat-row"><span class="cp2-ref-label">Event layer</span><span class="cp2-ref-val">${escapeHtml(eventsDate)}</span></div>
      </div>
      <div class="cp2-panel-note">${escapeHtml(coverageNote)}</div>
    </section>`;
}

function cpBuildEventTags(ev) {
  const tags = [];
  if (Array.isArray(ev?.event_signal_labels)) tags.push(...ev.event_signal_labels);
  if (Array.isArray(ev?.actors)) tags.push(...ev.actors);
  if (Array.isArray(ev?.event_construct_destinations)) {
    ev.event_construct_destinations.forEach(code => tags.push(getConstructLabel(code)));
  }
  const unique = [...new Set(tags.filter(Boolean).map(item => String(item).trim()).filter(Boolean))].slice(0, 6);
  if (!unique.length) return '';
  return `<div class="cp2-event-tag-strip">${unique.map(item => `<span class="cp2-event-tag">${escapeHtml(item)}</span>`).join('')}</div>`;
}

function cpBuildEventMonitorCue(ev) {
  const constructs = Array.isArray(ev?.event_construct_destinations)
    ? ev.event_construct_destinations.map(code => getConstructLabel(code)).filter(Boolean)
    : [];
  const lenses = Array.isArray(ev?.event_analyst_lenses) ? ev.event_analyst_lenses.filter(Boolean) : [];
  const cues = [];
  if (constructs.length) cues.push(`Pressure channels: ${constructs.slice(0, 3).join(', ')}`);
  if (lenses.length) cues.push(`Analyst lenses: ${lenses.slice(0, 3).join(', ')}`);
  if (!cues.length) return 'Track whether follow-on reporting changes confidence, actors, or escalation patterns.';
  return cues.join(' · ');
}

function cpEventDetailMarkup(ev){
  if(!ev){
    return `
      <div class="cp2-event-detail-empty">
        <div class="cp2-col-kicker">Field Note</div>
        <div class="cp2-event-empty-copy">Select a live event to see the reporting synthesis, monitor implications, and source trail without leaving the country profile.</div>
      </div>`;
  }
  return `
    <div class="cp2-event-detail-card cp2-event-detail-card-brief">
      ${buildEventAccordionDetail(ev)}
    </div>`;
}

function cpSelectCountryEvent(profileId, eventId){
  const ev = (allEvents || []).find(item => String(item.id) === String(eventId));
  document.querySelectorAll(`.cp2-event-item[data-profile-id="${profileId}"]`).forEach(item => {
    const isSelected = String(item.dataset.eventId) === String(eventId);
    item.classList.toggle('is-open', isSelected);
    const row = item.querySelector('.cp2-event-row');
    if (row) row.classList.toggle('selected', isSelected);
    const detail = item.querySelector('.cp2-event-inline-detail');
    if (detail) detail.innerHTML = isSelected ? cpEventDetailMarkup(ev) : '';
  });
}

function getMonitorTrendColor(label){
  const trend = String(label || '').toLowerCase();
  if(trend === 'rising') return 'var(--purge)';
  if(trend === 'easing') return 'var(--reform)';
  return 'var(--text-muted)';
}

function getMonitorScoreColor(score){
  const value = Number(score) || 0;
  if(value >= 75) return 'var(--coup)';
  if(value >= 55) return 'var(--purge)';
  if(value >= 35) return 'var(--aid)';
  return 'var(--reform)';
}

function getOverallRiskBand(score){
  const value = Number(score) || 0;
  if(value >= 75) return 'critical outlook';
  if(value >= 55) return 'elevated outlook';
  if(value >= 35) return 'guarded outlook';
  return 'lower-risk outlook';
}

function formatMonitorValue(score){
  return Number.isFinite(Number(score)) ? Math.round(Number(score)) : null;
}

function summarizeRegionalReadout(text){
  const raw = String(text || '').trim();
  if(!raw) return '';
  const firstSentence = raw.match(/.*?[.!?](?:\s|$)/)?.[0]?.trim() || raw;
  return firstSentence.length > 155 ? `${firstSentence.slice(0, 152).trim()}…` : firstSentence;
}

function buildRegionalMonitorNarrative(countries, data){
  if(!countries.length || !countryMonitorsByCountry.size) return data.note;
  const summaries = ['regime_vulnerability','militarization','security_fragmentation'].map(code => {
    const constructs = countries.map(country => getCountryRiskConstruct(country, code)).filter(Boolean);
    if(!constructs.length) return null;
    const avg = Math.round(constructs.reduce((sum, item) => sum + (Number(item.score) || 0), 0) / constructs.length);
    const rising = constructs.filter(item => String(item.trend_label || '').toLowerCase() === 'rising').length;
    return { code, avg, rising };
  }).filter(Boolean);
  if(!summaries.length) return data.note;
  const regime = summaries.find(item => item.code === 'regime_vulnerability');
  const militarization = summaries.find(item => item.code === 'militarization');
  const fragmentation = summaries.find(item => item.code === 'security_fragmentation');
  const bits = [];
  if(regime) bits.push(`regime vulnerability averages ${regime.avg}/100 across the visible set`);
  if(militarization) bits.push(`militarization averages ${militarization.avg}/100`);
  if(fragmentation) bits.push(`${fragmentation.rising} ${fragmentation.rising === 1 ? 'country is' : 'countries are'} on a rising fragmentation trend`);
  return `${data.note} ${bits.join(' · ')}.`;
}

function renderRegionalMonitorCards(){
  const cardsEl = document.getElementById('sr-cards');
  if(!cardsEl) return;
  const visibleCountries = getVisibleProfileCountries();
  const constructCodes = ['regime_vulnerability','militarization','security_fragmentation'];
  const cardData = constructCodes.map(code => {
    const constructs = visibleCountries.map(country => getCountryRiskConstruct(country, code)).filter(Boolean);
    if(!constructs.length) return null;
    const avgComposite = Math.round(constructs.reduce((sum, item) => sum + (Number(item.score) || 0), 0) / constructs.length);
    const rising = constructs.filter(item => String(item.trend_label || '').toLowerCase() === 'rising').length;
    return {
      label: constructs[0].label,
      value: `${avgComposite}/100`,
      sub: `${rising} rising · ${constructs[0].horizon_days || 90}-day horizon`,
      subClass: rising ? 'up' : ''
    };
  }).filter(Boolean);
  const risingTotal = visibleCountries.filter(country => {
    return ['regime_vulnerability','militarization','security_fragmentation']
      .some(code => String(getCountryRiskConstruct(country, code)?.trend_label || '').toLowerCase() === 'rising');
  }).length;
  const strongestCountry = visibleCountries
    .map(country => ({ country, score: Number(getCountryPredictiveSummary(country)?.overall_risk_score) || 0 }))
    .sort((a,b) => b.score - a.score)[0];
  const fallback = [
    { label:'Regime Vulnerability', value:'—', sub:'monitor not loaded', subClass:'' },
    { label:'Militarization', value:'—', sub:'monitor not loaded', subClass:'' },
    { label:'Security Fragmentation', value:'—', sub:'monitor not loaded', subClass:'' }
  ];
  const rows = (cardData.length ? cardData : fallback).concat([{
    label:'Rising Outlooks',
    value: `${risingTotal}`,
    sub: strongestCountry?.country ? `${strongestCountry.country} currently shows the highest overall risk score` : 'no current reading',
    subClass: risingTotal ? 'up' : ''
  }]);
  cardsEl.innerHTML = rows.slice(0,4).map(item => `
    <div class="cp-stat-card">
      <div class="cp-stat-card-label">${item.label}</div>
      <div class="cp-stat-card-value">${item.value}</div>
      <div class="cp-stat-card-sub ${item.subClass || ''}">${item.sub}</div>
    </div>`).join('');
}

function renderRegionalMonitorVisuals(){
  const visibleCountries = getVisibleProfileCountries();
  const mixes = ['cmr_balance','security_pressure','external_security_alignment'].map(code => {
    const monitors = visibleCountries.map(country => getCountryMonitor(country, code)).filter(Boolean);
    return {
      code,
      label: monitors[0]?.label || code,
      avgComposite: monitors.length ? Math.round(monitors.reduce((sum, item) => sum + (Number(item.composite_score) || 0), 0) / monitors.length) : 0,
      avgPulse: monitors.length ? Math.round(monitors.reduce((sum, item) => sum + (Number(item.pulse_score) || 0), 0) / monitors.length) : 0
    };
  });

  const leaders = visibleCountries.map(country => ({
    country,
    regime: formatMonitorValue(getCountryRiskConstruct(country, 'regime_vulnerability')?.score) || 0,
    militarization: formatMonitorValue(getCountryRiskConstruct(country, 'militarization')?.score) || 0,
    fragmentation: formatMonitorValue(getCountryRiskConstruct(country, 'security_fragmentation')?.score) || 0
  })).sort((a,b) => (b.regime + b.fragmentation) - (a.regime + a.fragmentation)).slice(0,6);

  const readoutsEl = document.getElementById('sr-monitor-readouts');
  if(readoutsEl){
    const dominant = visibleCountries.map(country => {
      const row = {
        country,
        regime: getCountryRiskConstruct(country, 'regime_vulnerability'),
        militarization: getCountryRiskConstruct(country, 'militarization'),
        fragmentation: getCountryRiskConstruct(country, 'security_fragmentation'),
        summary: getCountryPredictiveSummary(country)
      };
      const score = Number(row.summary?.overall_risk_score) || 0;
      return { ...row, score };
    }).sort((a,b) => b.score - a.score).slice(0,4);
    readoutsEl.innerHTML = dominant.length ? dominant.map(item => `
      <div class="cp-readout-row">
        <div class="cp-readout-top">
          <div class="cp-readout-country">${item.country}</div>
          <div class="cp-readout-score" style="color:${getMonitorScoreColor(item.score)};">overall risk ${item.score}/100</div>
        </div>
        <div class="cp-readout-text">${summarizeRegionalReadout(item.summary?.summary_text || 'No predictive summary is available yet.')}</div>
        <div class="cp-readout-score" style="margin-top:6px;">regime ${formatMonitorValue(item.regime?.score) || 0} · militarization ${formatMonitorValue(item.militarization?.score) || 0} · fragmentation ${formatMonitorValue(item.fragmentation?.score) || 0}</div>
      </div>`).join('') : '<div class="cp-readout-row"><div class="cp-readout-text">No regional monitor readouts are available yet.</div></div>';
  }

  if(typeof Chart === 'undefined') return;

  const spendCanvas = document.getElementById('spendChart');
  if(spendCanvas){
    regionalMixChart?.destroy();
    regionalMixChart = new Chart(spendCanvas,{
      type:'bar',
      data:{
        labels: mixes.map(item => item.label),
        datasets:[
          {label:'Baseline', data: mixes.map(item => Math.max(0, item.avgComposite - item.avgPulse)), backgroundColor:'rgba(85,107,47,0.35)', borderColor:'#556b2f', borderWidth:1, borderRadius:2},
          {label:'Pulse', data: mixes.map(item => item.avgPulse), backgroundColor:'rgba(200,110,18,0.45)', borderColor:'#c46e12', borderWidth:1, borderRadius:2}
        ]
      },
      options:{...chartOpts, plugins:{legend:{display:true,position:'top',labels:{color:chartText,font:{size:9,family:'DM Mono'},boxWidth:10,padding:10}}}, scales:{...chartOpts.scales,x:{...chartOpts.scales.x,stacked:true},y:{...chartOpts.scales.y,stacked:true,suggestedMax:100}}}
    });
  }

  const leadersCanvas = document.getElementById('armsChart');
  if(leadersCanvas){
    regionalLeadersChart?.destroy();
    regionalLeadersChart = new Chart(leadersCanvas,{
      type:'bar',
      data:{
        labels: leaders.map(item => item.country),
        datasets:[
          {label:'Regime vulnerability', data: leaders.map(item => item.regime), backgroundColor:'rgba(184,50,50,0.6)', borderColor:'#b83232', borderWidth:0, borderRadius:2},
          {label:'Militarization', data: leaders.map(item => item.militarization), backgroundColor:'rgba(85,107,47,0.58)', borderColor:'#556b2f', borderWidth:0, borderRadius:2},
          {label:'Security fragmentation', data: leaders.map(item => item.fragmentation), backgroundColor:'rgba(26,83,143,0.52)', borderColor:'#1a538f', borderWidth:0, borderRadius:2}
        ]
      },
      options:{...chartOpts, indexAxis:'y', plugins:{legend:{display:true,position:'top',labels:{color:chartText,font:{size:9,family:'DM Mono'},boxWidth:10,padding:10}}}, scales:{x:{grid:{color:chartGrid},ticks:{color:chartText,font:{size:9,family:'DM Mono'}},suggestedMax:100,border:{display:false}},y:{grid:{display:false},ticks:{color:chartText,font:{size:9,family:'DM Mono'}}}}}
    });
  }
}

function renderRegionalMonitorSummary(){
  const data = SUBREGIONS[cpActiveSr] || SUBREGIONS.all;
  const summaryEl = document.getElementById('sr-summary');
  if(summaryEl){
    summaryEl.textContent = buildRegionalMonitorNarrative(getVisibleProfileCountries(), data);
  }
  refreshCountryListButtons();
  renderRegionalMonitorCards();
  renderRegionalMonitorVisuals();
}

function refreshCountryListButtons(){
  const buttons = document.querySelectorAll('.cp-btn[data-country]');
  buttons.forEach(btn => {
    const country = btn.dataset.country;
    const summary = getCountryPredictiveSummary(country);
    const riskScore = Number(summary?.overall_risk_score) || 0;
    const riskBand = summary?.overall_risk_level || getOverallRiskBand(riskScore);
    const leadingTrend = summary?.leading_trend || 'steady';
    const leadingConstruct = summary?.leading_construct_label || summary?.leading_construct || 'monitor loading';
    const liveCount = (allEvents || []).filter(ev => matchesProfileCountryEvent(ev, country)).length;
    const constructs = ['regime_vulnerability','militarization','security_fragmentation']
      .map(code => getCountryRiskConstruct(country, code))
      .filter(Boolean);
    const measureBits = constructs.length
      ? constructs.map(item => {
          const short = item.code === 'regime_vulnerability' ? 'R' : item.code === 'militarization' ? 'M' : 'S';
          return `<span class="cp-btn-measure">${short} ${formatMonitorValue(item.score) || 0}</span>`;
        }).join('')
      : `<span class="cp-btn-measure">${btn.querySelector('small')?.textContent || ''}</span>`;
    const summaryText = summarizeRegionalReadout(summary?.summary_text || btn.querySelector('small')?.textContent || '');
    const compactSummary = summaryText.length > 54 ? `${summaryText.slice(0, 54).trim()}…` : summaryText;
    btn.innerHTML = `
      <span class="cp-btn-top">
        <strong>${escapeHtml(country)}</strong>
        <span class="cp-btn-risk" style="color:${getMonitorScoreColor(riskScore)};">${riskScore || '—'}</span>
      </span>
      <span class="cp-btn-sub">${escapeHtml(compactSummary)}</span>
      <span class="cp-btn-meta">
        <span class="cp-btn-measures">${measureBits}</span>
        <span class="cp-btn-trend">${escapeHtml(riskBand)} · ${escapeHtml(leadingTrend)}</span>
      </span>
      <span class="cp-btn-footer">
        <span class="cp-btn-signal">${escapeHtml(String(leadingConstruct))}</span>
        <span class="cp-btn-live">${liveCount} live</span>
      </span>`;
  });
}

// ── MAP ─────────────────────────────────────────────────────
function ensureEventMap(){
  if(!eventsMapSvg){
    initMap();
    return;
  }
  refreshMap(filtered);
}

function initMap(){
  eventsMapWrap = document.getElementById('map');
  eventsMapSvg = d3.select('#events-map-svg');
  eventsMapTooltip = document.getElementById('events-map-tooltip');
  map = {
    invalidateSize(){
      refreshMap(filtered);
    }
  };
  if(!eventsMapResizeBound){
    const rerender = ()=>{
      if(document.getElementById('events')?.classList.contains('active')){
        refreshMap(filtered);
      }
    };
    window.addEventListener('resize', rerender);
    if(typeof ResizeObserver !== 'undefined' && eventsMapWrap){
      new ResizeObserver(rerender).observe(eventsMapWrap);
    }
    eventsMapResizeBound = true;
  }
  ensureWorldFeaturesLoaded()
    .then(()=>refreshMap(filtered))
    .catch(error=>console.error('Event map geometry load failed', error));
}

function getEventPressureWeight(ev){
  if(ev.salience === 'high') return 3;
  if(ev.salience === 'medium') return 2;
  return 1;
}

function hasFiniteCoords(coords){
  return Array.isArray(coords) && coords.length === 2 && Number.isFinite(+coords[0]) && Number.isFinite(+coords[1]);
}

function getExactEventCoords(ev){
  if(hasFiniteCoords(ev?.coords)){
    return [+ev.coords[0], +ev.coords[1]];
  }
  return null;
}

function getCountryCentroidCoords(country, options = {}){
  const cfg = COUNTRY_MAP_CONFIG[country];
  if(!cfg) return null;
  const [lat, lng] = cfg.center;
  const jitter = options.jitter !== false;
  if(!jitter) return [lat, lng];
  const seed = String(options.seed || country);
  const hash = stableHash(seed);
  const latOffset = (((hash % 1000) / 1000) - 0.5) * 1.25;
  const lngOffset = ((((Math.floor(hash / 1000)) % 1000) / 1000) - 0.5) * 1.55;
  return [lat + latOffset, lng + lngOffset];
}

function getEventMapDisplayMode(){
  if(selected) return 'events';
  if(filters.country !== 'all' && filters.country !== 'regional') return 'events';
  return 'pressure';
}

function getEventMapDimensions(){
  const width = Math.max(320, Math.round(eventsMapWrap?.clientWidth || 0));
  const height = Math.max(360, Math.round(eventsMapWrap?.clientHeight || 0));
  return { width, height };
}

function getEventMapLatamFeatures(){
  return (worldFeatures || []).filter(feature=>LATAM_IDS.has(+feature.id));
}

function getEventMapCountryFeature(country){
  const numId = COUNTRY_NAME_TO_ID[country];
  if(!numId || !worldFeatures) return null;
  return worldFeatures.find(feature=>+feature.id===numId) || null;
}

function getEventMapFocusCountries(){
  if(selected){
    const selectedCountries = getEventProfileCountries(selected);
    if(selectedCountries.length) return selectedCountries;
  }
  if(filters.country && !['all','regional'].includes(filters.country)){
    return [filters.country];
  }
  return [];
}

function getEventMapContext(){
  if(!eventsMapSvg || !eventsMapWrap || !worldFeatures) return null;
  const { width, height } = getEventMapDimensions();
  const latamFeatures = getEventMapLatamFeatures();
  const focusCountries = getEventMapFocusCountries();
  const focusFeatures = focusCountries.map(country=>getEventMapCountryFeature(country)).filter(Boolean);
  const fitFeatures = focusFeatures.length ? focusFeatures : latamFeatures;
  const projection = d3.geoMercator()
    .fitExtent([[20,18],[width-20,height-18]], { type:'FeatureCollection', features: fitFeatures });
  const path = d3.geoPath(projection);
  eventsMapProjection = projection;
  eventsMapPath = path;
  eventsMapSvg.attr('viewBox', `0 0 ${width} ${height}`);
  return { width, height, latamFeatures, focusCountries, focusFeatures, projection, path };
}

function getRiskBubbleFill(score){
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  return d3.scaleLinear()
    .domain([0, 50, 100])
    .range(['#2d8659', '#d2ad42', '#b83232'])
    .interpolate(d3.interpolateRgb)(value);
}

function showEventsMapTooltip(event, title, meta){
  if(!eventsMapTooltip || !eventsMapWrap) return;
  const bounds = eventsMapWrap.getBoundingClientRect();
  eventsMapTooltip.innerHTML = `<strong>${escapeHtml(title)}</strong>${meta ? `<span class="meta">${escapeHtml(meta)}</span>` : ''}`;
  eventsMapTooltip.style.display = 'block';
  eventsMapTooltip.style.left = `${event.clientX - bounds.left + 14}px`;
  eventsMapTooltip.style.top = `${event.clientY - bounds.top + 14}px`;
}

function hideEventsMapTooltip(){
  if(eventsMapTooltip) eventsMapTooltip.style.display = 'none';
}

function buildEventPressureByCountry(evs){
  const grouped = new Map();
  evs.forEach(ev=>{
    const countries = getEventProfileCountries(ev);
    if(!countries.length) return;
    countries.forEach(country=>{
      if(!COUNTRY_MAP_CONFIG[country]) return;
      const entry = grouped.get(country) || {
        country,
        coords: COUNTRY_MAP_CONFIG[country].center,
        count: 0,
        weight: 0,
        highCount: 0,
        typeCounts: {}
      };
      entry.count += 1;
      entry.weight += getEventPressureWeight(ev);
      if(ev.salience === 'high') entry.highCount += 1;
      entry.typeCounts[ev.type] = (entry.typeCounts[ev.type] || 0) + 1;
      grouped.set(country, entry);
    });
  });
  return [...grouped.values()].map(entry=>{
    const dominantType = Object.entries(entry.typeCounts).sort((a,b)=>b[1]-a[1])[0]?.[0] || 'other';
    const size = Math.max(42, Math.min(76, 26 + Math.sqrt(entry.weight) * 6));
    return {
      ...entry,
      dominantType,
      size
    };
  }).sort((a,b)=>b.weight-a.weight);
}

function updateEventMapLegend(mode){
  const legend = document.getElementById('map-legend');
  if(!legend) return;
  const collapsed = legend.classList.contains('is-collapsed');
  const pressureItems = `
    <div class="legend-item"><div class="leg-dot" style="width:12px;height:12px;background:rgba(142,68,48,0.30);border:2px solid #8e4430;"></div>Darker country fill indicates greater event density</div>
    <div class="legend-item"><div class="leg-dot" style="width:12px;height:12px;background:rgba(26,83,143,0.24);border:2px solid #1a538f;"></div>Country border color shows the dominant event family</div>
    <div class="legend-item"><div class="leg-dot" style="width:12px;height:12px;background:rgba(255,251,244,0.88);border:1px solid rgba(26,24,20,0.18);"></div>Click a country surface to drill into event locations</div>
  `;
  const eventItems = `
    <div class="legend-item"><div class="leg-dot" style="width:12px;height:12px;background:rgba(184,150,62,0.15);border:2px solid rgba(255,255,255,0.85);"></div>Dot color shows event family</div>
    <div class="legend-item"><div class="leg-dot" style="width:12px;height:12px;background:rgba(184,150,62,0.15);border:2px solid rgba(255,255,255,0.85);box-shadow:0 0 0 4px rgba(184,150,62,0.08);"></div>Dot size reflects salience for precisely located events</div>
    <div class="legend-item"><div class="leg-dot" style="width:18px;height:14px;border-radius:8px;background:rgba(255,251,244,0.88);border:1px solid rgba(23,21,18,0.14);"></div>Country-level stacks collect reports without exact geolocation</div>
    <div class="legend-item"><div class="leg-dot" style="width:12px;height:12px;background:rgba(26,83,143,0.15);border:2px solid var(--aid);"></div>Selected event opens a focused country field</div>
  `;
  legend.innerHTML = `
    <div class="legend-head">
      <div class="legend-title">${mode === 'pressure' ? 'Regional Pressure View' : 'Event Field View'}</div>
      <button class="legend-toggle" type="button" onclick="toggleMapLegend()"><span id="map-legend-toggle-label">${collapsed ? 'Show' : 'Hide'}</span></button>
    </div>
    ${mode === 'pressure' ? pressureItems : eventItems}
  `;
  legend.classList.toggle('is-collapsed', collapsed);
}

function updateEventMapStatus(mode){
  eventMapRendererMode = mode;
  const pill = document.getElementById('events-map-mode-pill');
  const note = document.getElementById('events-map-note');
  const label = document.querySelector('#events .map-label');
  const isFocusedCountryView = !!selected && mode !== 'pressure';
  if(pill){
    pill.textContent = mode === 'pressure' ? 'Regional Pressure View' : (isFocusedCountryView ? 'Country Focus View' : 'Event Field View');
  }
  if(note){
    note.textContent = mode === 'pressure'
      ? 'Country shading reflects event density. Border color shows the dominant event family. Click a country surface to drill into event locations.'
      : (isFocusedCountryView
        ? 'The field is now narrowed to the selected country. Precisely located events remain as points, while country-level reporting collapses into stack badges.'
        : 'Individual events are now visible. Precisely located reporting appears as dots, while country-level reporting is folded into country signal stacks.');
  }
  if(label){
    label.textContent = mode === 'pressure'
      ? 'Latin America — Country Pressure Surface'
      : (isFocusedCountryView ? 'Selected Country — Event Field Focus' : 'Latin America — Event Locations & Selected Cases');
  }
  updateEventMapLegend(mode);
}

function renderEventPressureMap(evs){
  const ctx = getEventMapContext();
  if(!ctx) return;
  const { latamFeatures, projection, path } = ctx;
  const svg = eventsMapSvg;
  svg.selectAll('*').remove();
  const pressureEntries = buildEventPressureByCountry(evs);
  const pressureByCountry = new Map(pressureEntries.map(entry=>[entry.country, entry]));
  const maxWeight = pressureEntries.reduce((max, entry)=>Math.max(max, entry.weight), 0);

  svg.append('g')
    .attr('class','events-map-surface')
    .selectAll('path.country')
    .data(latamFeatures)
    .enter()
    .append('path')
    .attr('d', path)
    .attr('fill', feature=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      const entry = pressureByCountry.get(country);
      const density = maxWeight > 0 ? ((entry?.weight || 0) / maxWeight) : 0;
      const fill = d3.color('#efe8dc');
      fill.opacity = 0.48 + (density * 0.42);
      return `${fill}`;
    })
    .attr('stroke', feature=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      const entry = pressureByCountry.get(country);
      return entry ? (TC_HEX[entry.dominantType] || '#8b7d6b') : 'rgba(171,158,141,0.72)';
    })
    .attr('stroke-width', feature=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      const entry = pressureByCountry.get(country);
      return entry?.highCount ? 2.4 : entry ? 1.8 : 1.1;
    })
    .on('mouseenter', (event, feature)=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      const entry = pressureByCountry.get(country);
      const risk = formatMonitorValue(getCountryPredictiveSummary(country)?.overall_risk_score) ?? '—';
      const message = entry ? `${entry.count} visible events · dominant ${getEventTypeLabel(entry.dominantType)}` : 'No currently visible events';
      showEventsMapTooltip(event, `${country} · risk ${risk}`, message);
    })
    .on('mousemove', (event, feature)=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      const entry = pressureByCountry.get(country);
      const risk = formatMonitorValue(getCountryPredictiveSummary(country)?.overall_risk_score) ?? '—';
      const message = entry ? `${entry.count} visible events · dominant ${getEventTypeLabel(entry.dominantType)}` : 'No currently visible events';
      showEventsMapTooltip(event, `${country} · risk ${risk}`, message);
    })
    .on('mouseleave', hideEventsMapTooltip)
    .on('click', (event, feature)=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      if(!country) return;
      const countrySel = document.getElementById('country-filter-select');
      filters.country = country;
      if(countrySel) countrySel.value = country;
      selected = null;
      renderEventDetailEmpty();
      setEventCountryOverlayOpen(false);
      applyFilters('country');
    });

  const bubbles = svg.append('g').attr('class','events-risk-bubbles');
  latamFeatures.forEach(feature=>{
    const country = COUNTRY_NAMES_MAP[+feature.id];
    if(!country) return;
    const summary = getCountryPredictiveSummary(country);
    const riskScore = formatMonitorValue(summary?.overall_risk_score);
    if(riskScore == null) return;
    const center = COUNTRY_MAP_CONFIG[country]?.center;
    if(!center) return;
    const [lat, lng] = center;
    const point = projection([lng, lat]);
    if(!point) return;
    const entry = pressureByCountry.get(country);
    const bubble = bubbles.append('g')
      .attr('class','events-risk-bubble')
      .attr('transform', `translate(${point[0]}, ${point[1]})`)
      .on('mouseenter', event=>{
        const message = entry ? `${entry.count} visible events · click to filter this country` : 'Click to filter this country';
        showEventsMapTooltip(event, `${country} · overall risk ${riskScore}`, message);
      })
      .on('mousemove', event=>{
        const message = entry ? `${entry.count} visible events · click to filter this country` : 'Click to filter this country';
        showEventsMapTooltip(event, `${country} · overall risk ${riskScore}`, message);
      })
      .on('mouseleave', hideEventsMapTooltip)
      .on('click', ()=>{
        const countrySel = document.getElementById('country-filter-select');
        filters.country = country;
        if(countrySel) countrySel.value = country;
        selected = null;
        renderEventDetailEmpty();
        setEventCountryOverlayOpen(false);
        applyFilters('country');
      });
    bubble.append('circle')
      .attr('r', 12 + (riskScore / 100) * 14)
      .attr('fill', getRiskBubbleFill(riskScore))
      .attr('fill-opacity', 0.90)
      .attr('stroke', '#fff6ea')
      .attr('stroke-width', 2.4);
    bubble.append('text')
      .attr('text-anchor','middle')
      .attr('dy','0.36em')
      .text(riskScore);
  });
}

function renderEventMarkerMap(evs){
  const ctx = getEventMapContext();
  if(!ctx) return;
  const { latamFeatures, focusCountries, projection, path } = ctx;
  const svg = eventsMapSvg;
  svg.selectAll('*').remove();
  const focusActive = !!focusCountries.length;
  const scopedEvents = focusActive
    ? evs.filter(ev => {
        const countries = getEventProfileCountries(ev);
        return countries.some(country => focusCountries.includes(country));
      })
    : evs;
  svg.append('g')
    .attr('class','events-map-surface')
    .selectAll('path.country')
    .data(latamFeatures)
    .enter()
    .append('path')
    .attr('d', path)
    .attr('fill', feature=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      return focusCountries.includes(country) ? 'rgba(246,239,224,0.98)' : 'rgba(247,244,237,0.80)';
    })
    .attr('stroke', feature=>{
      const country = COUNTRY_NAMES_MAP[+feature.id];
      if(focusCountries.includes(country)){
        return selected ? (TC_HEX[selected.type] || '#ad7f34') : '#ad7f34';
      }
      return 'rgba(192,180,163,0.56)';
    })
    .attr('stroke-width', feature=>focusCountries.includes(COUNTRY_NAMES_MAP[+feature.id]) ? 2.6 : 1.0);

  const approximateStacks = new Map();
  const markerLayer = svg.append('g').attr('class','events-map-markers');
  scopedEvents.forEach(ev=>{
    const exactCoords = getExactEventCoords(ev);
    const countries = getEventProfileCountries(ev);
    const c=TC_HEX[ev.type]||'#6a6560';
    const title=(ev.standard_title || getStandardizedEventTitle(ev));
    const isSelected = selected?.id === ev.id;
    if(exactCoords){
      const point = projection([+exactCoords[1], +exactCoords[0]]);
      if(!point) return;
      const marker = markerLayer.append('g')
        .attr('class','events-event-dot')
        .attr('transform', `translate(${point[0]}, ${point[1]})`)
        .on('mouseenter', event=>{
          showEventsMapTooltip(event, getEventTypeLabel(ev.type).toUpperCase(), `${title.substring(0,72)}${title.length>72?'…':''}${countries[0] ? ` · ${countries[0]}` : ''}`);
        })
        .on('mousemove', event=>{
          showEventsMapTooltip(event, getEventTypeLabel(ev.type).toUpperCase(), `${title.substring(0,72)}${title.length>72?'…':''}${countries[0] ? ` · ${countries[0]}` : ''}`);
        })
        .on('mouseleave', hideEventsMapTooltip)
        .on('click', ()=>selectEvent(ev));
      if(isSelected){
        marker.append('circle')
          .attr('r', ev.salience==='high' ? 13 : 11)
          .attr('fill', c)
          .attr('fill-opacity', 0.10)
          .attr('stroke', c)
          .attr('stroke-width', 2.2);
      }
      marker.append('circle')
        .attr('r', isSelected ? 8.6 : ev.salience==='high' ? 6.9 : ev.salience==='medium' ? 5.2 : 4.1)
        .attr('fill', c)
        .attr('fill-opacity', isSelected ? 0.92 : (focusActive ? 0.68 : 0.84))
        .attr('stroke', isSelected ? '#fff8ee' : 'rgba(255,255,255,0.90)')
        .attr('stroke-width', isSelected ? 2.5 : 1.6);
      return;
    }

    const fallbackCountries = countries.length
      ? countries
      : (getEventCountryLabel(ev) === 'Regional' ? [] : [getEventCountryLabel(ev)]);
    fallbackCountries.forEach(country=>{
      if(!country || !COUNTRY_MAP_CONFIG[country]) return;
      const stack = approximateStacks.get(country) || {
        country,
        count:0,
        highCount:0,
        selectedCount:0,
        weight:0,
        typeCounts:{},
        events:[]
      };
      stack.count += 1;
      stack.weight += getEventPressureWeight(ev);
      if(ev.salience === 'high') stack.highCount += 1;
      if(isSelected) stack.selectedCount += 1;
      stack.typeCounts[ev.type] = (stack.typeCounts[ev.type] || 0) + 1;
      stack.events.push(ev);
      approximateStacks.set(country, stack);
    });
  });

  [...approximateStacks.values()].forEach(stack=>{
    const dominantType = Object.entries(stack.typeCounts).sort((a,b)=>b[1]-a[1])[0]?.[0] || 'other';
    const coords = getCountryCentroidCoords(stack.country, { jitter:false });
    if(!coords) return;
    const point = projection([+coords[1], +coords[0]]);
    if(!point) return;
    const stackGroup = markerLayer.append('g')
      .attr('class','events-event-stack')
      .attr('transform', `translate(${point[0] - 40}, ${point[1] - 18})`)
      .on('mouseenter', event=>{
        showEventsMapTooltip(event, stack.country, `${stack.count} country-level report${stack.count===1?'':'s'} · dominant ${getEventTypeLabel(dominantType)}`);
      })
      .on('mousemove', event=>{
        showEventsMapTooltip(event, stack.country, `${stack.count} country-level report${stack.count===1?'':'s'} · dominant ${getEventTypeLabel(dominantType)}`);
      })
      .on('mouseleave', hideEventsMapTooltip)
      .on('click', ()=>selectEvent(selected && stack.selectedCount ? selected : stack.events[0]));
    stackGroup.append('rect')
      .attr('width', 80)
      .attr('height', 36)
      .attr('rx', 16)
      .attr('fill', 'rgba(255,251,244,0.92)')
      .attr('stroke', `${TC_HEX[dominantType] || '#6a6560'}55`)
      .attr('stroke-width', stack.selectedCount ? 2.2 : 1.2);
    stackGroup.append('text')
      .attr('class','count')
      .attr('x', 40)
      .attr('y', 15)
      .attr('text-anchor','middle')
      .text(stack.count > 99 ? '99+' : stack.count);
    stackGroup.append('text')
      .attr('class','label')
      .attr('x', 40)
      .attr('y', 28)
      .attr('text-anchor','middle')
      .text('country-level');
  });
}

function refreshMap(evs){
  if(!eventsMapSvg){
    initMap();
    return;
  }
  if(!worldFeatures){
    ensureWorldFeaturesLoaded().then(()=>refreshMap(evs)).catch(error=>console.error('Event map render failed', error));
    return;
  }
  hideEventsMapTooltip();
  const mode = getEventMapDisplayMode();
  updateEventMapStatus(mode);
  if(mode === 'pressure'){
    renderEventPressureMap(evs);
    return;
  }
  renderEventMarkerMap(evs);
}

function toggleMapLegend(){
  const legend = document.getElementById('map-legend');
  const label = document.getElementById('map-legend-toggle-label');
  if(!legend || !label) return;
  legend.classList.toggle('is-collapsed');
  label.textContent = legend.classList.contains('is-collapsed') ? 'Show' : 'Hide';
}

globalThis.toggleMapLegend = toggleMapLegend;

// ── FILTERS ─────────────────────────────────────────────────
function closeEventFilterPickers(){
  document.querySelectorAll('.events-picker.is-open').forEach(picker=>{
    picker.classList.remove('is-open');
    const trigger = picker.querySelector('.events-picker-trigger');
    trigger?.setAttribute('aria-expanded','false');
  });
}

function renderPickerFromSelect(selectId, pickerId, triggerId, menuId){
  const select = document.getElementById(selectId);
  const picker = document.getElementById(pickerId);
  const trigger = document.getElementById(triggerId);
  const menu = document.getElementById(menuId);
  const triggerCopy = trigger?.querySelector('.events-picker-trigger-copy');
  if(!select || !picker || !trigger || !menu || !triggerCopy) return;
  const options = [...select.options].map(option=>({
    value: option.value,
    label: option.textContent || option.value
  }));
  const active = options.find(option=>option.value === select.value) || options[0];
  triggerCopy.textContent = active?.label || '';
  menu.innerHTML = options.map(option=>`
    <button class="events-picker-option${option.value === select.value ? ' is-active' : ''}" type="button" data-value="${escapeHtml(option.value)}" role="option" aria-selected="${option.value === select.value ? 'true' : 'false'}">
      <span>${escapeHtml(option.label)}</span>
      ${option.value === select.value ? '<span class="events-picker-option-note">Active</span>' : ''}
    </button>
  `).join('');
  menu.querySelectorAll('.events-picker-option').forEach(button=>{
    button.addEventListener('click',()=>{
      const nextValue = button.dataset.value || '';
      if(select.value !== nextValue){
        select.value = nextValue;
        select.dispatchEvent(new Event('change',{ bubbles:true }));
      }
      closeEventFilterPickers();
    });
  });
}

function syncEventFilterPicker(kind){
  renderPickerFromSelect(
    `${kind}-filter-select`,
    `${kind}-filter-picker`,
    `${kind}-filter-picker-trigger`,
    `${kind}-filter-picker-menu`
  );
}

function syncFeedbackPicker(kind){
  renderPickerFromSelect(
    `fb-${kind}`,
    `fb-${kind}-picker`,
    `fb-${kind}-picker-trigger`,
    `fb-${kind}-picker-menu`
  );
}

function buildCountries(){
  const sel=document.getElementById('country-filter-select');
  if(!sel) return;
  const tracked=[...(SUBREGIONS?.all?.countries || [])].sort();
  sel.innerHTML='';
  [
    ['all','All tracked countries'],
    ['regional','Regional']
  ].forEach(([value,label])=>{
    const opt=document.createElement('option');
    opt.value=value;
    opt.textContent=label;
    sel.appendChild(opt);
  });
  tracked.forEach(country=>{
    const opt=document.createElement('option');
    opt.value=country;
    opt.textContent=country;
    sel.appendChild(opt);
  });
  syncEventFilterPicker('country');
}

function renderTypeFilterOptions(){
  const sel=document.getElementById('type-filter-select');
  if(!sel) return;
  sel.innerHTML='';
  const base=document.createElement('option');
  base.value='all';
  base.textContent='All domains';
  sel.appendChild(base);
  const types=[...new Set(allEvents.map(ev=>ev.event_type_domain || ev.event_category).filter(Boolean))].sort();
  types.forEach(code=>{
    const opt=document.createElement('option');
    opt.value=code;
    opt.textContent=getEventDomainLabel(code);
    sel.appendChild(opt);
  });
  syncEventFilterPicker('type');
}

function renderCategoryFilterOptions(){
  const sel=document.getElementById('category-filter-select');
  if(!sel) return;
  sel.innerHTML='';
  const base=document.createElement('option');
  base.value='all';
  base.textContent='All categories';
  sel.appendChild(base);
  const categories=[...new Map(
    allEvents
      .filter(ev=>ev.public_category_key)
      .map(ev=>[
        ev.public_category_key,
        {
          key: ev.public_category_key,
          label: ev.public_category_label || normalizeKnowledgeLabel(ev.public_category_key),
          rank: Number(ev.public_category_rank) || publicCategoryMeta.get(ev.public_category_key)?.rank || 999
        }
      ])
  ).values()].sort((a,b)=>(a.rank-b.rank) || a.label.localeCompare(b.label));
  categories.forEach(item=>{
    const opt=document.createElement('option');
    opt.value=item.key;
    opt.textContent=item.label;
    sel.appendChild(opt);
  });
  syncEventFilterPicker('category');
}

function renderSignalFilterOptions(){
  const sel=document.getElementById('signal-filter-select');
  if(!sel) return;
  sel.innerHTML='';
  const base=document.createElement('option');
  base.value='all';
  base.textContent='All signals';
  sel.appendChild(base);
  const signals=[...new Map(
    allEvents.flatMap(ev=>{
      const ids = Array.isArray(ev.event_signal_families) ? ev.event_signal_families : [];
      const labels = Array.isArray(ev.event_signal_labels) ? ev.event_signal_labels : [];
      return ids.map((id,index)=>[
        id,
        {
          id,
          label: labels[index] || eventSignalMeta.get(id) || normalizeKnowledgeLabel(id)
        }
      ]);
    })
  ).values()].sort((a,b)=>(EVENT_SIGNAL_ORDER[a.id]||999)-(EVENT_SIGNAL_ORDER[b.id]||999) || a.label.localeCompare(b.label));
  signals.forEach(item=>{
    const opt=document.createElement('option');
    opt.value=item.id;
    opt.textContent=item.label;
    sel.appendChild(opt);
  });
  syncEventFilterPicker('signal');
}

function getEventTypeLabel(code){
  return eventTypeMeta.get(String(code))?.label || TYPE_LABEL[code] || String(code || 'Other');
}

function normalizeKnowledgeLabel(value){
  let text = String(value || '');
  if(text.startsWith('REL_')) text = text.slice(4);
  if(text.startsWith('INT_')) text = text.slice(4);
  return text
    .replace(/_/g,' ')
    .replace(/\b\w/g,ch=>ch.toUpperCase());
}

function getEventCategoryLabel(value){
  const key = String(value || '').trim().toLowerCase();
  return EVENT_CATEGORY_LABEL[key] || normalizeKnowledgeLabel(value || 'Not specified');
}

function getEventDomainLabel(value){
  return getEventCategoryLabel(value);
}

function getPublicCategoryLabel(ev){
  return ev?.public_category_label || publicCategoryMeta.get(String(ev?.public_category_key || ''))?.label || 'Not specified';
}

function getEventSignalLabels(ev){
  const ids = Array.isArray(ev?.event_signal_families) ? ev.event_signal_families : [];
  const labels = Array.isArray(ev?.event_signal_labels) ? ev.event_signal_labels : [];
  if(labels.length) return labels.filter(Boolean);
  return ids.map(id=>eventSignalMeta.get(String(id)) || normalizeKnowledgeLabel(id));
}

function getEventFamilyLabel(ev){
  return ev.event_category_label || getEventTypeLabel(ev.event_category_family || ev.type);
}

function getEventSubcategoryLabel(value){
  if(!value) return 'Not specified';
  return normalizeKnowledgeLabel(value);
}

function getEventAnalystLenses(ev){
  const lenses = Array.isArray(ev.event_analyst_lenses) ? ev.event_analyst_lenses : [];
  return lenses
    .map(item => ANALYST_LENS_META[String(item || '').trim().toLowerCase()] || null)
    .filter(Boolean);
}

function getEventCountryLabel(ev){
  const raw=String(ev.country||'').trim();
  if(!raw) return 'Regional';
  const tracked = new Set(SUBREGIONS?.all?.countries || []);
  if(tracked.has(raw)) return raw;
  if(/regional|latin america|latin america and the caribbean|caribbean basin/i.test(raw)) return 'Regional';
  return raw;
}

function getTrackedCountryNames(){
  return [...(SUBREGIONS?.all?.countries || [])];
}

function escapeHtml(value){
  return String(value ?? '')
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

function sanitizeExternalUrl(value){
  const raw = String(value ?? '').trim();
  if(!/^https?:\/\//i.test(raw)) return '';
  try{
    const parsed = new URL(raw);
    return /^(https?:)$/.test(parsed.protocol) ? parsed.href : '';
  }catch{
    return '';
  }
}

function getEventCountryTags(ev){
  const tracked = getTrackedCountryNames();
  const trackedSet = new Set(tracked);
  const explicit = String(ev.country || '').trim();
  const primary = trackedSet.has(explicit) ? explicit : null;
  const text = [
    ev.country,
    ev.display_country,
    ev.location,
    ev.subnational_location,
    ev.standard_title,
    ev.title,
    ev.summary
  ].filter(Boolean).join(' · ');

  const mentioned = tracked.filter(country=>{
    const escaped = country.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    return new RegExp(`\\b${escaped}\\b`, 'i').test(text);
  });

  const tags = [];
  if(primary) tags.push(primary);
  mentioned.forEach(country=>{
    if(!tags.includes(country)) tags.push(country);
  });
  if(!tags.length){
    const label = ev.display_country || getEventCountryLabel(ev);
    return [{ label, isProfile:false, isPrimary:true }];
  }
  return tags.slice(0, 4).map((country, index)=>({
    label: country,
    isProfile: trackedSet.has(country),
    isPrimary: index === 0
  }));
}

function getEventProfileCountries(ev){
  return getEventCountryTags(ev)
    .filter(item=>item.isProfile && item.label !== 'Regional')
    .map(item=>item.label);
}

function matchesProfileCountryEvent(ev, countryName){
  return getEventProfileCountries(ev).includes(countryName) || getEventCountryKey(ev) === countryName;
}

function renderCountryTagHtml(item){
  const classes = ['ev-country-tag'];
  if(item.isPrimary) classes.push('is-primary');
  const safeLabel = escapeHtml(item.label);
  return `<span class="${classes.join(' ')}">${safeLabel}</span>`;
}

function getOverallRiskTone(score){
  const value = Number(score);
  if(!Number.isFinite(value)) return 'medium';
  if(value >= 75) return 'critical';
  if(value >= 55) return 'high';
  if(value >= 35) return 'medium';
  return 'low';
}

function getConstructShortCode(code){
  if(code === 'regime_vulnerability') return 'R';
  if(code === 'militarization') return 'M';
  if(code === 'security_fragmentation') return 'S';
  return '•';
}

function getConstructAccent(code){
  if(code === 'regime_vulnerability') return '#b85a32';
  if(code === 'militarization') return '#556b2f';
  if(code === 'security_fragmentation') return '#1a538f';
  return '#7b756b';
}

function getConstructLabel(code){
  return ({
    regime_vulnerability:'Regime Vulnerability',
    militarization:'Militarization',
    security_fragmentation:'Security Fragmentation'
  })[String(code || '')] || normalizeKnowledgeLabel(code || 'Monitor');
}

function getLeadingConstructMeta(country){
  const summary = getCountryPredictiveSummary(country);
  const code = summary?.leading_construct || ['regime_vulnerability','militarization','security_fragmentation']
    .map(key=>getCountryRiskConstruct(country, key))
    .filter(Boolean)
    .sort((a,b)=>(Number(b.score) || 0) - (Number(a.score) || 0))[0]?.code || null;
  if(!code) return null;
  const construct = getCountryRiskConstruct(country, code);
  return {
    code,
    short:getConstructShortCode(code),
    label:getConstructLabel(code),
    color:getConstructAccent(code),
    trend:summary?.leading_trend || construct?.trend_label || 'stable',
    score:formatMonitorValue(summary?.[`${code}_score`] ?? construct?.score)
  };
}

function getEventWhyLine(ev){
  const leading = getLeadingConstructMeta(ev.country || ev.display_country || getEventCountryLabel(ev));
  const publicContext = getPublicEventContext(ev);
  const publicAnalysis = cleanCouncilAssessment(ev.public_analysis || '');
  const contextSentence = firstSentence(publicContext || publicAnalysis || ev.summary || '');
  if(leading && contextSentence){
    return `${leading.label} is the active monitor pressure. ${contextSentence}`;
  }
  if(leading){
    return `${leading.label} is the active monitor pressure shaping why this event matters now.`;
  }
  return contextSentence || '';
}

function parseEventDateValue(value){
  const ts = Date.parse(String(value || ''));
  return Number.isFinite(ts) ? ts : null;
}

function matchesDateRange(ev, range){
  if(range === 'all') return true;
  const ts = parseEventDateValue(ev.date);
  if(ts == null) return true;
  const days = range === '30d' ? 30 : range === '90d' ? 90 : null;
  if(days == null) return true;
  return ts >= (Date.now() - (days * 86400000));
}

function matchesEventSearch(ev, query){
  const needle = String(query || '').trim().toLowerCase();
  if(!needle) return true;
  const hay = [
    ev.standard_title,
    ev.title,
    ev.summary,
    ev.public_analysis,
    ev.location,
    ev.country,
    ev.display_country,
    ev.public_category_label,
    ev.event_subcategory,
    ev.event_category_label,
    ...(ev.event_signal_labels || []),
    ...(ev.actors || []),
    ...(getEventSources(ev).map(item=>`${item.name || ''} ${item.headline || ''}`))
  ].filter(Boolean).join(' ').toLowerCase();
  return hay.includes(needle);
}

function updateEventQueueSummary(evs){
  const highEl = document.getElementById('queue-high-salience');
  const countriesEl = document.getElementById('queue-countries');
  if(highEl){
    highEl.textContent = evs.filter(ev=>ev.salience === 'high').length;
  }
  if(countriesEl){
    const activeCountries = new Set();
    evs.forEach(ev=>{
      const profileCountries = getEventProfileCountries(ev);
      if(profileCountries.length){
        profileCountries.forEach(country=>activeCountries.add(country));
      } else {
        const label = getEventCountryLabel(ev);
        if(label && label !== 'Regional') activeCountries.add(label);
      }
    });
    countriesEl.textContent = activeCountries.size;
  }
}

function describeEventRange(range){
  if(range === '30d') return '30-day window';
  if(range === '90d') return '90-day window';
  return 'full archive';
}

function describeEventConfidence(conf){
  if(conf === 'green') return 'high-confidence reporting';
  if(conf === 'yellow') return 'medium-confidence reporting';
  if(conf === 'red') return 'low-confidence reporting';
  return '';
}

function updateEventFilterSummary(){
  const summaryEl=document.getElementById('events-filter-summary');
  const triggerBadge=document.getElementById('events-nav-trigger-badge');
  const railCount=document.getElementById('events-nav-rail-count');
  const railScope=document.getElementById('events-nav-rail-scope');
  const quickHigh=document.getElementById('events-nav-quick-high');
  const quickFocus=document.getElementById('events-nav-quick-focus');
  const dock=document.getElementById('events-nav-dock');
  const filterTrigger=document.getElementById('events-nav-trigger');
  const searchTrigger=document.getElementById('events-search-trigger');
  const domainLabel=document.getElementById('type-filter-select')?.selectedOptions?.[0]?.textContent?.trim() || 'All domains';
  const categoryLabel=document.getElementById('category-filter-select')?.selectedOptions?.[0]?.textContent?.trim() || 'All categories';
  const signalLabel=document.getElementById('signal-filter-select')?.selectedOptions?.[0]?.textContent?.trim() || 'All signals';
  const countryLabel=document.getElementById('country-filter-select')?.selectedOptions?.[0]?.textContent?.trim() || 'All tracked countries';
  const bits=[countryLabel, domainLabel, describeEventRange(filters.range)];
  const activeFilterCount = [
    filters.type !== 'all',
    filters.category !== 'all',
    filters.signal !== 'all',
    filters.country !== 'all',
    filters.conf !== 'all',
    filters.salience !== 'all',
    filters.range !== 'all'
  ].filter(Boolean).length;
  if(filters.category!=='all') bits.push(categoryLabel);
  if(filters.signal!=='all') bits.push(signalLabel);
  if(filters.salience!=='all') bits.push(`${filters.salience} salience`);
  const confLabel = describeEventConfidence(filters.conf);
  if(confLabel) bits.push(confLabel);
  if(summaryEl){
    summaryEl.textContent = bits.join(' · ');
  }
  if(triggerBadge){
    triggerBadge.hidden = activeFilterCount === 0;
    triggerBadge.textContent = String(activeFilterCount);
  }
  if(railCount) railCount.textContent = String(filtered.length || 0);
  if(railScope){
    const scopeBits = [];
    if(countryLabel !== 'All tracked countries') scopeBits.push(countryLabel);
    if(filters.range !== 'all') scopeBits.push(filters.range.toUpperCase());
    if(filters.salience === 'high') scopeBits.push('High');
    railScope.textContent = scopeBits.length ? scopeBits.join(' · ') : 'All countries';
  }
  const selectedCountryLabel = selected ? getEventCountryLabel(selected) : '';
  const shortcutCountry = (
    filters.country !== 'all' && filters.country !== 'regional'
      ? filters.country
      : (selectedCountryLabel && selectedCountryLabel !== 'Regional' ? selectedCountryLabel : '')
  );
  quickHigh?.classList.toggle('is-active', filters.salience === 'high');
  quickFocus?.classList.toggle('is-active', !!shortcutCountry && filters.country === shortcutCountry);
  quickFocus?.setAttribute('aria-disabled', shortcutCountry ? 'false' : 'true');
  filterTrigger?.classList.toggle('is-active', eventNavigatorMode === 'filters' && eventFilterPanelOpen);
  searchTrigger?.classList.toggle('is-active', !!(filters.search && String(filters.search).trim()) || (eventNavigatorMode === 'search' && eventFilterPanelOpen));
  if(dock) dock.toggleAttribute('data-active', !!eventFilterPanelOpen);
}

function setEventNavigatorOpen(open, mode='filters'){
  eventFilterPanelOpen = !!open;
  const dock=document.getElementById('events-nav-dock');
  const trigger=document.getElementById('events-nav-trigger');
  const searchTrigger=document.getElementById('events-search-trigger');
  const shell=document.querySelector('#events .events-shell');
  eventNavigatorMode = eventFilterPanelOpen ? (mode === 'search' ? 'search' : 'filters') : 'filters';
  dock?.classList.toggle('is-open', eventFilterPanelOpen);
  dock?.setAttribute('data-mode', eventNavigatorMode);
  trigger?.setAttribute('aria-expanded', eventFilterPanelOpen && eventNavigatorMode === 'filters' ? 'true' : 'false');
  searchTrigger?.setAttribute('aria-expanded', eventFilterPanelOpen && eventNavigatorMode === 'search' ? 'true' : 'false');
  shell?.classList.toggle('nav-open', eventFilterPanelOpen);
  if(eventFilterPanelOpen && eventNavigatorMode === 'search'){
    requestAnimationFrame(()=>{
      document.getElementById('event-search-input')?.focus();
      document.getElementById('event-search-input')?.select?.();
    });
  }
  updateEventFilterSummary();
}

function toggleEventNavigator(forceState, mode='filters'){
  const nextOpen = typeof forceState === 'boolean' ? forceState : !(eventFilterPanelOpen && eventNavigatorMode === mode);
  setEventNavigatorOpen(nextOpen, mode);
}

function openEventNavigator(mode){
  setEventNavigatorOpen(true, mode);
}

function clearEventFilters(){
  filters = { ...filters, type:'all', category:'all', signal:'all', country:'all', conf:'all', salience:'all', range:'all', search:'' };
  const typeSel=document.getElementById('type-filter-select');
  const categorySel=document.getElementById('category-filter-select');
  const signalSel=document.getElementById('signal-filter-select');
  const countrySel=document.getElementById('country-filter-select');
  const searchInput=document.getElementById('event-search-input');
  if(typeSel) typeSel.value='all';
  if(categorySel) categorySel.value='all';
  if(signalSel) signalSel.value='all';
  if(countrySel) countrySel.value='all';
  if(searchInput) searchInput.value='';
  syncEventFilterPicker('type');
  syncEventFilterPicker('category');
  syncEventFilterPicker('signal');
  syncEventFilterPicker('country');
  setActiveEventChips('event-range-chips','range',filters.range);
  setActiveEventChips('event-salience-chips','salience',filters.salience);
  setActiveEventChips('event-confidence-chips','conf',filters.conf);
  selected = null;
  setEventCountryOverlayOpen(false);
  renderEventCountryBrief(null);
  renderEventDetailEmpty();
  applyFilters('country');
}

globalThis.toggleEventNavigator = toggleEventNavigator;
globalThis.openEventNavigator = openEventNavigator;
globalThis.clearEventFilters = clearEventFilters;

function getOverallRiskMapStyle(country, fallbackColor = '#3a6ea5'){
  const summary = getCountryPredictiveSummary(country);
  const tone = getOverallRiskTone(summary?.overall_risk_score);
  const palette = {
    low: {
      color:'#2e4057',
      fillColor:'#2e4057',
      fillOpacity:0.08,
      opacity:0.82,
      weight:2.2
    },
    medium: {
      color:'#8a6e1f',
      fillColor:'#b8963e',
      fillOpacity:0.10,
      opacity:0.85,
      weight:2.3
    },
    high: {
      color:'#9c6e12',
      fillColor:'#b8963e',
      fillOpacity:0.14,
      opacity:0.9,
      weight:2.5
    },
    critical: {
      color:'#9a5730',
      fillColor:'#9a5730',
      fillOpacity:0.16,
      opacity:0.92,
      weight:2.7
    }
  };
  return palette[tone] || {
    color:fallbackColor,
    fillColor:fallbackColor,
    fillOpacity:0.10,
    opacity:0.85,
    weight:2.3
  };
}

function stableHash(value){
  const input = String(value || '');
  let hash = 0;
  for(let i=0;i<input.length;i+=1){
    hash = ((hash << 5) - hash) + input.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function normalizeText(value){
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'')
    .toLowerCase()
    .replace(/\s+/g,' ')
    .trim();
}

function tidyHeadline(text){
  return String(text || '')
    .replace(/^(reuters|associated press|ap|nyt world|bbc mundo|folha de s\.paulo|el tiempo colombia)\s*[:\-–]\s*/i,'')
    .replace(/\s*[|·]\s*(reuters|associated press|ap|nyt world|bbc mundo|folha de s\.paulo|el tiempo colombia)$/i,'')
    .replace(/\s+/g,' ')
    .trim();
}

function summaryToCanonicalTitle(summary){
  const cleaned=String(summary||'').replace(/\s+/g,' ').trim().replace(/[.;:]\s*$/,'');
  if(!cleaned) return '';
  const capped=cleaned.charAt(0).toUpperCase()+cleaned.slice(1);
  return capped.length>140 ? `${capped.slice(0,137).replace(/\s+\S*$/,'')}…` : capped;
}

function getEventActorNames(ev){
  const actors = ev.public_review?.actors || ev.actors || [];
  return [...new Set(actors.map(actor=>{
    if(typeof actor === 'string') return actor;
    return actor?.actor_canonical_name || actor?.actor_name || '';
  }).filter(Boolean))];
}

function buildCanonicalEventTitle(ev){
  const location = ev.location || ev.subnational_location || ev.display_country || getEventCountryLabel(ev);
  const actorNames = getEventActorNames(ev);
  const typeLabel = getEventTypeLabel(ev.type);
  if(actorNames.length){
    return `${typeLabel} involving ${actorNames[0]} in ${location}`;
  }
  return `${typeLabel} reported in ${location}`;
}

function getStandardizedEventTitle(ev){
  const sourceCount = (ev.sources?.length || ev.public_review?.linked_reports?.length || ev.public_review?.source_all?.length || 0);
  if(sourceCount > 1){
    const fromSummary = summaryToCanonicalTitle(ev.summary);
    if(fromSummary && fromSummary.length >= 48) return fromSummary;
    return buildCanonicalEventTitle(ev);
  }
  return tidyHeadline(ev.public_review?.headline || ev.title || ev.headline || 'Untitled event');
}

function getEventSources(ev){
  const linked=ev.public_review?.linked_reports || ev.linked_reports || [];
  if(linked.length){
    return linked.map((item, index)=>({
      name:item.source_name || ev.sources?.[index] || ev.source || 'Source',
      url:item.url || ev.links?.[index] || ev.url || null,
      role:item.report_role || (index===0 ? 'primary' : 'supporting'),
      headline:item.headline || null
    }));
  }
  const urls=ev.links?.length ? ev.links : (ev.url ? [ev.url] : []);
  const names=ev.sources?.length ? ev.sources : [ev.source || 'Source'];
  return names.map((name,index)=>({
    name,
    url:urls[index] || ev.url || null,
    role:index===0 ? 'primary' : 'supporting',
    headline:null
  }));
}

function getKnowledgeSignals(ev){
  const analyses=ev.council?.analyses || {};
  const traces=[analyses.cmr?.knowledge_trace, analyses.political_risk?.knowledge_trace, analyses.regional_security?.knowledge_trace, analyses.synthesis?.knowledge_trace].filter(Boolean);
  const raw = [];
  traces.forEach(trace=>{
    Object.values(trace).forEach(value=>{
      if(Array.isArray(value)) raw.push(...value);
    });
  });
  return [...new Set(raw.map(normalizeKnowledgeLabel).filter(Boolean))].slice(0,8);
}

function cleanSummaryText(text){
  const cleaned = String(text || '')
    .replace(/\s+/g,' ')
    .replace(/\s*;\s*/g,'. ')
    .trim();
  if(!cleaned) return '';
  return cleaned.endsWith('.') ? cleaned : `${cleaned}.`;
}

function getPublicEventDescription(ev){
  const summary = cleanSummaryText(ev.summary);
  if(summary) return summary;
  const title = tidyHeadline(ev.public_review?.headline || ev.title || ev.headline || '');
  if(title) return `${title}.`;
  return 'No public description is available yet for this event.';
}

function getPublicReportingSynthesis(ev){
  const lede = getPublicEventDescription(ev);
  const sources = getEventSources(ev);
  const sourceNames = [...new Set(sources.map(item=>item.name).filter(Boolean))];
  const sourceHeadlines = [...new Set(sources.map(item=>cleanSummaryText(item.headline || '')).filter(Boolean))];
  const actors = getEventActorNames(ev);
  const location = ev.location || ev.subnational_location || getEventCountryLabel(ev);
  const extended = [];

  if(sourceNames.length > 1){
    extended.push(`Cross-reporting currently converges across ${sourceNames.length} outlets: ${joinReadableList(sourceNames.slice(0,5))}.`);
  } else if(sourceNames.length === 1){
    extended.push(`The current public record is anchored in ${sourceNames[0]}.`);
  }

  if(sourceHeadlines.length){
    const relatedHeadlines = sourceHeadlines
      .filter(headline => normalizeText(headline) !== normalizeText(lede))
      .slice(0, 3);
    if(relatedHeadlines.length){
      extended.push(`Companion reporting frames the event through ${joinReadableList(relatedHeadlines.map(item=>`"${item}"`))}.`);
    }
  }

  if(actors.length){
    extended.push(`Named actors in the reporting include ${joinReadableList(actors.slice(0,4))}.`);
  }

  if(location){
    extended.push(`Reporting is centered on ${location}.`);
  }

  return {
    lede,
    extended: extended.filter(Boolean),
  };
}

function getPublicEventContext(ev){
  const salience = String(ev.salience || '').toLowerCase();
  const sources = getEventSources(ev);
  const sourceNames = [...new Set(sources.map(item=>item.name).filter(Boolean))];
  const actors = getEventActorNames(ev);
  const classification = ev.council?.analyses?.synthesis?.classification || {};
  const deedType = String(classification.deed_type || ev.public_review?.deed_type || ev.deed_type || '').trim().toLowerCase();
  const country = ev.display_country || getEventCountryLabel(ev);
  const location = ev.location || ev.subnational_location || country;
  const frame = normalizeKnowledgeLabel(classification.primary_frame || '');
  const effect = normalizeKnowledgeLabel(classification.effect_domain || '');
  const deedLine = deedType
    ? `This event is also classified as ${normalizeKnowledgeLabel(deedType)} within the project's institutional-erosion framework.`
    : '';

  if(salience === 'high'){
    const sourceText = sourceNames.length
      ? (sourceNames.length === 1
          ? `Current reporting is anchored in ${sourceNames[0]}.`
          : `Current reporting draws on ${joinReadableList(sourceNames)}.`)
      : '';
    const actorText = actors.length
      ? `The event currently centers on ${joinReadableList(actors.slice(0,2))}${actors.length>2 ? ', among other actors' : ''}.`
      : '';
    const frameText = frame || effect
      ? `In analytical terms, it sits in the frame of ${frame || 'security politics'}${effect ? ` and points most directly to ${effect.toLowerCase()}` : ''}.`
      : '';
    return [sourceText, actorText, frameText, deedLine].filter(Boolean).join(' ');
  }

  if(salience === 'medium'){
    const bits = [];
    if(sourceNames.length > 1){
      bits.push(`The event is corroborated across ${sourceNames.length} sources.`);
    }
    if(actors.length){
      bits.push(`The main actors currently visible in the reporting are ${joinReadableList(actors.slice(0,2))}.`);
    }
    if(location && location !== country){
      bits.push(`The reporting is centered on ${location}.`);
    }
    if(deedLine){
      bits.push(deedLine);
    }
    return bits.join(' ');
  }

  return deedLine;
}

function cleanCouncilAssessment(text){
  return String(text || '')
    .replace(/^AI-generated\s+[A-Za-z-]+\s+analysis:\s*/i,'')
    .replace(/^AI-generated synthesis:\s*/i,'')
    .replace(/\s*Primary priorities:.*$/i,'')
    .replace(/\s*Primary synthesis priorities:.*$/i,'')
    .replace(/\s*Role domains in view:.*$/i,'')
    .replace(/\s*Relationship cues:.*$/i,'')
    .replace(/\s*Interaction cues:.*$/i,'')
    .replace(/\s*Key project concepts in play include.*$/i,'')
    .replace(/\s+/g,' ')
    .trim();
}

function isGenericCouncilText(text){
  const cleaned = String(text || '').trim();
  if(!cleaned) return true;
  return /AI-generated synthesis:|Primary synthesis priorities:|Key project concepts in play include|Role domains in view:|Relationship cues:|Interaction cues:/i.test(cleaned);
}

function humanizeConceptSignal(value){
  const normalized = String(value || '').trim().toLowerCase();
  const map = {
    public_security:'military role in public security',
    political_influence:'military influence over politics',
    governance_tasks:'military involvement in governance tasks',
    external_defense:'external defense posture',
    internal_security:'internal security role',
    organized_crime:'organized crime pressure',
    illicit_networks:'illicit network activity',
    cross_border_spillover:'cross-border spillover',
    subordinate:'civilian subordination',
    tutelary_veto:'tutelary military influence'
  };
  return map[normalized] || normalizeKnowledgeLabel(value).toLowerCase();
}

function joinReadableList(items){
  const arr = items.filter(Boolean);
  if(!arr.length) return '';
  if(arr.length===1) return arr[0];
  if(arr.length===2) return `${arr[0]} and ${arr[1]}`;
  return `${arr.slice(0,-1).join(', ')}, and ${arr[arr.length-1]}`;
}

function getPublicEventAnalysisParts(ev){
  const analyses = ev.council?.analyses || {};
  const synthesis = analyses.synthesis || {};
  const takeaways = synthesis.public_takeaways || {};
  const significance = cleanCouncilAssessment(takeaways.significance || '');
  const countryEffect = cleanCouncilAssessment(takeaways.country_effect || '');
  const patternFit = cleanCouncilAssessment(takeaways.pattern_fit || '');
  const mechanism = cleanCouncilAssessment(takeaways.mechanism || '');
  const institutionalImplication = cleanCouncilAssessment(takeaways.institutional_implication || '');
  const forwardRisk = cleanCouncilAssessment(takeaways.forward_risk || '');
  const confidenceNote = cleanCouncilAssessment(takeaways.confidence_note || '');
  const watchpoint = cleanCouncilAssessment(takeaways.watchpoint || '');
  if(significance || countryEffect || patternFit || mechanism || institutionalImplication || forwardRisk || watchpoint){
    return { significance, countryEffect, patternFit, mechanism, institutionalImplication, forwardRisk, confidenceNote, watchpoint };
  }

  const cleanedSynthesis = cleanCouncilAssessment(synthesis.assessment || '');
  if(cleanedSynthesis && !isGenericCouncilText(synthesis.assessment || '')){
    const bits = cleanedSynthesis.split(/(?<=\.)\s+/).filter(Boolean);
    return {
      significance: bits[0] || '',
      countryEffect: bits[1] || '',
      patternFit: '',
      mechanism: '',
      institutionalImplication: '',
      forwardRisk: '',
      confidenceNote: '',
      watchpoint: bits.slice(2).join(' ')
    };
  }

  const conceptSignals = getKnowledgeSignals(ev).slice(0,3).map(humanizeConceptSignal);
  const countryLabel = ev.display_country || getEventCountryLabel(ev);
  const typeLabel = getEventTypeLabel(ev.type).toLowerCase();
  return {
    significance: `This ${typeLabel} event is relevant for ${countryLabel} because it touches the broader balance between political authority, security institutions, and public order.`,
    countryEffect: conceptSignals.length ? `The main analytical themes are ${joinReadableList(conceptSignals)}.` : '',
    patternFit: '',
    mechanism: '',
    institutionalImplication: '',
    forwardRisk: '',
    confidenceNote: '',
    watchpoint: 'The key question is whether follow-on reporting shows this to be isolated or part of a broader pattern.'
  };
}

function getRenderablePublicAnalysis(ev){
  const salience = String(ev.salience || '').toLowerCase();
  const raw = getPublicEventAnalysisParts(ev);
  const ordered = [
    ['significance', 'Immediate significance'],
    ['countryEffect', 'Country-level effect'],
    ['patternFit', 'Pattern fit'],
    ['mechanism', 'Mechanism'],
    ['institutionalImplication', 'Institutional implication'],
    ['forwardRisk', 'Forward risk'],
    ['confidenceNote', 'Interpretive note'],
    ['watchpoint', 'What to watch'],
  ];

  let allowed;
  if(salience === 'high'){
    allowed = new Set(ordered.map(([key]) => key));
  } else if(salience === 'medium'){
    allowed = new Set(['significance','countryEffect','patternFit','mechanism','forwardRisk','confidenceNote','watchpoint']);
  } else {
    allowed = new Set(['significance','countryEffect','confidenceNote','watchpoint']);
  }

  const blocks = ordered
    .filter(([key]) => allowed.has(key))
    .map(([key, label]) => ({ key, label, value: String(raw[key] || '').trim() }))
    .filter(item => item.value);

  const deduped = [];
  const seen = new Set();
  for(const block of blocks){
    const normalized = block.value.toLowerCase();
    if(seen.has(normalized)) continue;
    seen.add(normalized);
    deduped.push(block);
  }

  if(salience !== 'high' && deduped.length > 5){
    return deduped.slice(0, 5);
  }
  return deduped;
}

function getPublicClassificationChips(ev){
  const chips = [];
  const subtype = ev.public_review?.event_subtype || ev.subtype;
  const classification = ev.council?.analyses?.synthesis?.classification || {};
  const deedType = classification.deed_type || ev.public_review?.deed_type || ev.deed_type;
  if(classification.primary_frame) chips.push(classification.primary_frame);
  if(classification.effect_domain) chips.push(classification.effect_domain);
  if(deedType) chips.push(deedType);
  if(subtype) chips.push(subtype);
  getKnowledgeSignals(ev).slice(0,3).forEach(signal=>chips.push(signal));
  return [...new Set(chips)];
}

function getPublicClassificationRows(ev){
  const actors = getEventActorNames(ev);
  const classification = ev.council?.analyses?.synthesis?.classification || {};
  const deedType = classification.deed_type || ev.public_review?.deed_type || ev.deed_type;
  const eventMeta = eventTypeMeta.get(String(ev.type)) || {};
  const lenses = getEventAnalystLenses(ev);
  const signalLabels = getEventSignalLabels(ev);
  const rows = [
    { label:'Domain', value:getEventDomainLabel(ev.event_type_domain || ev.event_category || eventMeta.event_category) },
    { label:'Category', value:getPublicCategoryLabel(ev) },
    { label:'Family', value:getEventFamilyLabel(ev) },
    { label:'Signal', value:signalLabels.length ? signalLabels.join(' · ') : '' },
    { label:'Subcategory', value:getEventSubcategoryLabel(ev.event_subcategory || ev.public_review?.event_subtype || ev.subtype) },
    { label:'Active lenses', value:lenses.length ? lenses.map(item=>item.label).join(' · ') : '' },
    { label:'Institutional signal', value:deedType ? normalizeKnowledgeLabel(deedType) : '' },
    { label:'Analytical frame', value:normalizeKnowledgeLabel(classification.primary_frame || eventMeta.description || 'General security monitoring') },
    { label:'Likely effect', value:normalizeKnowledgeLabel(classification.effect_domain || 'Security-sector positioning') },
    { label:'Main actors', value:actors.length ? actors.join(' · ') : '' },
    { label:'Confidence', value:ev.conf==='green'?'High-confidence reporting':ev.conf==='yellow'?'Medium-confidence reporting':'Low-confidence reporting' },
  ];
  return rows.filter(item => {
    const value = String(item.value || '').trim();
    if(!value) return false;
    return !['Not specified','Not identified','General monitoring'].includes(value);
  });
}

function splitClassificationRows(rows){
  const priority = ['Domain','Category','Signal','Subcategory','Likely effect','Main actors','Active lenses','Institutional signal'];
  const visible = [];
  const hidden = [];
  priority.forEach(label=>{
    const match = rows.find(item=>item.label === label);
    if(match && !visible.includes(match)) visible.push(match);
  });
  rows.forEach(item=>{
    if(!visible.includes(item)) hidden.push(item);
  });
  return {
    visible: visible.slice(0,4),
    hidden: [...visible.slice(4), ...hidden]
  };
}

function getPublicProvenanceSummary(ev, linkedReports, timeline){
  const summary = ev.public_review?.provenance_summary || {};
  const items = [];
  if(typeof summary.article_link_count === 'number'){
    items.push({ label:'Linked reports', value:String(summary.article_link_count) });
  } else if(linkedReports.length){
    items.push({ label:'Linked reports', value:String(linkedReports.length) });
  }
  if(summary.source_type){
    items.push({ label:'Source base', value:normalizeKnowledgeLabel(summary.source_type) });
  }
  if(summary.latest_stage){
    items.push({ label:'Current stage', value:normalizeKnowledgeLabel(summary.latest_stage) });
  }
  return items;
}

function getPublicTransparencyText(ev, linkedReports){
  const parts = [];
  if(linkedReports.length){
    parts.push(`Compiled from ${linkedReports.length} report${linkedReports.length===1?'':'s'}`);
  }
  if(ev.public_review?.reviewed_by_human || ev.public_review?.human_validated){
    parts.push(ev.public_review?.human_validated ? 'Human validated' : 'Human reviewed');
  }
  if(ev.council?.analyses?.synthesis?.ai_generated){
    parts.push('AI-assisted interpretation');
  }
  const sourceType = ev.public_review?.provenance_summary?.source_type;
  if(sourceType){
    parts.push(`Source base: ${normalizeKnowledgeLabel(sourceType)}`);
  }
  return parts.join(' · ');
}

function applyFilters(zoomTrigger){
  if(selected && !allEvents.some(ev=>ev.id === selected.id)){
    selected = null;
  }
  filtered=allEvents.filter(ev=>{
    const eventTypeDomain = ev.event_type_domain || ev.event_category;
    if(filters.type!=='all'&&eventTypeDomain!==filters.type)return false;
    if(filters.category!=='all'&&String(ev.public_category_key || '')!==filters.category)return false;
    if(filters.signal!=='all'&&!((ev.event_signal_families || []).includes(filters.signal)))return false;
    if(filters.conf!=='all'&&String(ev.conf||'')!==filters.conf)return false;
    if(filters.salience!=='all'&&String(ev.salience||'')!==filters.salience)return false;
    if(!matchesDateRange(ev, filters.range)) return false;
    const eventCountries=getEventProfileCountries(ev);
    const eventCountry=getEventCountryLabel(ev);
    if(filters.country==='regional'&&eventCountry!=='Regional')return false;
    if(filters.country!=='all'&&filters.country!=='regional'&&!(eventCountries.includes(filters.country) || eventCountry===filters.country))return false;
    if(!matchesEventSearch(ev, filters.search)) return false;
    return true;
  }).sort((a,b)=>b.date.localeCompare(a.date));
  if(selected && !filtered.some(ev=>ev.id === selected.id)){
    selected = null;
    setEventCountryOverlayOpen(false);
    renderEventCountryBrief(null);
    renderEventDetailEmpty();
  } else if(!selected){
    setEventCountryOverlayOpen(false);
    renderEventCountryBrief(null);
  }
  const mapCountryFocus = selected
    ? selected
    : (filters.country !== 'all' && filters.country !== 'regional'
      ? { country: filters.country, display_country: filters.country }
      : null);
  renderEventCountryBrief(mapCountryFocus);
  renderList(); refreshMap(filtered);
  const eventCountEl = document.getElementById('event-count');
  if(eventCountEl) eventCountEl.textContent = String(filtered.length);
  updateEventQueueSummary(filtered);
  updateEventFilterSummary();
}

function setActiveEventChips(groupId, attrName, value){
  document.querySelectorAll(`#${groupId} [data-${attrName}]`).forEach(btn=>{
    btn.classList.toggle('active', btn.dataset[attrName] === value);
  });
}

function initEventFilterControls(){
  const typeSel=document.getElementById('type-filter-select');
  const categorySel=document.getElementById('category-filter-select');
  const signalSel=document.getElementById('signal-filter-select');
  const countrySel=document.getElementById('country-filter-select');
  const searchInput=document.getElementById('event-search-input');
  const typePickerTrigger=document.getElementById('type-filter-picker-trigger');
  const categoryPickerTrigger=document.getElementById('category-filter-picker-trigger');
  const signalPickerTrigger=document.getElementById('signal-filter-picker-trigger');
  const countryPickerTrigger=document.getElementById('country-filter-picker-trigger');
  const navResetBtn=document.getElementById('events-nav-reset-btn');
  const navCloseBtn=document.getElementById('events-nav-close-btn');
  const searchTrigger=document.getElementById('events-search-trigger');
  const searchClearBtn=document.getElementById('events-search-clear-btn');
  const searchCloseBtn=document.getElementById('events-search-close-btn');
  const quickHighBtn=document.getElementById('events-nav-quick-high');
  const quickFocusBtn=document.getElementById('events-nav-quick-focus');
  const quickResetBtn=document.getElementById('events-nav-quick-reset');
  const navDock=document.getElementById('events-nav-dock');
  const navTrigger=document.getElementById('events-nav-trigger');
  const navBackdrop=document.getElementById('events-nav-backdrop');
  if(!typeSel || !categorySel || !signalSel || !countrySel || !searchInput) return;
  navTrigger?.addEventListener('click',()=>toggleEventNavigator(undefined, 'filters'));
  searchTrigger?.addEventListener('click',()=>toggleEventNavigator(undefined, 'search'));
  navBackdrop?.addEventListener('click',()=>setEventNavigatorOpen(false, eventNavigatorMode));
  document.addEventListener('keydown',(event)=>{
    if(event.key === 'Escape' && eventFilterPanelOpen){
      closeEventFilterPickers();
      setEventNavigatorOpen(false, eventNavigatorMode);
    }
  });
  document.addEventListener('click',(event)=>{
    if(!(event.target instanceof Element)) return;
    if(!event.target.closest('.events-picker')) closeEventFilterPickers();
    if(!eventFilterPanelOpen || !navDock) return;
    if(navDock.contains(event.target)) return;
    setEventNavigatorOpen(false, eventNavigatorMode);
  });
  typePickerTrigger?.addEventListener('click',()=>{
    const picker=document.getElementById('type-filter-picker');
    const nextOpen=!picker?.classList.contains('is-open');
    closeEventFilterPickers();
    picker?.classList.toggle('is-open', nextOpen);
    typePickerTrigger.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  });
  categoryPickerTrigger?.addEventListener('click',()=>{
    const picker=document.getElementById('category-filter-picker');
    const nextOpen=!picker?.classList.contains('is-open');
    closeEventFilterPickers();
    picker?.classList.toggle('is-open', nextOpen);
    categoryPickerTrigger.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  });
  signalPickerTrigger?.addEventListener('click',()=>{
    const picker=document.getElementById('signal-filter-picker');
    const nextOpen=!picker?.classList.contains('is-open');
    closeEventFilterPickers();
    picker?.classList.toggle('is-open', nextOpen);
    signalPickerTrigger.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  });
  countryPickerTrigger?.addEventListener('click',()=>{
    const picker=document.getElementById('country-filter-picker');
    const nextOpen=!picker?.classList.contains('is-open');
    closeEventFilterPickers();
    picker?.classList.toggle('is-open', nextOpen);
    countryPickerTrigger.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  });
  navResetBtn?.addEventListener('click',()=>clearEventFilters());
  navCloseBtn?.addEventListener('click',()=>setEventNavigatorOpen(false, 'filters'));
  searchClearBtn?.addEventListener('click',()=>{
    filters.search='';
    searchInput.value='';
    applyFilters();
    searchInput.focus();
  });
  searchCloseBtn?.addEventListener('click',()=>setEventNavigatorOpen(false, 'search'));
  quickHighBtn?.addEventListener('click',()=>{
    filters.salience = filters.salience === 'high' ? 'all' : 'high';
    setActiveEventChips('event-salience-chips','salience',filters.salience);
    applyFilters();
  });
  quickFocusBtn?.addEventListener('click',()=>{
    const selectedCountry = selected ? getEventCountryLabel(selected) : '';
    const nextCountry = (selectedCountry && selectedCountry !== 'Regional')
      ? selectedCountry
      : (filters.country !== 'all' && filters.country !== 'regional' ? filters.country : '');
    if(!nextCountry) return;
    filters.country = nextCountry;
    if(countrySel) countrySel.value = nextCountry;
    applyFilters('country');
  });
  quickResetBtn?.addEventListener('click',()=>clearEventFilters());
  typeSel.addEventListener('change',()=>{
    syncEventFilterPicker('type');
    filters.type=typeSel.value;
    applyFilters();
  });
  categorySel.addEventListener('change',()=>{
    syncEventFilterPicker('category');
    filters.category=categorySel.value;
    applyFilters();
  });
  signalSel.addEventListener('change',()=>{
    syncEventFilterPicker('signal');
    filters.signal=signalSel.value;
    applyFilters();
  });
  countrySel.addEventListener('change',()=>{
    syncEventFilterPicker('country');
    filters.country=countrySel.value;
    applyFilters('country');
  });
  searchInput.addEventListener('input',()=>{
    filters.search=searchInput.value;
    applyFilters();
  });
  document.querySelectorAll('#event-range-chips [data-range]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      filters.range=btn.dataset.range || '30d';
      setActiveEventChips('event-range-chips','range',filters.range);
      applyFilters();
    });
  });
  document.querySelectorAll('#event-salience-chips [data-salience]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      filters.salience=btn.dataset.salience || 'all';
      setActiveEventChips('event-salience-chips','salience',filters.salience);
      applyFilters();
    });
  });
  document.querySelectorAll('#event-confidence-chips [data-conf]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      filters.conf=btn.dataset.conf || 'all';
      setActiveEventChips('event-confidence-chips','conf',filters.conf);
      applyFilters();
    });
  });
  setActiveEventChips('event-range-chips','range',filters.range);
  setActiveEventChips('event-salience-chips','salience',filters.salience);
  setActiveEventChips('event-confidence-chips','conf',filters.conf);
  updateEventFilterSummary();
}

function sentenceCaseDate(value){
  if(!value) return '—';
  const d = new Date(value);
  if(Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('en-US',{month:'short', day:'numeric'});
}

function firstSentence(text){
  if(!text) return '';
  const clean = String(text).replace(/\s+/g,' ').trim();
  const match = clean.match(/(.+?[.!?])(\s|$)/);
  return (match ? match[1] : clean).trim();
}

function getEventListPreview(ev){
  return firstSentence(
    ev.summary ||
    ev.public_analysis ||
    ev.ai_analysis ||
    ev.public_review?.headline ||
    ''
  );
}

function getEventMechanismLabel(ev){
  const parts = [];
  if(ev.event_type_domain || ev.event_category) parts.push(getEventDomainLabel(ev.event_type_domain || ev.event_category));
  if(ev.public_category_key) parts.push(getPublicCategoryLabel(ev));
  const signalLabels = getEventSignalLabels(ev);
  if(signalLabels.length) parts.push(signalLabels[0]);
  return parts.slice(0,3).join(' · ');
}

function getEventAccordionIds(ev){
  const base = String(ev?.sentinel_id || ev?.id || 'event')
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '') || 'event';
  return {
    triggerId: `event-trigger-${base}`,
    panelId: `event-panel-${base}`
  };
}

function buildEventAccordionDetail(ev){
  const linkedReports = getEventSources(ev);
  const reportingSynthesis = getPublicReportingSynthesis(ev);
  const publicContext = getPublicEventContext(ev);
  const analysisBlocks = getRenderablePublicAnalysis(ev);
  const fallbackAssessment = cleanCouncilAssessment(ev.public_analysis || '');
  const assessment = analysisBlocks[0]?.value || (!isGenericCouncilText(fallbackAssessment) ? fallbackAssessment : '') || publicContext;
  const signalLabels = getEventSignalLabels(ev);
  const chips = getPublicClassificationChips(ev).slice(0, 5);
  const metaRows = [
    ['Country', getEventCountryLabel(ev)],
    ['Location', ev.location || ev.country || 'Location pending'],
    ['Date', sentenceCaseDate(ev.date)],
    ['Signal', signalLabels[0] || getEventFamilyLabel(ev)],
    ['Domain', getEventDomainLabel(ev.event_type_domain || ev.event_category)],
    ['Coverage', `${linkedReports.length} source${linkedReports.length === 1 ? '' : 's'}`]
  ];
  const sourceMarkup = linkedReports.length
    ? linkedReports.slice(0, 4).map(item => {
        const safeUrl = sanitizeExternalUrl(item.url);
        if(safeUrl){
          return `<a class="ev-inline-source" href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.name || 'Source')}</a>`;
        }
        return `<span class="ev-inline-source is-muted">${escapeHtml(item.name || 'Source')}</span>`;
      }).join('')
    : '<span class="ev-inline-source is-muted">Source pending</span>';
  return `
    <div class="ev-inline-grid">
      <div class="ev-inline-brief">
        <span class="ev-inline-label">Field brief</span>
        <div class="ev-inline-summary">${escapeHtml(reportingSynthesis.lede)}</div>
        ${publicContext ? `<div class="ev-inline-assessment"><strong>Why it matters:</strong> ${escapeHtml(publicContext)}</div>` : ''}
        ${assessment && assessment !== publicContext ? `<div class="ev-inline-assessment"><strong>Assessment:</strong> ${escapeHtml(assessment)}</div>` : ''}
      </div>
      <div class="ev-inline-meta">
        <div class="ev-inline-card">
          <span class="ev-inline-label">Operational metadata</span>
          <div class="ev-inline-data">
            ${metaRows.map(([label, value]) => `
              <div class="ev-inline-kv">
                <span class="ev-inline-kv-label">${escapeHtml(label)}</span>
                <span class="ev-inline-kv-value">${escapeHtml(String(value || '—'))}</span>
              </div>`).join('')}
          </div>
        </div>
        ${chips.length ? `
          <div class="ev-inline-card">
            <span class="ev-inline-label">Analytical cues</span>
            <div class="ev-inline-chip-row">${chips.map(item => `<span class="ev-inline-chip">${escapeHtml(item)}</span>`).join('')}</div>
          </div>` : ''}
        <div class="ev-inline-card">
          <span class="ev-inline-label">Source base</span>
          <div class="ev-inline-source-list">${sourceMarkup}</div>
        </div>
      </div>
    </div>`;
}


// ── LIST ────────────────────────────────────────────────────
function renderList(){
  const el=document.getElementById('event-list');
  if(!filtered.length){ el.innerHTML='<div style="padding:20px 16px;color:var(--text-muted);font-family:var(--mono);font-size:9.5px;">No events match filters.</div>'; return; }
  el.innerHTML='';
  filtered.forEach(ev=>{
    const c=TC_HEX[ev.type]||'#6a6560';
    const humanValidated = !!ev.public_review?.human_validated;
    const reviewedByHuman = !!ev.public_review?.reviewed_by_human;
    const sourceCount=getEventSources(ev).length;
    const isSelected = selected?.id===ev.id;
    const div=document.createElement('div');
    div.setAttribute('role', 'listitem');
    div.className=`ev-item${isSelected?' selected':''}`;
    const mechanism = getEventMechanismLabel(ev);
    const countryTags = getEventCountryTags(ev);
    const sourceLabel = ev.source || getEventSources(ev)[0]?.name || 'Source pending';
    div.innerHTML=`
      <div class="ev-row1">
        <div class="ev-dot" style="background:${c}"></div>
        <span class="ev-type" style="color:${c}">${getEventTypeLabel(ev.type)}</span>
        ${humanValidated?`<span class="src-badge tri" title="Validated by a human analyst">Human Validated</span>`:reviewedByHuman?`<span class="src-badge single" title="Reviewed by a human analyst">Human Reviewed</span>`:''}
        <span class="ev-country-tags">${countryTags.map(renderCountryTagHtml).join('')}</span>
      </div>
      <div class="ev-title">${escapeHtml(ev.standard_title || getStandardizedEventTitle(ev))}</div>
      ${mechanism?`<div class="ev-kicker">${escapeHtml(mechanism)}</div>`:''}
      <div class="ev-row1-bottom">
        <div class="ev-meta"><span>${escapeHtml(sentenceCaseDate(ev.date))}</span><span>${sourceCount} source${sourceCount===1?'':'s'}</span><span>${escapeHtml(sourceLabel)}</span></div>
      </div>`;
    div.onclick=()=>selectEvent(ev);
    el.appendChild(div);
  });
}

function initFeedbackPickers(){
  const categorySelect=document.getElementById('fb-category');
  const countrySelect=document.getElementById('fb-country');
  const categoryTrigger=document.getElementById('fb-category-picker-trigger');
  const countryTrigger=document.getElementById('fb-country-picker-trigger');
  if(!categorySelect || !countrySelect) return;

  const togglePicker=(pickerId, trigger)=>{
    const picker=document.getElementById(pickerId);
    const nextOpen=!picker?.classList.contains('is-open');
    closeEventFilterPickers();
    picker?.classList.toggle('is-open', nextOpen);
    trigger?.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  };

  categoryTrigger?.addEventListener('click',()=>togglePicker('fb-category-picker', categoryTrigger));
  countryTrigger?.addEventListener('click',()=>togglePicker('fb-country-picker', countryTrigger));

  categorySelect.addEventListener('change',()=>syncFeedbackPicker('category'));
  countrySelect.addEventListener('change',()=>syncFeedbackPicker('country'));

  syncFeedbackPicker('category');
  syncFeedbackPicker('country');
}

function renderEventDetailEmpty(){
  const detailEl = document.getElementById('detail');
  if(!detailEl) return;
  detailEl.innerHTML = `
    <div class="detail-empty">
      <div class="detail-empty-glyph">⊕</div>
      <div class="detail-empty-text">Select an event</div>
    </div>
  `;
}

function getEventCountryFocus(ev){
  const countryLabel = ev?.display_country || getEventCountryLabel(ev);
  const monitorCountry = ev?.country || countryLabel;
  const predictiveSummary = getCountryPredictiveSummary(monitorCountry);
  const overallRisk = predictiveSummary?.overall_risk_score;
  const overallRiskTone = getOverallRiskTone(overallRisk);
  const leadingConstructMeta = getLeadingConstructMeta(monitorCountry);
  const regimeConstruct = getCountryRiskConstruct(monitorCountry, 'regime_vulnerability');
  const militarizationConstruct = getCountryRiskConstruct(monitorCountry, 'militarization');
  const fragmentationConstruct = getCountryRiskConstruct(monitorCountry, 'security_fragmentation');
  const watchpoints = Array.isArray(predictiveSummary?.watchpoints) ? predictiveSummary.watchpoints.slice(0,2) : [];
  const countryTags = ev ? getEventCountryTags(ev) : [];
  const primaryProfileCountry = countryTags.find(item=>item.isProfile)?.label || '';
  return {
    countryLabel,
    monitorCountry,
    predictiveSummary,
    overallRisk,
    overallRiskTone,
    leadingConstructMeta,
    regimeConstruct,
    militarizationConstruct,
    fragmentationConstruct,
    watchpoints,
    countryTags,
    primaryProfileCountry
  };
}

function setEventCountryOverlayOpen(open){
  eventCountryOverlayOpen = !!open;
  const overlay = document.getElementById('map-country-brief');
  if(!overlay) return;
  if(eventCountryOverlayOpen){
    overlay.hidden = false;
    overlay.classList.add('is-open');
  } else {
    overlay.classList.remove('is-open');
    overlay.hidden = true;
  }
}

function toggleEventCountryOverlay(forceState){
  setEventCountryOverlayOpen(typeof forceState === 'boolean' ? forceState : !eventCountryOverlayOpen);
  if(selected) renderEventCountryBrief(selected);
}

function renderEventCountryBrief(ev){
  const strip = document.getElementById('events-country-strip');
  const overlay = document.getElementById('map-country-brief');
  const toolbar = document.getElementById('events-toolbar');
  if(!strip || !overlay) return;
  if(!ev){
    if(toolbar) toolbar.hidden = true;
    strip.hidden = true;
    strip.classList.remove('is-visible');
    overlay.hidden = true;
    overlay.classList.remove('is-open');
    overlay.innerHTML = '';
    return;
  }
  const focus = getEventCountryFocus(ev);
  const countryEventCount = (filtered || allEvents || []).filter(item=>{
    const profileCountries = getEventProfileCountries(item);
    const itemCountry = getEventCountryLabel(item);
    return profileCountries.includes(focus.countryLabel) || itemCountry === focus.countryLabel;
  }).length;
  if(!focus.countryLabel || focus.countryLabel === 'Regional'){
    if(toolbar) toolbar.hidden = true;
    strip.hidden = true;
    strip.classList.remove('is-visible');
    overlay.hidden = true;
    overlay.classList.remove('is-open');
    overlay.innerHTML = '';
    return;
  }
  if(toolbar) toolbar.hidden = false;
  const indexes = [
    {
      label:'Overall risk',
      value:formatMonitorValue(focus.overallRisk) ?? '—',
      note:focus.predictiveSummary?.overall_risk_level || 'active'
    },
    {
      label:'Regime',
      value:formatMonitorValue(focus.regimeConstruct?.score) ?? '—',
      note:focus.regimeConstruct?.trend_label || 'vulnerability'
    },
    {
      label:'Militarization',
      value:formatMonitorValue(focus.militarizationConstruct?.score) ?? '—',
      note:focus.militarizationConstruct?.trend_label || 'current'
    },
    {
      label:'Fragmentation',
      value:formatMonitorValue(focus.fragmentationConstruct?.score) ?? '—',
      note:focus.fragmentationConstruct?.trend_label || 'security'
    }
  ];
  strip.hidden = false;
  strip.classList.add('is-visible');
  strip.innerHTML = `
    <div class="events-country-strip-utility">
      <span class="events-country-strip-kicker">Country focus</span>
      <button class="events-country-brief-btn secondary" type="button" onclick="resetEventCountryFocus()">Reset view</button>
    </div>
    <div class="events-country-strip-main">
      <button class="events-country-strip-title-btn ${eventCountryOverlayOpen ? 'is-open' : ''}" type="button" onclick="toggleEventCountryOverlay()" aria-expanded="${eventCountryOverlayOpen ? 'true' : 'false'}" aria-controls="map-country-brief">
        <span class="events-country-strip-title">${escapeHtml(focus.countryLabel)}</span>
        <span class="events-country-strip-title-hint">${eventCountryOverlayOpen ? 'Hide country brief' : 'Open country brief'}</span>
      </button>
    </div>
    <div class="events-country-strip-indexes">
      ${indexes.map(item=>`
        <div class="events-country-index">
          <span class="events-country-index-label">${item.label}</span>
          <span class="events-country-index-value">${item.value}</span>
          <span class="events-country-index-note">${item.note}</span>
        </div>`).join('')}
    </div>
  `;
  overlay.innerHTML = `
    <div class="map-country-brief-card">
      <div class="map-country-brief-head">
        <div>
          <div class="events-country-strip-kicker">Selected country</div>
          <div class="map-country-brief-title">${escapeHtml(focus.countryLabel)}</div>
        </div>
        <button class="map-country-brief-close" type="button" onclick="toggleEventCountryOverlay(false)">Close</button>
      </div>
      ${focus.predictiveSummary?.summary_text ? `<div class="map-country-brief-copy">${escapeHtml(focus.predictiveSummary.summary_text)}</div>` : ''}
      <div class="map-country-brief-grid">
        <div class="map-country-brief-cell">
          <label>Leading pressure</label>
          <span style="color:${focus.leadingConstructMeta?.color || 'var(--slate)'};">${escapeHtml(focus.leadingConstructMeta?.short || '—')}</span>
          <small>${escapeHtml(focus.leadingConstructMeta?.label || 'not identified')}</small>
        </div>
        <div class="map-country-brief-cell">
          <label>Trend</label>
          <span style="color:${getMonitorTrendColor(focus.leadingConstructMeta?.trend)};">${escapeHtml(String(focus.predictiveSummary?.leading_trend || focus.leadingConstructMeta?.trend || 'stable').toUpperCase())}</span>
          <small>${escapeHtml(focus.predictiveSummary?.leading_construct || 'monitor direction')}</small>
        </div>
        <div class="map-country-brief-cell">
          <label>Event field</label>
          <span>${countryEventCount}</span>
          <small>currently visible public events tied to ${escapeHtml(focus.countryLabel)}</small>
        </div>
      </div>
      ${focus.watchpoints.length ? `
        <div class="map-country-brief-watch">
          <label>Watch next</label>
          <ul>${focus.watchpoints.map(point=>`<li>${escapeHtml(point)}</li>`).join('')}</ul>
        </div>` : ''}
    </div>
  `;
  setEventCountryOverlayOpen(eventCountryOverlayOpen);
}

function resetEventCountryFocus(){
  selected = null;
  filters.country = 'all';
  const countrySel = document.getElementById('country-filter-select');
  if(countrySel) countrySel.value = 'all';
  setEventCountryOverlayOpen(false);
  renderEventDetailEmpty();
  applyFilters('country');
}

globalThis.resetEventCountryFocus = resetEventCountryFocus;

globalThis.toggleEventCountryOverlay = toggleEventCountryOverlay;

function sortProvenanceTimeline(timeline){
  return [...(timeline||[])].sort((a,b)=>{
    const aStage = PROVENANCE_STAGE_ORDER[String(a?.stage||'')] ?? 999;
    const bStage = PROVENANCE_STAGE_ORDER[String(b?.stage||'')] ?? 999;
    if(aStage !== bStage) return aStage - bStage;
    return String(a?.at||'').localeCompare(String(b?.at||''));
  });
}

function selectEvent(ev){
  selected=ev;
  eventCountryOverlayOpen = false;
  renderList();
  refreshMap(filtered);
  renderEventCountryBrief(selected);
  const c=TC_HEX[ev.type]||'#6a6560';
  const confClass=ev.conf==='green'?'conf-green':ev.conf==='yellow'?'conf-yellow':'conf-red';
  const humanValidated = !!ev.public_review?.human_validated;
  const reviewedByHuman = !!ev.public_review?.reviewed_by_human;
  const provenanceTimeline = sortProvenanceTimeline(ev.public_review?.provenance_timeline || []);
  const linkedReports = getEventSources(ev);
  const councilAnalyses = ev.council?.analyses || {};
  const synthesis = councilAnalyses.synthesis;
  const knowledgeSignals = getPublicClassificationChips(ev);
  const analysisBlocks = getRenderablePublicAnalysis(ev);
  const publicDescription = getPublicEventDescription(ev);
  const publicContext = getPublicEventContext(ev);
  const provenanceSummaryItems = getPublicProvenanceSummary(ev, linkedReports, provenanceTimeline);
  const transparencyText = getPublicTransparencyText(ev, linkedReports);
  const classificationRows = getPublicClassificationRows(ev);
  const classificationSplit = splitClassificationRows(classificationRows);
  const typeLabel = getEventFamilyLabel(ev);
  const eventCategoryLabel = getEventDomainLabel(ev.event_type_domain || ev.event_category);
  const analystLenses = getEventAnalystLenses(ev);
  const countryLabel = ev.display_country || getEventCountryLabel(ev);
  const monitorEntry = getCountryMonitorEntry(ev.country || countryLabel);
  const predictiveSummary = getCountryPredictiveSummary(ev.country || countryLabel);
  const overallRisk = predictiveSummary?.overall_risk_score;
  const regimeConstruct = getCountryRiskConstruct(ev.country || countryLabel, 'regime_vulnerability');
  const militarizationConstruct = getCountryRiskConstruct(ev.country || countryLabel, 'militarization');
  const fragmentationConstruct = getCountryRiskConstruct(ev.country || countryLabel, 'security_fragmentation');
  const measureRows = monitorEntry ? [
    {
      label:'Regime vulnerability',
      value: formatMonitorValue(regimeConstruct?.score) ?? '—',
      note: regimeConstruct?.trend_label || 'current construct'
    },
    {
      label:'Militarization',
      value: formatMonitorValue(militarizationConstruct?.score) ?? '—',
      note: militarizationConstruct?.trend_label || 'current construct'
    },
    {
      label:'Security fragmentation',
      value: formatMonitorValue(fragmentationConstruct?.score) ?? '—',
      note: fragmentationConstruct?.trend_label || 'current construct'
    }
  ] : [];
  const countryTags = getEventCountryTags(ev);
  const primaryProfileCountry = countryTags.find(item=>item.isProfile)?.label || '';
  const overallRiskTone = getOverallRiskTone(overallRisk);
  const analystAssessmentText = (()=>{
    const raw = cleanCouncilAssessment(ev.public_analysis || '');
    return (!raw || isGenericCouncilText(raw)) ? '' : raw;
  })();
  document.getElementById('detail').innerHTML=`
    <div class="detail-brief">
      <div class="detail-country-line">
        <div class="detail-country-main">
          <div class="detail-country-kicker">Country Brief</div>
          <div class="detail-country-name">${escapeHtml(countryLabel)}</div>
          <div class="detail-country-actions">
            ${countryTags.map(renderCountryTagHtml).join('')}
            ${primaryProfileCountry ? `<a class="detail-profile-link" href="#" onclick="event.preventDefault();switchTab('profiles');setTimeout(()=>showCountryProfile('${escapeHtml(primaryProfileCountry).replace(/&#39;/g,"\\'")}'),80)">View country profile ↗</a>` : ''}
          </div>
        </div>
        ${(monitorEntry || predictiveSummary) ? `
          <div class="detail-overall-risk ${overallRiskTone}">
            <div class="detail-overall-risk-copy">
              <div class="detail-country-kicker">Overall risk</div>
              <div class="detail-measure-note">${predictiveSummary?.overall_risk_level ? `${escapeHtml(predictiveSummary.overall_risk_level)} outlook` : 'sentinel monitor active'}</div>
            </div>
            <div class="detail-overall-risk-value">${formatMonitorValue(overallRisk) ?? '—'}</div>
          </div>` : ''}
      </div>
      ${predictiveSummary?.summary_text ? `<div class="detail-text">${escapeHtml(predictiveSummary.summary_text)}</div>` : ''}
      ${measureRows.length ? `
        <details class="detail-more-grid">
          <summary class="detail-more-toggle">Sentinel measures</summary>
          <div class="detail-measures" style="margin-top:10px;">
            ${measureRows.map(item=>`
              <div class="detail-measure">
                <span class="detail-measure-label">${escapeHtml(item.label)}</span>
                <span class="detail-measure-value">${escapeHtml(item.value)}</span>
                <div class="detail-measure-note">${escapeHtml(item.note)}</div>
              </div>
            `).join('')}
          </div>
        </details>` : ''}
    </div>
    <div class="detail-event-hero">
      <div class="detail-hero-meta">
        <span class="type-badge" style="background:${c}">${escapeHtml(typeLabel)}</span>
        <span class="conf-badge ${confClass}">${ev.conf==='green'?'High':ev.conf==='yellow'?'Medium':'Low'} confidence</span>
        ${humanValidated?`<span class="src-badge tri" title="Validated by a human analyst">Human Validated</span>`:reviewedByHuman?`<span class="src-badge single" title="Reviewed by a human analyst">Human Reviewed</span>`:''}
        ${linkedReports.length>1
          ?`<span class="src-badge tri" title="Corroborated by ${linkedReports.length} reports">Corroborated · ${linkedReports.length} reports</span>`
          :`<span class="src-badge single">Single-report event</span>`}
      </div>
      <div class="detail-title">${escapeHtml(ev.standard_title || getStandardizedEventTitle(ev))}</div>
    </div>
    <div class="detail-meta">
      <div class="dmi"><label>ID</label><span>${escapeHtml(String(ev.sentinel_id || ev.id || '—'))}</span></div>
      <div class="dmi"><label>Location</label><span>${escapeHtml(ev.location || ev.country || 'Location pending')}</span></div>
      <div class="dmi"><label>Time</label><span>${escapeHtml(sentenceCaseDate(ev.date))}</span></div>
      <div class="dmi"><label>Type</label><span>${escapeHtml(eventCategoryLabel)}</span></div>
      <div class="dmi"><label>Category</label><span>${escapeHtml(typeLabel)}</span></div>
      <div class="dmi"><label>Salience</label><span style="color:${c}">${escapeHtml(String(ev.salience || 'pending').toUpperCase())}</span></div>
      <div class="dmi"><label>Coverage</label><span>${linkedReports.length} report${linkedReports.length===1?'':'s'}</span></div>
    </div>
    <div class="detail-section">
      <div class="detail-section-title">Event</div>
      <div class="detail-text">${publicDescription}</div>
      ${publicContext ? `<div class="detail-context"><span class="detail-context-label">Context</span><div class="detail-context-copy">${publicContext}</div></div>` : ''}
    </div>
    <div class="detail-section">
      <div class="detail-section-title">Classification</div>
      <div class="detail-grid">
        ${classificationSplit.visible.map(item=>`<div class="detail-kv"><label>${escapeHtml(item.label)}</label><span>${escapeHtml(item.value)}</span></div>`).join('')}
      </div>
      ${classificationSplit.hidden.length ? `
        <details class="detail-more-grid">
          <summary class="detail-more-toggle">More classification</summary>
          <div class="detail-grid" style="margin-top:10px;">
            ${classificationSplit.hidden.map(item=>`<div class="detail-kv"><label>${escapeHtml(item.label)}</label><span>${escapeHtml(item.value)}</span></div>`).join('')}
          </div>
        </details>
      ` : ''}
      ${knowledgeSignals.length ? `<div class="detail-chip-row" style="margin-top:10px;">${knowledgeSignals.map(item=>`<span class="detail-chip">${escapeHtml(item)}</span>`).join('')}</div>` : ''}
      ${analystLenses.length ? `<div class="detail-chip-row" style="margin-top:8px;">${analystLenses.map(item=>`<span class="analysis-badge ${item.className}">${escapeHtml(item.label)}</span>`).join('')}</div>` : ''}
    </div>
    ${(analystAssessmentText || analysisBlocks.length) ? `
    <div class="detail-section">
      <div class="detail-section-title">Analyst Assessment</div>
      <div class="detail-analysis">
        <div class="detail-analysis-meta">
          ${analystAssessmentText ? `<span class="detail-chip">AI · Sonnet 4.6</span>` : ''}
          ${synthesis?.risk_level?`<span class="detail-chip">${normalizeKnowledgeLabel(synthesis.risk_level)} concern</span>`:''}
        </div>
        ${analystAssessmentText ? `
          <div class="detail-analysis-copy">${escapeHtml(analystAssessmentText).replace(/\n{2,}/g,'</p><p style="margin-top:10px">').replace(/\n/g,' ')}</div>
        ` : ''}
        ${analysisBlocks.length ? `
          <details class="detail-more-grid" style="margin-top:${analystAssessmentText ? '14px' : '0'};">
            <summary class="detail-more-toggle">Framework analysis</summary>
            <div style="margin-top:10px;">
              ${analysisBlocks.map(block=>`<div class="detail-analysis-block"><span class="detail-analysis-label">${escapeHtml(block.label)}</span><div class="detail-analysis-copy">${block.value}</div></div>`).join('')}
            </div>
          </details>
        ` : ''}
      </div>
    </div>` : ''}
    ${linkedReports.length?`
    <div class="detail-section">
      <div class="detail-section-title">Sources</div>
      <div class="detail-source-list">
        ${linkedReports.map(item=>`
          <div class="detail-source-item">
            <div class="detail-source-main">
              <div class="detail-source-name">${escapeHtml(item.name || 'Source')}</div>
              <div class="detail-source-sub">${escapeHtml(item.role || 'Linked report')}${item.headline?` · ${escapeHtml(item.headline)}`:''}</div>
            </div>
            ${sanitizeExternalUrl(item.url)?`<a class="detail-source-link" href="${escapeHtml(sanitizeExternalUrl(item.url))}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`:''}
          </div>
        `).join('')}
      </div>
    </div>`:''}
    ${(transparencyText || provenanceSummaryItems.length)?`
    <div class="detail-section">
      <div class="detail-section-title">Transparency</div>
      ${transparencyText?`<div class="detail-text">${transparencyText}</div>`:''}
      ${provenanceSummaryItems.length?`<div class="detail-grid" style="margin-top:12px;">${provenanceSummaryItems.map(item=>`<div class="detail-kv"><label>${escapeHtml(item.label)}</label><span>${escapeHtml(item.value)}</span></div>`).join('')}</div>`:''}
    </div>`:''}
  `;
}

// ── CHARTS ───────────────────────────────────────────────────
const chartText='#96928c', chartGrid='rgba(0,0,0,0.04)';
const chartOpts={responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:chartText,font:{size:9,family:'DM Mono'}}},y:{grid:{color:chartGrid},ticks:{color:chartText,font:{size:9,family:'DM Mono'}},border:{display:false}}}};

// US Aid trend
// US Aid total LatAm 1990-2019 (economic + military dual line)
new Chart(document.getElementById('usChart'),{type:'bar',data:{
  labels:['90','91','92','93','94','95','96','97','98','99','00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19'],
  datasets:[
    {label:'Economic',data:[3114,2417,1923,1804,1267,969,914,975,1143,1775,2772,1535,2054,2177,1810,2265,3207,1940,2060,2618,4021,2355,2075,1685,1988,3186,1513,1895,1768,2128],backgroundColor:'rgba(26,83,143,0.55)',borderColor:'#1a538f',borderWidth:0,borderRadius:1},
    {label:'Military',data:[477,371,269,159,48,53,66,292,298,321,309,449,304,396,491,432,419,374,314,421,449,433,318,249,220,258,255,326,222,379],backgroundColor:'rgba(184,50,50,0.7)',borderColor:'#b83232',borderWidth:0,borderRadius:1}
  ]},options:{...chartOpts,plugins:{legend:{display:true,position:'top',labels:{color:chartText,font:{size:9,family:'DM Mono'},boxWidth:10,padding:12}}},scales:{...chartOpts.scales,x:{...chartOpts.scales.x,stacked:true},y:{...chartOpts.scales.y,stacked:true,ticks:{...chartOpts.scales.y.ticks,callback:v=>'$'+v+'M'}}}}});

// Top countries 2000-2019 trend
new Chart(document.getElementById('usCountryChart'),{type:'line',data:{
  labels:['00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19'],
  datasets:[
    {label:'Colombia',data:[1685,372,741,934,836,902,1528,461,853,1018,929,454,784,279,610,899,346,552,526,801],borderColor:'#1a538f',borderWidth:2,pointRadius:2,tension:0.3,fill:false},
    {label:'Haiti',data:[122,117,85,113,171,301,226,229,344,459,1597,672,536,398,381,536,395,321,257,258],borderColor:'#b83232',borderWidth:2,pointRadius:2,tension:0.3,fill:false},
    {label:'Peru',data:[294,295,376,306,260,168,366,121,154,131,238,204,122,138,179,324,104,128,131,183],borderColor:'#1a6e52',borderWidth:2,pointRadius:2,tension:0.3,fill:false},
    {label:'El Salvador',data:[50,193,178,124,99,55,80,630,86,58,73,99,71,77,91,356,79,124,97,86],borderColor:'#c46e12',borderWidth:2,pointRadius:2,tension:0.3,fill:false,borderDash:[4,2]},
    {label:'Mexico',data:[59,125,54,98,75,89,89,135,291,252,839,490,241,463,360,624,92,309,241,444],borderColor:'#6a4a6e',borderWidth:2,pointRadius:2,tension:0.3,fill:false,borderDash:[2,2]}
  ]},options:{...chartOpts,plugins:{legend:{display:true,position:'top',labels:{color:chartText,font:{size:9,family:'DM Mono'},boxWidth:10,padding:10}}},scales:{...chartOpts.scales,y:{...chartOpts.scales.y,ticks:{...chartOpts.scales.y.ticks,callback:v=>'$'+v+'M'}}}}});

// Economic vs Military breakdown by country (horizontal stacked bar)
new Chart(document.getElementById('usMilEconChart'),{type:'bar',data:{
  labels:['Colombia','Brazil','Peru','El Salvador','Haiti','Bolivia','Mexico','Guatemala'],
  datasets:[
    {label:'Economic',data:[20.91,16.77,11.31,11.23,11.26,10.26,7.74,7.98],backgroundColor:'rgba(26,83,143,0.55)',borderColor:'#1a538f',borderWidth:0,borderRadius:1},
    {label:'Military',data:[6.04,3.92,1.96,1.48,0.10,0.77,1.37,0.48],backgroundColor:'rgba(184,50,50,0.7)',borderColor:'#b83232',borderWidth:0,borderRadius:1}
  ]},options:{...chartOpts,indexAxis:'y',plugins:{legend:{display:true,position:'top',labels:{color:chartText,font:{size:9,family:'DM Mono'},boxWidth:10,padding:12}}},scales:{x:{grid:{color:chartGrid},ticks:{color:chartText,font:{size:9,family:'DM Mono'},callback:v=>'$'+v+'B'},stacked:true,border:{display:false}},y:{grid:{display:false},ticks:{color:chartText,font:{size:9,family:'DM Mono'}},stacked:true}}}});

// Regional monitor charts render after country monitor data loads.

// Coca cultivation
new Chart(document.getElementById('cocaChart'),{type:'bar',data:{labels:['2017','2018','2019','2020','2021','2022','2023','2024'],datasets:[{data:[171,169,154,143,204,230,214,230],backgroundColor:'rgba(184,50,50,0.22)',borderColor:'#b83232',borderWidth:1,borderRadius:2}]},options:{...chartOpts,scales:{...chartOpts.scales,y:{...chartOpts.scales.y,ticks:{...chartOpts.scales.y.ticks,callback:v=>v+'K'}}}}});

// Transnational Security coca chart (same data as Colombia tab for now)
new Chart(document.getElementById('tscocaChart'),{type:'bar',data:{labels:['2017','2018','2019','2020','2021','2022','2023','2024'],datasets:[{data:[171,169,154,143,204,230,214,230],backgroundColor:'rgba(106,74,110,0.22)',borderColor:'#6a4a6e',borderWidth:1,borderRadius:2}]},options:{...chartOpts,scales:{...chartOpts.scales,y:{...chartOpts.scales.y,ticks:{...chartOpts.scales.y.ticks,callback:v=>v+'K'}}}}});

// ── TIMELINE ─────────────────────────────────────────────────
// Helper: set type filter from bars or tags and keep both in sync
function tlSetType(v){
  tlFilter=v;
  document.querySelectorAll('.tl-tag').forEach(x=>x.classList.toggle('active',x.dataset.v===v));
  renderTimeline();
}

// ── HISTORICAL MILESTONES ────────────────────────────────────
const TL_MILESTONES=[
  // ── Constitutional milestones ─────────────────────────────
  {id:'m-br-1988',date:'1988-10-05',country:'Brazil',type:'reform',salience:'high',title:'Brazil adopts new democratic constitution — ends 21-year military rule, establishes civilian supremacy over armed forces',mLabel:'Constitutional'},
  {id:'m-co-1991',date:'1991-07-04',country:'Colombia',type:'reform',salience:'high',title:'Colombia promulgates new constitution — creates Constitutional Court, Ombudsman, expands civil liberties, restructures security sector',mLabel:'Constitutional'},
  {id:'m-ve-1999',date:'1999-12-15',country:'Venezuela',type:'reform',salience:'high',title:'Venezuela adopts Bolivarian Constitution under Chávez — expands executive power, renames armed forces, mandates active military participation in national development',mLabel:'Constitutional'},
  {id:'m-ec-2008',date:'2008-09-28',country:'Ecuador',type:'reform',salience:'high',title:'Ecuador adopts new constitution under Correa — restructures security sector, creates civilian oversight bodies',mLabel:'Constitutional'},
  {id:'m-bo-2009',date:'2009-01-25',country:'Bolivia',type:'reform',salience:'high',title:'Bolivia ratifies plurinational constitution — indigenous recognition, military restructuring, nationalization mandate embedded in founding law',mLabel:'Constitutional'},
  // ── Transitions & SSR milestones ──────────────────────────
  {id:'m-ni-1990',date:'1990-02-25',country:'Nicaragua',type:'reform',salience:'high',title:'Chamorro defeats Ortega — first peaceful transfer from revolutionary civil-military state; Sandinista army begins formal subordination to civilian control',mLabel:'Transition'},
  {id:'m-cl-1990',date:'1990-03-11',country:'Chile',type:'reform',salience:'high',title:'Aylwin inaugurated as first democratic president since 1973 — Pinochet remains Army commander-in-chief until 1998; "authoritarian enclaves" model',mLabel:'Transition'},
  {id:'m-ni-1995',date:'1995-03-01',country:'Nicaragua',type:'reform',salience:'medium',title:'Gen. Humberto Ortega steps down as army chief — Sandinista-army formally subordinated to civilian control; institution renamed Ejército de Nicaragua',mLabel:'SSR Milestone'},
  {id:'m-gt-1996',date:'1996-12-29',country:'Guatemala',type:'peace',salience:'high',title:'Guatemalan Peace Accords end 36-year civil war — mandate military reduction, civilian police creation, PAC dissolution, intelligence reform',mLabel:'Peace Accords / SSR'},
  {id:'m-sv-1992',date:'1992-01-16',country:'El Salvador',type:'peace',salience:'high',title:'Chapultepec Peace Accords end 12-year civil war — National Civil Police created; military barred from domestic law enforcement; model Central American SSR',mLabel:'Peace Accords / SSR'},
  {id:'m-ht-1994',date:'1994-10-15',country:'Haiti',type:'reform',salience:'high',title:'Operation Uphold Democracy restores Aristide — Haitian Armed Forces formally disbanded; HNP created; most complete military abolition in hemisphere history',mLabel:'Military Disbanded'},
  {id:'m-cl-1998',date:'1998-10-16',country:'Chile',type:'reform',salience:'high',title:'Pinochet arrested in London on crimes against humanity warrant — shatters military immunity framework; transitional justice precedent permanently altered',mLabel:'Transitional Justice'},
  {id:'m-co-2000',date:'2000-07-13',country:'Colombia',type:'aid',salience:'high',title:'Plan Colombia signed — $1.3B US security package begins; largest US military aid program in Western Hemisphere history; transforms Colombian Armed Forces capability',mLabel:'Plan Colombia'},
  {id:'m-co-2016',date:'2016-11-24',country:'Colombia',type:'peace',salience:'high',title:'Final Peace Agreement with FARC-EP signed — most significant DDR process in Western Hemisphere since 1990s; JEP created with jurisdiction over military officers',mLabel:'FARC Peace Accord'},
  {id:'m-mx-2019',date:'2019-06-27',country:'Mexico',type:'reform',salience:'high',title:'National Guard created under AMLO — militarized force replaces Federal Police; begins institutionalized militarization of domestic security',mLabel:'Nat\'l Guard Created'},
  {id:'m-mx-2024',date:'2024-11-04',country:'Mexico',type:'other',salience:'high',title:'Sheinbaum passes constitutional reform placing National Guard permanently under military command — deepest change to Mexican civil-military relations since 1917',mLabel:'Security Militarized'},
  // ── Coups, autogolpes & coup attempts ─────────────────────
  {id:'m-sr-1990',date:'1990-12-24',country:'Suriname',type:'coup',salience:'medium',title:'"Telephone coup" — Bouterse\'s forces overthrow civilian government by phone; new elections restore civilian rule May 1991; Bouterse\'s recurring intervention cycle continues',mLabel:'Coup'},
  {id:'m-ht-1991',date:'1991-09-30',country:'Haiti',type:'coup',salience:'high',title:'Gen. Cédras ousts President Aristide in military coup — OAS/UN embargo follows; reversed by US Operation Uphold Democracy 1994; FAd\'H subsequently disbanded',mLabel:'Coup'},
  {id:'m-ve-1992a',date:'1992-02-04',country:'Venezuela',type:'coup',salience:'high',title:'Lt. Col. Chávez leads failed coup against President Pérez — "por ahora" speech launches his political career; demonstrates deep military fractures in Punto Fijo system',mLabel:'Coup Attempt'},
  {id:'m-ve-1992b',date:'1992-11-27',country:'Venezuela',type:'coup',salience:'high',title:'Second Venezuelan coup attempt — larger navy/air force operation; also fails; confirms anti-system civil-military insurgency is structural, not aberrational',mLabel:'Coup Attempt'},
  {id:'m-pe-1992',date:'1992-04-05',country:'Peru',type:'coup',salience:'high',title:'Fujimori autogolpe — closes Congress, suspends constitution with military backing; Montesinos runs state 1992–2000; benchmark Latin American civil-military authoritarian fusion',mLabel:'Autogolpe'},
  {id:'m-gt-1993',date:'1993-05-25',country:'Guatemala',type:'coup',salience:'high',title:'Serrano autogolpe attempt fails — unlike Peru, military refuses to back him; Constitutional Court rules illegal; military removes Serrano; US/OAS pressure decisive',mLabel:'Failed Autogolpe'},
  {id:'m-ec-1997',date:'1997-02-06',country:'Ecuador',type:'coup',salience:'medium',title:'Congress removes President Bucaram ("mental incapacity") amid mass protests — armed forces refuse to defend him; military-as-institutional-arbiter model established',mLabel:'Soft Removal'},
  {id:'m-ec-2000',date:'2000-01-21',country:'Ecuador',type:'coup',salience:'high',title:'President Mahuad overthrown by indigenous-military coalition — Col. Gutiérrez co-leads; VP Noboa assumes power; only successful coup in Latin America 1994–2009',mLabel:'Coup'},
  {id:'m-ve-2002',date:'2002-04-11',country:'Venezuela',type:'coup',salience:'high',title:'Military coup briefly removes Chávez — Carmona installed; reversed in 47 hours by loyalist units and mass protests; hardened purge of opposition officers',mLabel:'Coup Attempt'},
  {id:'m-bo-2003',date:'2003-10-12',country:'Bolivia',type:'conflict',salience:'high',title:'"Gas War" — army fires on El Alto protesters, killing 60+; President Sánchez de Lozada resigns and flees US; military violence directly causes regime change',mLabel:'Gas War'},
  {id:'m-ec-2005',date:'2005-04-20',country:'Ecuador',type:'coup',salience:'medium',title:'President Gutiérrez ousted by mass protests — armed forces refuse to defend him; third consecutive Ecuadorian presidential removal via military acquiescence since 1997',mLabel:'Soft Removal'},
  {id:'m-hn-2009',date:'2009-06-28',country:'Honduras',type:'coup',salience:'high',title:'Military arrests President Zelaya at gunpoint and exiles him — first unambiguous coup in Central America in decades; OAS suspends Honduras',mLabel:'Coup'},
  {id:'m-ec-2010',date:'2010-09-30',country:'Ecuador',type:'coup',salience:'high',title:'Police rebellion detains President Correa — military rescues him; contested as coup attempt vs. labor dispute; consolidates Correa\'s political position',mLabel:'Coup Attempt'},
  {id:'m-py-2012',date:'2012-06-22',country:'Paraguay',type:'coup',salience:'high',title:'President Lugo removed in 24-hour "express impeachment" — MERCOSUR/UNASUR term it a parliamentary coup; military accepts outcome; Paraguay suspended from MERCOSUR',mLabel:'Parliamentary Coup'},
  {id:'m-bo-2019',date:'2019-11-10',country:'Bolivia',type:'coup',salience:'high',title:'Military chief publicly suggests Morales resign after disputed election — police mutiny; Morales flees; Áñez assumes power; contested classification (coup vs. restoration)',mLabel:'Coup / Resignation'},
  {id:'m-ht-2021',date:'2021-07-07',country:'Haiti',type:'coup',salience:'high',title:'President Moïse assassinated by Colombian mercenaries — security apparatus collapses; gang territorial expansion accelerates; MSS intervention process begins',mLabel:'Assassination'},
  {id:'m-bo-2024',date:'2024-06-26',country:'Bolivia',type:'coup',salience:'high',title:'Gen. Zúñiga leads armored column that rams Presidential Palace in failed coup attempt — other commanders refuse support; collapses within hours; linked to Arce-Morales MAS split',mLabel:'Coup Attempt'},
  {id:'m-ve-2026',date:'2026-01-03',country:'Venezuela',type:'coup',salience:'high',title:'Operation Absolute Resolve — US-backed operation captures Maduro in Caracas; Rodríguez acting government; FANB cohesion crisis; election timeline contested',mLabel:'Op. Absolute Resolve'},
  // ── Democratic backsliding via military ───────────────────
  {id:'m-mx-2007',date:'2007-01-11',country:'Mexico',type:'conflict',salience:'high',title:'Calderón deploys army to Michoacán — formal start of military takeover of domestic security; 36,000 soldiers deployed by mid-2007; militarization of public security begins',mLabel:'Drug War Begins'},
  {id:'m-ve-2008',date:'2008-09-01',country:'Venezuela',type:'purge',salience:'high',title:'Chávez retires 26 generals, replaces with loyalty-vetted officers — ideological alignment institutionalized as FANB promotion criterion; FANB conversion to Bolivarian institution',mLabel:'FANB Purge'},
  {id:'m-ve-2013',date:'2013-04-14',country:'Venezuela',type:'other',salience:'high',title:'Maduro wins post-Chávez election — FANB endorses disputed result; military shifts from Chávez\'s personal instrument to systemic guarantor of chavismo as a system',mLabel:'FANB Endorsement'},
  {id:'m-br-2018',date:'2018-10-28',country:'Brazil',type:'other',salience:'high',title:'Bolsonaro elected — retired captain appoints ~6,000 military officers to government; Gen. Mourão as VP; most significant remilitarization of Brazilian politics since 1985',mLabel:'Military in Politics'},
  {id:'m-sv-2021a',date:'2021-02-09',country:'El Salvador',type:'other',salience:'high',title:'Bukele deploys soldiers to Legislative Assembly to coerce security loan vote — most explicit autogolpe-adjacent act in hemisphere since Fujimori 1992; OAS condemns',mLabel:'Military in Congress'},
  {id:'m-sv-2021b',date:'2021-05-01',country:'El Salvador',type:'other',salience:'high',title:'NUEVAS IDEAS supermajority fires Supreme Court magistrates and AG on day one — judicial oversight of military eliminated; constitutional framework for Régimen de Excepción installed',mLabel:'Institutional Capture'},
  {id:'m-sv-2022',date:'2022-03-27',country:'El Salvador',type:'conflict',salience:'high',title:'Régimen de Excepción declared — military/police joint operations suspend due process; 88,000+ detained by 2026, 235+ custody deaths; Bukele model institutionalized',mLabel:'Régimen de Excepción'},
  {id:'m-ve-2017',date:'2017-07-30',country:'Venezuela',type:'other',salience:'high',title:'Maduro convenes Constituent Assembly (ANC) — FANB provides security for disputed election; opposition boycotts; military protection of ANC completes FANB conversion to regime pillar',mLabel:'ANC / FANB as Regime'},
  {id:'m-ec-2024',date:'2024-01-09',country:'Ecuador',type:'conflict',salience:'high',title:'Noboa declares "internal armed conflict" against OC groups — military deploys under IHL framework; armed group seizes TV live; Bukele model adopted in Ecuador',mLabel:'Internal Armed Conflict'},
  {id:'m-gt-2024',date:'2024-01-14',country:'Guatemala',type:'other',salience:'high',title:'Military and police used to block vote counts and obstruct Arévalo\'s inauguration — armed forces maintain ambiguous "neutrality" while available to anti-democratic actors',mLabel:'Electoral Obstruction'},
  {id:'m-ve-2024',date:'2024-07-28',country:'Venezuela',type:'other',salience:'high',title:'FANB endorses Maduro\'s fraudulent election claim — Padrino López and commanders publicly reaffirm loyalty; FANB\'s organic role as electoral pillar of regime confirmed',mLabel:'FANB Electoral Fraud'},
  // ── Protests & repression ─────────────────────────────────
  {id:'m-ve-2014',date:'2014-02-12',country:'Venezuela',type:'protest',salience:'high',title:'"La Salida" — FANB, police, and colectivos kill 43, injure hundreds; Leopoldo López imprisoned; first major test of FANB loyalty under Maduro',mLabel:'Repression'},
  {id:'m-ni-2018',date:'2018-04-18',country:'Nicaragua',type:'protest',salience:'high',title:'Mass protests against Ortega — 325+ killed by police, Sandinista youth, and armed turbas; army formally neutral but acquiescent; Nicaragua completes authoritarian turn',mLabel:'Repression'},
  {id:'m-ve-2019b',date:'2019-04-30',country:'Venezuela',type:'other',salience:'high',title:'Guaidó\'s "Operación Libertad" — calls for military uprising at La Carlota; small group briefly joins, collapses within hours; top FANB including Padrino López remain loyal to Maduro',mLabel:'Failed Defection'},
  {id:'m-ec-2019',date:'2019-10-02',country:'Ecuador',type:'protest',salience:'medium',title:'Protests against Moreno\'s IMF austerity measures — state of emergency; military deployed; 8 killed, hundreds injured; Moreno evacuates government to Guayaquil',mLabel:'Protest / Deployment'},
  {id:'m-cl-2019',date:'2019-10-18',country:'Chile',type:'protest',salience:'high',title:'Estallido Social — military deployed for first time since 1987; 8,827 injured, 460 with eye injuries from rubber bullets; triggers 2020 constitutional plebiscite',mLabel:'Estallido Social'},
  {id:'m-cu-2021',date:'2021-07-11',country:'Cuba',type:'protest',salience:'high',title:'11J protests — largest in Cuba since 1959; military and Brigadas de Respuesta Rápida deployed; 1,400+ detained; dozens sentenced to long prison terms',mLabel:'11J Repression'},
  {id:'m-br-2022b',date:'2022-11-01',country:'Brazil',type:'other',salience:'high',title:'Bolsonaro refuses to concede after Lula victory — military encampments at barracks; Army commander General Freitas ambiguous; coup planning documents later found in military homes',mLabel:'Election Crisis'},
  {id:'m-br-2023',date:'2023-01-08',country:'Brazil',type:'coup',salience:'high',title:'Bolsonaro supporters storm Congress, Planalto, and Supreme Court — military police accused of passivity; coup planning documents found; worst breach of constitutional order since 1964',mLabel:'Jan. 8 Coup Attempt'},
  // ── COVID militarization ──────────────────────────────────
  {id:'m-sv-2020',date:'2020-03-21',country:'El Salvador',type:'conflict',salience:'medium',title:'Bukele deploys military for COVID enforcement — detention centers for quarantine violators; extrajudicial detentions documented; precursor to 2022 Régimen de Excepción',mLabel:'COVID Militarization'},
  {id:'m-br-2020',date:'2020-05-15',country:'Brazil',type:'other',salience:'medium',title:'General Pazuello appointed Health Minister — first general to run Health Ministry in peacetime Brazil; peak of military penetration across Bolsonaro executive branch',mLabel:'Military Runs Health Ministry'},
  {id:'m-ve-2020',date:'2020-03-17',country:'Venezuela',type:'conflict',salience:'medium',title:'FANB, SEBIN, and colectivos deployed for COVID quarantine enforcement — military as primary enforcement mechanism with no civilian oversight; civil-military fusion deepens',mLabel:'COVID Militarization'},
  // ── Major elections with CMR significance ─────────────────
  {id:'m-cl-2021',date:'2021-12-19',country:'Chile',type:'other',salience:'high',title:'Gabriel Boric elected — campaigns on demilitarization of Araucanía and security sector reform; inauguration Mar 2022',mLabel:'Election'},
  {id:'m-co-2022',date:'2022-06-19',country:'Colombia',type:'other',salience:'high',title:'Gustavo Petro elected — first leftist president in Colombian history; launches Total Peace doctrine; restructures military command, reduces offensive operations',mLabel:'Election'},
  {id:'m-br-2022',date:'2022-10-30',country:'Brazil',type:'other',salience:'high',title:'Lula defeats Bolsonaro — ends four years of unprecedented military involvement in executive government; civilian purge of military-aligned positions begins',mLabel:'Election'},
  {id:'m-ar-2023',date:'2023-11-19',country:'Argentina',type:'other',salience:'high',title:'Javier Milei elected — libertarian outsider; pledges radical defense cuts; transitional justice processes continue; civil-military posture in transition',mLabel:'Election'},
  {id:'m-sv-2024',date:'2024-02-04',country:'El Salvador',type:'other',salience:'high',title:'Bukele re-elected with 85% despite constitutional prohibition — Régimen de Excepción and military integration into domestic security continue as permanent governance',mLabel:'Election'},
  {id:'m-ec-2025',date:'2025-02-09',country:'Ecuador',type:'other',salience:'high',title:'Daniel Noboa re-elected — mandate continues internal armed conflict framework and military deployment in prisons and urban zones',mLabel:'Election'},
  {id:'m-uy-2025',date:'2025-03-01',country:'Uruguay',type:'other',salience:'high',title:'Yamandú Orsi inaugurated — Frente Amplio returns to power; continuation of Uruguay\'s strong civilian control model, strongest in Southern Cone',mLabel:'Inauguration'},
];

function renderTimeline(){
  const MONTH_ABBR=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const TYPE_LABELS={all:'All',coup:'Coup',purge:'Purge',coup_proofing:'Coup-Proofing',
    conflict:'Conflict',reform:'Reform',oc:'Org. Crime',aid:'Mil. Aid',coop:'US Coop',
    protest:'Protest',exercise:'Exercise',peace:'Peace',other:'Other'};

  // ── Base filter predicate (for all derived counts) ───────
  function baseMatch(ev){
    if(tlCountry!=='all'&&ev.country!==tlCountry) return false;
    if(tlSalience!=='all'&&ev.salience!==tlSalience) return false;
    if(tlConf!=='all'&&ev.conf!==tlConf) return false;
    if(tlYear!=='all'&&!ev.date.startsWith(tlYear)) return false;
    if(tlMonth!=='all'&&ev.date.substring(5,7)!==tlMonth) return false;
    return true;
  }

  // ── Confidence filter tags ───────────────────────────────
  document.querySelectorAll('.tl-conf').forEach(t=>{
    t.classList.toggle('active', t.dataset.v===tlConf);
    t.onclick=function(){tlConf=this.dataset.v;renderTimeline();};
  });

  const evs=allEvents
    .filter(ev=>baseMatch(ev)&&(tlFilter==='all'||ev.type===tlFilter))
    .sort((a,b)=>b.date.localeCompare(a.date));

  const el=document.getElementById('timeline-list');
  if(!el) return;
  document.getElementById('tl-count').textContent=evs.length;

  // ── Year filter tags (dynamic) ───────────────────────────
  const yearEl=document.getElementById('tl-year-filters');
  if(yearEl){
    const years=[...new Set(allEvents.map(ev=>ev.date.substring(0,4)))].sort((a,b)=>b-a);
    yearEl.innerHTML=`<span class="tag${tlYear==='all'?' active':''} tl-year" data-v="all">All</span>`
      +years.map(y=>`<span class="tag${tlYear===y?' active':''} tl-year" data-v="${y}">${y}</span>`).join('');
    yearEl.querySelectorAll('.tl-year').forEach(t=>{
      t.onclick=function(){tlYear=this.dataset.v;tlMonth='all';renderTimeline();};
    });
  }

  // ── Month filter tags (dynamic, filtered by year) ────────
  const monthEl=document.getElementById('tl-month-filters');
  if(monthEl){
    const yearBase=allEvents.filter(ev=>tlYear==='all'||ev.date.startsWith(tlYear));
    const months=[...new Set(yearBase.map(ev=>ev.date.substring(5,7)))].sort();
    monthEl.innerHTML=`<span class="tag${tlMonth==='all'?' active':''} tl-month" data-v="all">All</span>`
      +months.map(m=>`<span class="tag${tlMonth===m?' active':''} tl-month" data-v="${m}">${MONTH_ABBR[parseInt(m)]}</span>`).join('');
    monthEl.querySelectorAll('.tl-month').forEach(t=>{
      t.onclick=function(){tlMonth=this.dataset.v;renderTimeline();};
    });
  }

  // ── Update type tag counts and active state ──────────────
  const typeCts={};
  allEvents.filter(ev=>baseMatch(ev)).forEach(ev=>{typeCts[ev.type]=(typeCts[ev.type]||0)+1;});
  document.querySelectorAll('.tl-tag').forEach(t=>{
    const v=t.dataset.v;
    const baseText=TYPE_LABELS[v]||v;
    const n=v==='all'?allEvents.filter(ev=>baseMatch(ev)).length:(typeCts[v]||0);
    t.innerHTML=`${baseText}<span class="tag-n">${n}</span>`;
    t.classList.toggle('active', v===tlFilter);
  });

  // ── Type activity bars ───────────────────────────────────
  const typeBarsEl=document.getElementById('tl-type-bars');
  if(typeBarsEl){
    const sortedTypes=Object.entries(typeCts).sort((a,b)=>b[1]-a[1]);
    const maxTN=sortedTypes[0]?.[1]||1;
    typeBarsEl.innerHTML=sortedTypes.map(([t,n])=>`
      <div class="tl-ctry-bar-row${tlFilter===t?' tl-ctry-active':''}" style="opacity:${tlFilter==='all'||tlFilter===t?1:0.45};"
           onclick="tlSetType(tlFilter==='${t}'?'all':'${t}');">
        <span class="tl-ctry-bar-label">${TYPE_LABELS[t]||t}</span>
        <div class="tl-ctry-bar-track"><div class="tl-ctry-bar-fill" style="width:${(n/maxTN*100).toFixed(0)}%;background:${TC_HEX[t]||'#6a6560'};"></div></div>
        <span class="tl-ctry-bar-n">${n}</span>
      </div>`).join('');
  }

  // ── Country activity bars ─────────────────────────────────
  const barsEl=document.getElementById('tl-country-bars');
  if(barsEl){
    const allCts={};
    allEvents.filter(ev=>baseMatch(ev)&&(tlFilter==='all'||ev.type===tlFilter))
             .forEach(ev=>{allCts[ev.country]=(allCts[ev.country]||0)+1;});
    const sorted=Object.entries(allCts).sort((a,b)=>b[1]-a[1]);
    const maxN=sorted[0]?.[1]||1;
    const ctryDomColor={};
    allEvents.forEach(ev=>{if(!ctryDomColor[ev.country])ctryDomColor[ev.country]=TC_HEX[ev.type]||'#6a6560';});
    barsEl.innerHTML=sorted.map(([c,n])=>`
      <div class="tl-ctry-bar-row${tlCountry===c?' tl-ctry-active':''}" style="opacity:${tlCountry==='all'||tlCountry===c?1:0.45};" onclick="tlCountry=tlCountry==='${c}'?'all':'${c}';renderTimeline();">
        <span class="tl-ctry-bar-label">${c}</span>
        <div class="tl-ctry-bar-track"><div class="tl-ctry-bar-fill" style="width:${(n/maxN*100).toFixed(0)}%;background:${ctryDomColor[c]};"></div></div>
        <span class="tl-ctry-bar-n">${n}</span>
      </div>`).join('');
  }

  // ── Type / Salience filter bindings ──────────────────────
  document.querySelectorAll('.tl-tag').forEach(t=>{
    t.onclick=function(){tlSetType(this.dataset.v);};
  });
  document.querySelectorAll('.tl-sal').forEach(t=>{
    t.onclick=function(){document.querySelectorAll('.tl-sal').forEach(x=>x.classList.remove('active'));this.classList.add('active');tlSalience=this.dataset.v;renderTimeline();};
  });

  // ── Event rows ───────────────────────────────────────────
  if(!evs.length){
    el.innerHTML='<div style="padding:24px;color:var(--text-muted);font-family:var(--mono);font-size:9.5px;text-align:center;">No events match current filters.</div>';
    return;
  }
  // ── Merge milestones ─────────────────────────────────────
  const visMilestones=TL_MILESTONES.filter(m=>{
    if(tlFilter!=='all'&&m.type!==tlFilter) return false;
    if(tlCountry!=='all'&&m.country!==tlCountry) return false;
    if(tlYear!=='all'&&!m.date.startsWith(tlYear)) return false;
    if(tlMonth!=='all'&&m.date.substring(5,7)!==tlMonth) return false;
    if(tlSalience==='medium'||tlSalience==='low') return false; // milestones are all high-salience
    return true;
  });
  const combined=[...evs,...visMilestones.map(m=>({...m,_milestone:true}))];
  combined.sort((a,b)=>b.date.localeCompare(a.date));
  document.getElementById('tl-count').textContent=combined.length;

  if(!combined.length){
    el.innerHTML='<div style="padding:24px;color:var(--text-muted);font-family:var(--mono);font-size:9.5px;text-align:center;">No events match current filters.</div>';
    return;
  }

  // ── Group by year ─────────────────────────────────────────
  const byYear={};
  combined.forEach(ev=>{const y=ev.date.substring(0,4);if(!byYear[y])byYear[y]=[];byYear[y].push(ev);});
  const years=Object.keys(byYear).sort((a,b)=>b-a);

  el.innerHTML='<div class="vtl">'+years.map(year=>{
    const items=byYear[year];
    const yearHdr=`<div class="vtl-year-hdr">
      <span class="vtl-year-label">${year}</span>
      <div class="vtl-year-line"></div>
      <span class="vtl-year-ct">${items.length} ${items.length===1?'entry':'entries'}</span>
    </div>`;
    const track=`<div class="vtl-track">${items.map(ev=>{
      const isMilestone=!!ev._milestone;
      const c=TC_HEX[ev.type]||'#6a6560';
      const salDot=!isMilestone?(ev.salience==='high'?`<span style="color:var(--coup);font-size:9px;line-height:1;" title="High salience">●●</span>`:ev.salience==='medium'?`<span style="color:var(--purge);font-size:9px;line-height:1;" title="Medium salience">●</span>`:''):'';
      let srcHtml='';
      if(!isMilestone){
        if(ev.links&&ev.links.length){
          srcHtml=`<div class="vtl-src-row">${ev.links.map((l,i)=>`<a class="tl-src" href="${l}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${(ev.sources&&ev.sources[i])||ev.source} ↗</a>`).join('')}</div>`;
        } else if(ev.url){
          srcHtml=`<div class="vtl-src-row"><a class="tl-src" href="${ev.url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${ev.source} ↗</a></div>`;
        }
      }
      const metaBadge=isMilestone
        ?`<span class="vtl-milestone-badge">${ev.mLabel||ev.type}</span>`
        :`<span class="vtl-type-tag" style="color:${c}">${TYPE_LABEL[ev.type]||ev.type}</span>`;
      return `<div class="vtl-item${isMilestone?' vtl-milestone':''}" ${!isMilestone?`data-id="${ev.id}"`:''}">
        <div class="vtl-dot-wrap"><div class="vtl-dot${isMilestone?' vtl-dot-sq':''}" style="border-color:${isMilestone?'var(--border2)':c}"></div></div>
        <div class="vtl-card">
          <div class="vtl-card-meta">
            ${metaBadge}
            <span class="vtl-country-tag">${ev.country}</span>
            ${salDot}
            <span class="vtl-date-tag">${ev.date}</span>
          </div>
          <div class="vtl-title">${ev.title}</div>
          ${srcHtml}
        </div>
      </div>`;
    }).join('')}</div>`;
    return yearHdr+track;
  }).join('')+'</div>';

  // ── Row click — deep-link to events tab ─────────────────
  el.querySelectorAll('.vtl-item[data-id]').forEach(row=>{
    row.querySelector('.vtl-card').addEventListener('click',e=>{
      if(e.target.tagName==='A') return;
      const ev=allEvents.find(x=>String(x.id)===row.dataset.id);
      if(!ev) return;
      switchTab('events');
      setTimeout(()=>{if(map)map.invalidateSize();selectEvent(ev);},80);
    });
  });
}

// ── OVERVIEW D3 MAP ──────────────────────────────────────────
const LATAM_IDS = new Set([76,170,484,862,32,604,152,218,68,340,558,320,222,600,858,192,332,214,591,188,388,780,328,740,84]);
const COUNTRY_NAMES_MAP = {76:"Brazil",170:"Colombia",484:"Mexico",862:"Venezuela",32:"Argentina",604:"Peru",152:"Chile",218:"Ecuador",68:"Bolivia",340:"Honduras",558:"Nicaragua",320:"Guatemala",222:"El Salvador",600:"Paraguay",858:"Uruguay",192:"Cuba",332:"Haiti",214:"Dominican Republic",591:"Panama",188:"Costa Rica",388:"Jamaica",780:"Trinidad and Tobago",328:"Guyana",740:"Suriname",84:"Belize"};
// Reverse map: name → numeric ID for Events/Overview geographic lookups
const COUNTRY_NAME_TO_ID = Object.fromEntries(Object.entries(COUNTRY_NAMES_MAP).map(([id,n])=>[n,+id]));
// Cache world features once topology is loaded for the overview and events maps
let worldFeatures = null;
let worldFeaturesPromise = null;
async function ensureWorldFeaturesLoaded(){
  if(worldFeatures) return worldFeatures;
  if(worldFeaturesPromise) return worldFeaturesPromise;
  worldFeaturesPromise = d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
    .then(world=>{
      worldFeatures = topojson.feature(world, world.objects.countries).features;
      return worldFeatures;
    })
    .catch(error=>{
      worldFeaturesPromise = null;
      throw error;
    });
  return worldFeaturesPromise;
}
const COUNTRY_STATS = {
  "Brazil":             {spending:"$29.4B",personnel:"366K",usAid:"$102M"},
  "Colombia":           {spending:"$14.1B",personnel:"295K",usAid:"$461M"},
  "Mexico":             {spending:"$9.4B", personnel:"277K",usAid:"$332M"},
  "Venezuela":          {spending:"$3.2B", personnel:"123K",usAid:"—"},
  "Argentina":          {spending:"$4.7B", personnel:"75K", usAid:"—"},
  "Peru":               {spending:"$2.9B", personnel:"95K", usAid:"$175M"},
  "Chile":              {spending:"$6.5B", personnel:"80K", usAid:"—"},
  "Ecuador":            {spending:"$2.4B", personnel:"40K", usAid:"$138M"},
  "Bolivia":            {spending:"$680M", personnel:"34K", usAid:"—"},
  "Honduras":           {spending:"$410M", personnel:"15K", usAid:"$83M"},
  "Nicaragua":          {spending:"$90M",  personnel:"12K", usAid:"—"},
  "Guatemala":          {spending:"$340M", personnel:"22K", usAid:"$69M"},
  "El Salvador":        {spending:"$290M", personnel:"25K", usAid:"$46M"},
  "Paraguay":           {spending:"$520M", personnel:"14K", usAid:"—"},
  "Uruguay":            {spending:"$1.1B", personnel:"22K", usAid:"—"},
  "Cuba":               {spending:"~$1.8B",personnel:"49K", usAid:"—"},
  "Haiti":              {spending:"$103M", personnel:"~10K (HNP)", usAid:"$187M"},
  "Dominican Republic": {spending:"$730M", personnel:"56K", usAid:"$15M"},
  "Panama":             {spending:"$450M", personnel:"12K (security forces)", usAid:"$15M"},
  "Costa Rica":         {spending:"$310M", personnel:"9K (Public Force)", usAid:"$20M"},
  "Jamaica":            {spending:"$80M",  personnel:"4K", usAid:"$3M"},
  "Trinidad and Tobago":{spending:"$220M", personnel:"4K", usAid:"—"},
  "Guyana":             {spending:"$250M", personnel:"4K", usAid:"$4M"},
  "Suriname":           {spending:"$90M",  personnel:"2K", usAid:"—"},
  "Belize":             {spending:"$26M",  personnel:"1.5K", usAid:"$2M"},
};
// ── ACLED CONFLICT INDEX 2025 ─────────────────────────────────
const COUNTRY_ACLED = {
  "Mexico":             {level:"Extreme",     ranking:4},
  "Ecuador":            {level:"Extreme",     ranking:6},
  "Brazil":             {level:"Extreme",     ranking:7},
  "Haiti":              {level:"Extreme",     ranking:8},
  "Colombia":           {level:"High",        ranking:14},
  "Guatemala":          {level:"High",        ranking:17},
  "Honduras":           {level:"High",        ranking:26},
  "Jamaica":            {level:"High",        ranking:28},
  "Trinidad and Tobago":{level:"Turbulent",   ranking:32},
  "Venezuela":          {level:"Turbulent",   ranking:34},
  "Peru":               {level:"Turbulent",   ranking:43},
  "Chile":              {level:"Turbulent",   ranking:46},
  "Belize":             {level:"Turbulent",   ranking:49},
  "Bolivia":            {level:"Low",         ranking:52},
  "Dominican Republic": {level:"Low",         ranking:69},
  "El Salvador":        {level:"Low",         ranking:75},
  "Nicaragua":          {level:"Low",         ranking:79},
  "Cuba":               {level:"Low",         ranking:83},
  "Costa Rica":         {level:"Low",         ranking:84},
  "Guyana":             {level:"Low",         ranking:87},
  "Argentina":          {level:"Low",         ranking:92},
  "Paraguay":           {level:"Low",         ranking:113},
  "Panama":             {level:"Low",         ranking:116},
  "Suriname":           {level:"Low",         ranking:130},
  "Uruguay":            {level:"Low",         ranking:156},
};

// ── M3 DATASET — CMR INDICATORS (2020 data) ────────────────────
// com_mil_serv=compulsory service, mil_veto=military veto,
// mil_impun=impunity, milpol_crime=crime policing,
// mil_eco_dummy=economic role, hwi=Hybrid Warfare Index
const COUNTRY_M3 = {
  "Brazil":             {conscription:1, milVeto:0, milImpunity:1, milCrimePolice:0, milEco:0, hwi:1.3},
  "Colombia":           {conscription:1, milVeto:0, milImpunity:0, milCrimePolice:null, milEco:1, hwi:0.8},
  "Mexico":             {conscription:1, milVeto:0, milImpunity:1, milCrimePolice:1, milEco:1, hwi:1.0},
  "Venezuela":          {conscription:1, milVeto:1, milImpunity:1, milCrimePolice:0, milEco:1, hwi:3.6},
  "Argentina":          {conscription:0, milVeto:0, milImpunity:0, milCrimePolice:0, milEco:0, hwi:2.9},
  "Peru":               {conscription:0, milVeto:0, milImpunity:1, milCrimePolice:0, milEco:1, hwi:3.8},
  "Chile":              {conscription:1, milVeto:0, milImpunity:0, milCrimePolice:0, milEco:1, hwi:7.8},
  "Ecuador":            {conscription:0, milVeto:0, milImpunity:0, milCrimePolice:1, milEco:1, hwi:2.0},
  "Bolivia":            {conscription:0, milVeto:0, milImpunity:1, milCrimePolice:1, milEco:1, hwi:2.6},
  "Cuba":               {conscription:1, milVeto:1, milImpunity:0, milCrimePolice:0, milEco:1, hwi:19.6},
  "Honduras":           {conscription:0, milVeto:0, milImpunity:1, milCrimePolice:1, milEco:1, hwi:0.6},
  "Guatemala":          {conscription:1, milVeto:0, milImpunity:1, milCrimePolice:1, milEco:1, hwi:0.8},
  "El Salvador":        {conscription:1, milVeto:0, milImpunity:1, milCrimePolice:1, milEco:1, hwi:2.0},
  "Nicaragua":          {conscription:0, milVeto:0, milImpunity:1, milCrimePolice:1, milEco:1, hwi:8.0},
  "Paraguay":           {conscription:1, milVeto:0, milImpunity:1, milCrimePolice:null, milEco:0, hwi:0.5},
  "Uruguay":            {conscription:0, milVeto:0, milImpunity:0, milCrimePolice:1, milEco:0, hwi:15.0},
  "Haiti":              {conscription:0, milVeto:null, milImpunity:null, milCrimePolice:0, milEco:0, hwi:null},
  "Dominican Republic": {conscription:0, milVeto:0, milImpunity:1, milCrimePolice:null, milEco:0, hwi:0.3},
  "Jamaica":            {conscription:0, milVeto:0, milImpunity:0, milCrimePolice:1, milEco:0, hwi:0.4},
  "Trinidad and Tobago":{conscription:0, milVeto:0, milImpunity:1, milCrimePolice:0, milEco:0, hwi:null},
};

const LIVE_MIL_WEIGHT = {
  coup:1.2,
  purge:0.95,
  coup_proofing:0.75,
  conflict:1.0,
  oc:1.0,
  protest:0.78,
  reform:0.45,
  coop:0.28,
  aid:0.24,
  exercise:0.18,
  peace:0.12,
  other:0.35
};
const LIVE_SALIENCE_WEIGHT = { high:1.0, medium:0.68, low:0.38 };

const ACLED_LEVEL_COLOR={'Extreme':'var(--coup)','Very High':'var(--purge)','High':'var(--conflict)','Turbulent':'var(--purge)','Low':'var(--text-muted)'};

const COUNTRY_LABELS = {76:["Brazil",[-52,-14]],170:["Colombia",[-74,4.5]],484:["Mexico",[-104,24]],862:["Venezuela",[-65,7]],32:["Argentina",[-64,-36]],604:["Peru",[-75,-9]],152:["Chile",[-70,-35]]};

// ── COUNTRY MAP CENTERS ──────────────────────────────────────
const COUNTRY_MAP_CONFIG = {
  "Brazil":      {center:[-14,-51],zoom:4}, "Colombia":    {center:[4.5,-74],zoom:5},
  "Mexico":      {center:[24,-102],zoom:5}, "Venezuela":   {center:[8,-66],zoom:6},
  "Chile":       {center:[-33,-71],zoom:4}, "Argentina":   {center:[-38,-65],zoom:4},
  "Peru":        {center:[-9,-75], zoom:5}, "Ecuador":     {center:[-2,-78], zoom:6},
  "Bolivia":     {center:[-17,-64],zoom:6}, "Cuba":        {center:[22,-80], zoom:6},
  "Honduras":    {center:[15,-87], zoom:7}, "Guatemala":   {center:[15.5,-90],zoom:7},
  "El Salvador": {center:[13.8,-88.9],zoom:8},"Nicaragua": {center:[12.8,-85.2],zoom:7},
  "Paraguay":    {center:[-23,-58],zoom:6}, "Uruguay":     {center:[-33,-56],zoom:7},
  "Haiti":              {center:[18.9,-72.3],zoom:8},
  "Dominican Republic": {center:[18.7,-70.2],zoom:8},
  "Panama":             {center:[8.5,-80],zoom:7},
  "Costa Rica":         {center:[9.75,-83.7],zoom:7},
  "Jamaica":            {center:[18.1,-77.3],zoom:9},
  "Trinidad and Tobago":{center:[10.7,-61.2],zoom:9},
  "Guyana":             {center:[5,-59],zoom:6},
  "Suriname":           {center:[4,-56],zoom:7},
  "Belize":             {center:[17.25,-88.8],zoom:8}
};

// ── KEY POSITIONS (title → name) ─────────────────────────────
const COUNTRY_POSITIONS = {
  "Brazil":      [{t:"President",          n:"Luiz Inácio Lula da Silva"},
                  {t:"Min. of Defence",     n:"José Múcio Monteiro"},
                  {t:"Army Commander",      n:"Gen. Tomás Paiva"},
                  {t:"Navy Commander",      n:"Adm. Marcos Sampaio Olsen"}],
  "Colombia":    [{t:"President",           n:"Gustavo Petro"},
                  {t:"Min. of Defence",     n:"Iván Velásquez Gómez"},
                  {t:"Armed Forces Cmdr",   n:"Gen. Helder Giraldo Bonilla"},
                  {t:"Army Commander",      n:"Gen. Luis Ospina Gutiérrez"}],
  "Mexico":      [{t:"President",           n:"Claudia Sheinbaum"},
                  {t:"Sec. of Defence (SEDENA)",n:"Gen. Ricardo Trevilla Trejo"},
                  {t:"Sec. of Navy (SEMAR)", n:"Adm. Raymundo Morales Ángeles"},
                  {t:"Nat. Guard Commander", n:"Gen. Crisóforo Lazo Vieyra"}],
  "Venezuela":   [{t:"Acting President",     n:"Delcy Rodríguez"},
                  {t:"Former President",    n:"Nicolás Maduro (US custody)"},
                  {t:"Min. of Defence",     n:"Gen. Vladimir Padrino López"},
                  {t:"CEOFANB Commander",   n:"Gen. Domingo Hernández Lárez"},
                  {t:"DGCIM Director",      n:"Gen. Iván Hernández Dala"}],
  "Chile":       [{t:"President",           n:"[verify — Boric term ended Mar 11, 2026]"},
                  {t:"Min. of National Defence",n:"[verify — new cabinet Mar 2026]"},
                  {t:"Army Commander",      n:"Gen. Javier Iturriaga del Campo"},
                  {t:"Joint Chiefs Chair",  n:"Gen. Rodrigo Álvarez Valdés"}],
  "Argentina":   [{t:"President",           n:"Javier Milei"},
                  {t:"Min. of Defence",     n:"Luis Petri"},
                  {t:"Joint General Staff", n:"Gen. Xavier Julián Isaac"},
                  {t:"Army Commander",      n:"Gen. Carlos Vittori"}],
  "Peru":        [{t:"President",           n:"Dina Boluarte"},
                  {t:"Min. of Defence",     n:"Walter Astudillo Castillo"},
                  {t:"Joint Command Chair", n:"Adm. Javier Enrique Moreno"},
                  {t:"Army Commander",      n:"Gen. Óscar Rubén Ugarte"}],
  "Ecuador":     [{t:"President",           n:"Daniel Noboa"},
                  {t:"Min. of Defence",     n:"Gian Carlo Loffredo Ridolfi"},
                  {t:"Armed Forces Cmdr",   n:"Gen. Víctor Zapata Álvarez"},
                  {t:"Army Commander",      n:"Gen. Pablo Romero Vega"}],
  "Bolivia":     [{t:"President",           n:"[verify — elections held Aug 2025]"},
                  {t:"Min. of Defence",     n:"[verify — new government 2025]"},
                  {t:"Armed Forces Cmdr",   n:"Gen. José Wilson Sánchez"},
                  {t:"Army Commander",      n:"Gen. Marco Antonio Vizcarra"}],
  "Cuba":        [{t:"President / First Sec.",n:"Miguel Díaz-Canel"},
                  {t:"Min. of FAR (MINFAR)",n:"Gen. Álvaro López Miera"},
                  {t:"Chief of General Staff",n:"Gen. Álvaro López Miera"},
                  {t:"Min. of Interior",    n:"Gen. Lázaro Alberto Álvarez"}],
  "Honduras":    [{t:"President",           n:"[verify — elections held Nov 2025]"},
                  {t:"Sec. of Defence",     n:"[verify — new government 2026]"},
                  {t:"Armed Forces Cmdr",   n:"Gen. Héctor Guillermo Escalante"},
                  {t:"Nat. Police Director", n:"Gustavo Sánchez"}],
  "Guatemala":   [{t:"President",           n:"Bernardo Arévalo de León"},
                  {t:"Min. of National Defence",n:"Henry Skippy Barrientos"},
                  {t:"Army Commander",      n:"Gen. Marco Tulio Espinoza Jerez"},
                  {t:"Nat. Civil Police",   n:"David Pérez González"}],
  "El Salvador": [{t:"President",           n:"Nayib Bukele"},
                  {t:"Min. of Defence",     n:"René Francis Merino Monroy"},
                  {t:"Armed Forces Chief",  n:"Gen. Francisco Merino Monroy"},
                  {t:"Nat. Civil Police",   n:"Mauricio Arriaza Chicas"}],
  "Nicaragua":   [{t:"President",           n:"Daniel Ortega Saavedra"},
                  {t:"Vice President",      n:"Rosario Murillo"},
                  {t:"Min. of Defence",     n:"Martha Ruiz Sevilla"},
                  {t:"EPS Commander",       n:"Gen. Julio César Avilés Castillo"}],
  "Paraguay":    [{t:"President",           n:"Santiago Peña Palacios"},
                  {t:"Min. of Defence",     n:"Óscar González Daher Jr."},
                  {t:"Armed Forces Cmdr",   n:"Gen. Carlos Chaparro Bejarano"},
                  {t:"Nat. Police",         n:"Comm. César Cattebeke"}],
  "Uruguay":     [{t:"President",           n:"Yamandú Orsi (since Mar 2025)"},
                  {t:"Min. of National Defence",n:"José Bayardi"},
                  {t:"Army Commander",      n:"Gen. Gerardo Fregossi Ferreira"},
                  {t:"Joint Defence Staff", n:"Gen. José González Torterolo"}],
  "Haiti":              [{t:"Prime Minister",       n:"Alix Didier Fils-Aimé"},
                         {t:"Transitional Council", n:"Unelected (formed Apr 2024)"},
                         {t:"HNP Director General", n:"Rameau Normil"},
                         {t:"FAd'H Commander",      n:"Gen. Jodel Lessage"}],
  "Dominican Republic": [{t:"President",            n:"Luis Abinader"},
                         {t:"Min. of Armed Forces", n:"Carlos Luciano Díaz Morfa"},
                         {t:"Armed Forces Cmdr",    n:"Gen. Carlos Fernández Onofre"},
                         {t:"Nat. Police Director", n:"Eduardo Then"}],
  "Panama":             [{t:"President",            n:"José Raúl Mulino"},
                         {t:"Min. of Security",     n:"Frank Abrego"},
                         {t:"Canal Authority Admin",n:"Ricaurte Vásquez Morales"}],
  "Costa Rica":         [{t:"President",            n:"Rodrigo Chaves"},
                         {t:"Min. of Security",     n:"Mario Zamora Cordero"},
                         {t:"Public Force Director",n:"Luis Hernández Quesada"}],
  "Jamaica":            [{t:"Prime Minister",       n:"Andrew Holness"},
                         {t:"Min. of National Security",n:"Dr. Horace Chang"},
                         {t:"JDF Commander",        n:"Rear Adm. Antonette Wemyss-Gorman"},
                         {t:"Police Commissioner",  n:"Kevin Blake"}],
  "Trinidad and Tobago":[{t:"Prime Minister",       n:"Keith Rowley"},
                         {t:"Nat. Security Min.",   n:"Fitzgerald Hinds"},
                         {t:"TTDF Commander",       n:"Brig. Gen. Rodney Smart"},
                         {t:"Police Commissioner",  n:"Erla Harewood-Christopher"}],
  "Guyana":             [{t:"President",            n:"Irfaan Ali"},
                         {t:"Min. of Home Affairs", n:"Robeson Benn"},
                         {t:"GDF Commander",        n:"Brig. Gen. Godfrey Bess"},
                         {t:"Police Commissioner",  n:"Clifton Hicken"}],
  "Suriname":           [{t:"President",            n:"Chan Santokhi"},
                         {t:"Min. of Defence",      n:"Krishna Matwali"},
                         {t:"SNL Commander",        n:"Kenneth Amoksi"},
                         {t:"Police Chief",         n:"Humphrey Cateau"}],
  "Belize":             [{t:"Prime Minister",       n:"John Briceño"},
                         {t:"Min. of National Security",n:"Kareem Musa"},
                         {t:"BDF Commander",        n:"Brig. Gen. Azariel Loriá"},
                         {t:"Police Commissioner",  n:"Chester Williams"}]
};

// ── NEXT ELECTIONS ────────────────────────────────────────────
const COUNTRY_ELECTIONS = {
  "Brazil":      {type:"Presidential + Legislative", date:"Oct 2026",       note:"Lula eligible for re-election; military posture a central campaign issue"},
  "Colombia":    {type:"Presidential + Legislative", date:"Mar/May 2026",   note:"Petro constitutionally barred from re-election; successor's CMR posture TBD"},
  "Mexico":      {type:"No national election",       date:"Until 2030",     note:"Sheinbaum began 6-year term June 2024"},
  "Venezuela":   {type:"Constitutional mandate — required by ~Jul 2026",date:"~Jul 2026 (presidential)", note:"Following Operation Absolute Resolve (Jan 3, 2026) and Maduro's capture, Acting President Delcy Rodríguez faces a constitutionally-required election within six months (~July 2026). Political landscape is fragmented: opposition-in-exile, Rodríguez-led Chavismo, and international pressure all converging. Electoral conditions under military fragility remain highly uncertain."},
  "Chile":       {type:"Presidential + Parliamentary — Held",date:"Nov 2025 (runoff Dec)",note:"Boric term ended Mar 2026 — verify new government composition [2026]"},
  "Argentina":   {type:"Legislative midterms — Held",date:"Oct 2025",      note:"Milei's La Libertad Avanza coalition tested in midterms; presidential election Oct 2027"},
  "Peru":        {type:"Presidential + Legislative", date:"Apr 2026",       note:"Boluarte eligible; executive instability context high — election cycle begins"},
  "Ecuador":     {type:"Presidential — Held",        date:"Feb 2025",       note:"Noboa re-elected Feb 2025 (1st round); governing second term; next presidential 2029"},
  "Bolivia":     {type:"Presidential + Legislative — Held",date:"Aug 2025", note:"MAS split outcome — verify new president and military posture [2026]"},
  "Cuba":        {type:"National Assembly",          date:"2028 (est.)",    note:"Non-competitive; FAR institutional continuity the key variable"},
  "Honduras":    {type:"Presidential + Legislative — Held",date:"Nov 2025", note:"Castro re-election result — verify outcome and new cabinet [2026]"},
  "Guatemala":   {type:"Presidential",               date:"Jun 2027",       note:"Arévalo reform agenda's durability depends on 2027 outcome"},
  "El Salvador": {type:"No national election",       date:"Until 2030",     note:"Bukele re-elected Feb 2024; second term through 2030"},
  "Nicaragua":   {type:"Presidential",               date:"Nov 2026",       note:"Non-competitive; Ortega expected to continue; watch for health-related succession signals"},
  "Paraguay":    {type:"Presidential + Legislative", date:"Apr 2028",       note:"Colorado Party dominance expected to continue"},
  "Uruguay":     {type:"Departmental elections — Held",date:"May 2025",     note:"Frente Amplio performed well in departmentals; Orsi national term secure through 2030"},
  "Haiti":              {type:"Presidential (pending transition)", date:"TBD 2026", note:"No election scheduled; Transitional Presidential Council governing pending security stabilization and constitutional process. MSS mission progress is the key precondition."},
  "Dominican Republic": {type:"Presidential — Held",            date:"May 2024",   note:"Abinader re-elected with 57%; next presidential election 2028"},
  "Panama":             {type:"Presidential — Held",            date:"May 2024",   note:"Mulino elected; next presidential election 2029"},
  "Costa Rica":         {type:"Presidential",                   date:"Feb 2026",   note:"Chaves constitutionally limited to one term; elections held Feb 2026 — verify result"},
  "Jamaica":            {type:"Parliamentary — Held",           date:"Sep 2024",   note:"Holness JLP re-elected Sep 2024; next election by 2029"},
  "Trinidad and Tobago":{type:"Parliamentary — Held",           date:"Sep 2025",   note:"Rowley PNM; election due by Sep 2025 — verify outcome"},
  "Guyana":             {type:"Presidential + Parliamentary — Held",date:"2025",   note:"Ali PPP/C; next election by 2025 — verify outcome"},
  "Suriname":           {type:"National Assembly — Held",       date:"May 2025",   note:"Santokhi VHP coalition; election held May 2025 — verify outcome"},
  "Belize":             {type:"Parliamentary — Held",           date:"2025",       note:"Briceño PUP; election due 2025 — verify outcome"}
};

const SPECIAL_MONITOR_MILESTONES = {
  Colombia: {
    subtitle: 'Peace Process · Armed Conflict · CMR',
    brief: "Colombia's civil-military relations are defined by a decades-long counter-insurgency legacy and the unfinished 2016 FARC peace process. The armed forces retain significant operational autonomy acquired during 50+ years of internal conflict, which structurally constrains Petro's Total Peace agenda. Three simultaneous negotiation tracks — FARC-EMC, ELN, and paramilitary successor groups — create competing military command authorities and fragmented territorial control.",
    meta: [
      { kicker: 'Focus period', value: '2016 – present\nPost-agreement arc' },
      { kicker: 'Key dynamic',  value: 'Peace process vs. military autonomy' },
    ],
    timelineStart: 2016,
    events: [
      { id:'col-e1',  date:'2016-11-24', cat:'peace',    title:'Final FARC agreement signed',                        desc:'Revised agreement establishes JEP, requiring military officers to testify on false positives. Armed forces accept framework but resist accountability mechanisms.' },
      { id:'col-e2',  date:'2016-12-01', cat:'reform',   title:'DDR begins for 13,000 FARC combatants',             desc:'Military role shifts to territorial stabilisation. Doctrine gap exposed — counter-insurgency institutions ill-equipped for post-conflict consolidation.' },
      { id:'col-e3',  date:'2018-04-10', cat:'military', title:'Army accused of resuming false positives',           desc:'HRW documents 5 new extrajudicial killings presented as combat kills. Defence Minister orders investigation.' },
      { id:'col-e4',  date:'2019-08-29', cat:'oc',       title:'FARC-EMC declared; Márquez resurfaces',             desc:'Key FARC commanders return to armed conflict, citing non-compliance with 2016 agreement. Creates new armed actor outside the peace framework.' },
      { id:'col-e5',  date:'2019-11-15', cat:'military', title:'Army airstrike kills 8 minors in Caquetá',          desc:'Bombing of a FARC-EMC camp. Defence Minister resigns. Military operating autonomously in borderline legal territory.' },
      { id:'col-e6',  date:'2020-03-22', cat:'intl',     title:'SOUTHCOM joint ops expand under COVID',             desc:'US-Colombia counter-narcotics operations expand. Military given expanded police powers in 7 departments.' },
      { id:'col-e7',  date:'2021-05-01', cat:'political',title:'National Strike — military deployed against protests',desc:'Mass protests met with live fire. Military tasked with civilian policing, triggering ICC preliminary examination.' },
      { id:'col-e8',  date:'2022-08-07', cat:'political',title:'Petro inaugurated; Velásquez named Defence Minister',desc:'First civilian critic of military in the post. Three generals and army commander retire within 30 days.' },
      { id:'col-e9',  date:'2022-10-13', cat:'military', title:'11 generals removed — deepest purge since 1957',    desc:'Rotation accelerates promotion of officers with professional rather than counter-insurgency profiles.' },
      { id:'col-e10', date:'2023-02-20', cat:'peace',    title:'ELN peace talks open in Havana',                    desc:'Fifth round of talks. Military High Command publicly expresses reservations about ceasefire scope.' },
      { id:'col-e11', date:'2023-10-05', cat:'intl',     title:'US suspends $90M FMF over human rights',            desc:'Leahy Law restrictions on three army brigades. SOUTHCOM ops continue separately, creating parallel US-military channels.' },
      { id:'col-e12', date:'2024-02-08', cat:'peace',    title:'FARC-EMC ceasefire collapses',                      desc:'Estado Mayor Central cites non-compliance. Southwest Command resumes full offensive posture after 14-month pause.' },
      { id:'col-e13', date:'2025-01-15', cat:'peace',    title:'ELN ceasefire collapses',                           desc:'Sixth round of Havana talks breaks down. Northern Command reauthorized for offensive operations.' },
      { id:'col-e14', date:'2025-03-04', cat:'oc',       title:'FARC-EMC fractures into two factions',              desc:'EMC/Mordisco split creates ambiguity over negotiating partners. Army begins dual posture: ops vs Mordisco, talks with EMC.' },
    ],
    keyData: [
      { name: 'FARC ex-combatants', value: '13,202', sub: 'enrolled in DDR · 2016' },
      { name: 'Reincorporated',     value: '~3,900',  sub: 'civilian returnees · 2024' },
      { name: 'FARC-EMC strength',  value: '~4,800',  sub: 'active combatants · 2025' },
      { name: 'Ex-combatant killings', value: '390+', sub: 'since agreement · 2025' },
    ],
  },
  Venezuela: {
    subtitle: 'FANB Structure · Authoritarian CMR · Succession',
    brief: "Venezuela represents the region's most advanced case of civil-military fusion. The Bolivarian Armed Forces (FANB) are structurally integrated into the economy, intelligence architecture, and political legitimation of the regime. The January 2026 Operation Absolute Resolve — the arrest of President Maduro by opposition forces and his transfer to US custody — creates an acute succession crisis with no precedent in SENTINEL's monitoring period.",
    meta: [
      { kicker: 'Focus period', value: '2013 – present\nMaduro era & beyond' },
      { kicker: 'Key dynamic',  value: 'Military as regime pillar · succession crisis' },
    ],
    timelineStart: 2016,
    events: [
      { id:'ven-e1', date:'2017-04-19', cat:'military',  title:'Military loyalty oath to Maduro — officer corps public pledge', desc:'Following mass protests. Padrino López leads ceremony. Marks militarization of regime survival strategy.' },
      { id:'ven-e2', date:'2018-05-20', cat:'political', title:'Maduro re-elected — international non-recognition',            desc:'FANB provides electoral security. US, EU, Lima Group reject results.' },
      { id:'ven-e3', date:'2019-01-23', cat:'political', title:'Guaidó declares interim presidency — coup attempt fails',      desc:'Military refuses to back Guaidó despite US recognition. Padrino remains loyal. Marks limits of opposition strategy.' },
      { id:'ven-e4', date:'2020-03-01', cat:'oc',        title:'FANB-colectivo-Tren de Aragua integration documented',        desc:'US Treasury sanctions FANB generals with direct cartel ties. Military economic enterprises (CAMIMPEG) expand.' },
      { id:'ven-e5', date:'2023-07-28', cat:'political', title:'Maduro claims re-election amid mass fraud allegations',        desc:'Results disputed internationally. Armed forces maintain loyalty. Opposition candidate Edmundo González wins by independent tally.' },
      { id:'ven-e6', date:'2025-01-10', cat:'political', title:'Maduro transferred to US custody — Operation Absolute Resolve',desc:'Opposition coalition seizes Caracas, arrests Maduro. Rodríguez sworn in as President. FANB High Command remains in place.' },
      { id:'ven-e7', date:'2025-03-17', cat:'political', title:'Maduro federal detention hearing in New York',                desc:'First appearance before US judge. Charges include narco-terrorism. FANB generals monitor Rodríguez closely.' },
    ],
    keyData: [
      { name: 'FANB active personnel', value: '~160K',  sub: 'army, navy, air, NG · 2024' },
      { name: 'FANB generals',          value: '2,000+', sub: 'coup-proofing legacy' },
      { name: 'Colectivos',             value: '~15K',   sub: 'armed pro-regime militias' },
      { name: 'GDP contraction (2014–23)', value: '−80%', sub: 'constant USD' },
    ],
  },
  'El Salvador': {
    subtitle: 'Régimen de Excepción · Civil-Military Fusion · CECOT',
    brief: "El Salvador represents a textbook case of democratic backsliding through civil-military fusion. Unlike classical coups, Bukele's consolidation proceeds via managed elections — enabled by judicial packing that reversed constitutional term limits — while using the military as a visible loyalty instrument and domestic enforcement mechanism. The February 2020 Legislative Assembly occupation was the defining inflection point.",
    meta: [
      { kicker: 'Focus period', value: '2020 – present\nBukele consolidation' },
      { kicker: 'Key dynamic',  value: 'Civil-military fusion via Régimen' },
    ],
    timelineStart: 2016,
    events: [
      { id:'sv-e1', date:'2019-06-01', cat:'political', title:'Bukele inaugurated — begins military-adjacent posture',    desc:'Cabinet includes former military figures. Security policy emphasizes visibility of armed forces.' },
      { id:'sv-e2', date:'2020-02-09', cat:'military',  title:'Bukele enters Assembly with armed soldiers — loyalty oath', desc:'Officers publicly pledge loyalty to president. Constitutional crisis: military refuses to enforce legislative limits on executive.' },
      { id:'sv-e3', date:'2021-05-01', cat:'political', title:'Bukele-controlled Assembly removes Supreme Court magistrates',desc:'Judicial packing removes institutional check. Plan announced to double army from 20K to 40K by 2026.' },
      { id:'sv-e4', date:'2022-03-27', cat:'military',  title:'Régimen de Excepción declared — mass arrest campaign',      desc:'Following 80-homicide weekend. Military and police begin mass arrests. Suspension of due process rights.' },
      { id:'sv-e5', date:'2023-02-01', cat:'military',  title:'CECOT mega-prison opens — military operates security',       desc:'Designed for 40,000 detainees. Military handles transport and perimeter. Military discipline applied to civilians.' },
      { id:'sv-e6', date:'2024-02-04', cat:'political', title:'Bukele re-elected with 85% — second term begins June 2024',  desc:'Despite constitutional ban on consecutive terms, reversed by packed court. No major military dissent recorded.' },
      { id:'sv-e7', date:'2025-03-16', cat:'intl',      title:'252 Venezuelan deportees arrive at CECOT under Trump deal',  desc:'US pays $6M/year. Deportees later report systematic torture per HRW report (Nov 2025).' },
      { id:'sv-e8', date:'2025-05-12', cat:'military',  title:'Military deployed to disperse peaceful protests',           desc:'First post-civil war use of armed forces against civil society. Heinrich Böll Stiftung documents cases.' },
      { id:'sv-e9', date:'2025-07-31', cat:'political', title:'Constitutional reform: indefinite re-election, 6-year terms', desc:'Assembly approves 57–3: abolishes runoffs, moves elections to 2027. Constitutional order restructured.' },
      { id:'sv-e10',date:'2026-03-27', cat:'political', title:'GIPES presents to CIDH: 504 in-custody deaths under régimen', desc:'Findings of crimes against humanity submitted to Inter-American Commission. 48th régimen extension.' },
    ],
    keyData: [
      { name: 'Régimen detentions',  value: '85K+',  sub: 'total since Mar 2022' },
      { name: 'In-custody deaths',   value: '504',   sub: 'per GIPES · Mar 2026' },
      { name: 'CECOT capacity',      value: '40,000',sub: 'mega-prison · opened 2023' },
      { name: 'Homicide rate (2023)', value: '2.4/100K', sub: 'vs 103/100K in 2015' },
    ],
  },
  Mexico: {
    subtitle: 'SEDENA Militarization · Cartel Wars · FTO Designations',
    brief: "Mexico presents the region's most complex civil-military case: deep structural militarization under a formally democratic civilian government that has not experienced a coup. The officer corps has not asserted political preferences but has been the consistent beneficiary of institutional expansion. The Sheinbaum administration has deepened the AMLO-era model: in July 2025, SEDENA was formally granted national security intelligence authority, and the National Guard was transferred to SEDENA command.",
    meta: [
      { kicker: 'Focus period', value: '2006 – present\nMilitarization arc' },
      { kicker: 'Key dynamic',  value: 'Structural militarization under civilian rule' },
    ],
    timelineStart: 2016,
    events: [
      { id:'mx-e1', date:'2019-01-01', cat:'reform',   title:'AMLO creates National Guard — civilian name, military personnel', desc:'Constitutionally civilian in name only. Built from military cadre. Marks start of institutional re-militarization under new labels.' },
      { id:'mx-e2', date:'2022-09-05', cat:'reform',   title:'National Guard formally transferred to SEDENA',                  desc:'Military takes AIFA airport, Tren Maya, ports, customs. Mexico has no nationwide civilian police force.' },
      { id:'mx-e3', date:'2024-06-01', cat:'political', title:'Sheinbaum takes office — deepens AMLO militarization model',   desc:'New SEDENA / SEMAR chiefs appointed Sep 2024. Maintains and expands military institutional roles.' },
      { id:'mx-e4', date:'2024-09-12', cat:'oc',       title:'Sinaloa civil war begins — El Mayo transferred to US',          desc:'Chapitos faction hands Zambada to US. Cartel splits: La Mayiza vs Chapitos. 2,197 homicides in Sinaloa state.' },
      { id:'mx-e5', date:'2025-02-06', cat:'intl',     title:'Trump designates 6 Mexican cartels as FTOs',                    desc:'Sovereignty crisis. Sheinbaum deploys 10K NG to border to preempt tariffs. DEA access restricted.' },
      { id:'mx-e6', date:'2025-07-01', cat:'reform',   title:'SEDENA granted national security intelligence authority',        desc:'Legislative reform. Military now authorized to generate and act on national security intelligence without civilian co-lead.' },
      { id:'mx-e7', date:'2026-02-22', cat:'military', title:'El Mencho (CJNG) killed in joint SEDENA/SEMAR operation',       desc:'US JITC-CC intelligence and planning support. 25 National Guard members killed. Largest cartel takedown in years.' },
    ],
    keyData: [
      { name: 'Active military',       value: '~277K', sub: 'SEDENA + SEMAR · 2025' },
      { name: 'National Guard (SEDENA)', value: '~120K', sub: 'formerly civilian mandate' },
      { name: 'Homicides (2025)',       value: '23,374',sub: '−30% vs 2024 · 17.5/100K' },
      { name: 'Cartel HVTs to US',      value: '93',    sub: 'transferred in 12 months' },
    ],
  },
};

// ── WHAT TO WATCH ─────────────────────────────────────────────
const COUNTRY_WATCH = {
  "Brazil":      "Monitor civil-military normalization after Bolsonaro-era politicization; Army Commander Paiva's posture heading into the 2026 election cycle is the key CMR indicator.",
  "Colombia":    "Track ELN negotiation rounds and EMC escalation simultaneously; the tension between Petro's Total Peace doctrine and military operational doctrine is the defining friction point.",
  "Mexico":      "CJNG leader El Mencho killed Feb 22 by SEDENA with US intelligence; 12 US Green Berets authorized at Mexican bases Feb 27. Monitor CJNG successor dynamics and whether Sheinbaum's deepened US military cooperation becomes institutionalized — or triggers backlash from sovereignty-focused sectors of the officer corps.",
  "Venezuela":   "CRITICAL WATCH — Post-Operation Absolute Resolve (Jan 3, 2026): Monitor FANB cohesion under Acting President Rodríguez, progress of constitutionally-required elections (~Jul 2026), DGCIM officer purges, colectivo mobilisation, and international recognition dynamics. Maduro's arraignment in New York is live. The six-month transition window is the most consequential CMR crisis in the hemisphere.",
  "Chile":       "The post-November 2025 election government took office March 11, 2026 — the new administration's stance on Pinochet-era accountability, the military's 2019 human rights liability, and defence budget direction are the key early CMR indicators to track.",
  "Argentina":   "Milei's defense budget cuts and his relationship with a historically politicized officer corps; 2025 midterms will determine whether austerity reforms proceed.",
  "Peru":        "VRAEM military operations are escalating while Boluarte faces active human rights proceedings; monitor whether the officer corps is insulated from or implicated in those cases.",
  "Ecuador":     "US-Ecuador joint military operation launched March 3 (Operation Southern Spear); IHL violation allegations against joint forces are live. Monitor whether US advisory embed becomes permanent, civilian judicial oversight of military operations, and ACHR proceedings over alleged torture and arbitrary detention.",
  "Bolivia":     "The Arce-Morales split in MAS tests military neutrality; any faction that secures military backing in the succession contest will effectively control the state.",
  "Cuba":        "Economic collapse and unprecedented 2021–2024 emigration are straining FAR institutional capacity — monitor for any public expressions of dissent within the officer corps.",
  "Honduras":    "The Hernández narco-state legacy and Castro's reform resistance define the civil-military landscape; November 2025 elections could return coup-era affiliated actors.",
  "Guatemala":   "Arévalo's ability to subordinate military intelligence to civilian oversight — specifically the Directorate of Military Intelligence (DIM) — is the structural test of his government.",
  "El Salvador": "Estado de excepción hit 4 years March 27 (49th extension); 91,650+ detained, 504 deaths in custody, FAES military role in policing extended through Dec 2026. Watch for any judicial or international accountability mechanism and whether the US-Bukele alignment survives any shift in Washington's CECOT posture.",
  "Nicaragua":   "Economic deterioration and emigration are the key destabilizers; monitor for generational tensions in the EPS officer corps as post-Ortega succession dynamics begin.",
  "Paraguay":    "EPP guerrilla activity in the north and Triple Frontera OC operations are the primary drivers of military domestic deployment — and documented corruption.",
  "Uruguay":     "Benchmark case for civilian control — watch for any changes to peacekeeping commitments under Orsi and whether the defense reform agenda continues.",
  "Haiti":              "CRITICAL — MSS formally transitioned to Gang Suppression Force (GSF) March 17; 215 Kenyan police withdrew, Chad-led replacement force arriving summer 2026. Monitor GSF mandate execution, HNP reconstruction progress, and whether the Transitional Council produces a credible electoral timeline given gang control of 85%+ of Port-au-Prince.",
  "Dominican Republic": "Haiti border management and military role in wall construction — monitor whether the security-driven expansion of military domestic roles sets precedents for institutional autonomy beyond the current civilian oversight framework.",
  "Panama":             "Darién Gap narco-migration crisis is securitizing the border zone absent a formal army; monitor civilian force capacity and US SOUTHCOM engagement under canal sovereignty tensions with Trump administration.",
  "Costa Rica":         "Rising gang violence and cartel expansion from Nicaragua and Panama — monitor whether political pressure to militarize the border erodes Costa Rica's constitutionally unarmed tradition and what the Feb 2026 election outcome means for security doctrine.",
  "Jamaica":            "Zone of Special Operations (ZOSO) normalization — monitor whether joint military-police operations become a permanent institutional feature and their effect on civil-military accountability and human rights norms.",
  "Trinidad and Tobago":"Post-Maduro Venezuela narco-trafficking export pressure on T&T's maritime corridor — key Caribbean SENTINEL monitoring point. Eastern Caribbean drug seizures up 34% Q1 2026; SOUTHCOM surge ongoing.",
  "Guyana":             "Venezuela's Essequibo territorial claim and oil-sector security are driving the first significant GDF expansion in decades. US and Brazil security partnerships are reshaping the strategic posture; monitor for any Venezuelan provocation post-Rodríguez transition.",
  "Suriname":           "The Bouterse legacy and the SNL's institutional memory of political rule — whether democratic consolidation under Santokhi is durable. The narco-transit network's political penetration is the key governance risk.",
  "Belize":             "Guatemala-Belize ICJ process is the primary strategic risk; watch for any escalation in territorial friction. BDF capacity-building and US SOUTHCOM engagement are the key CMR variables."
};

// ── MILITARY MISSIONS / ROLES BY COUNTRY ─────────────────────
// Each entry: array of {role, status} objects
// status: "primary" | "active" | "expanded" | "controversial" | "routine"
const COUNTRY_MISSIONS = {
  "Brazil":      [{role:"External defence / sovereignty",status:"primary"},{role:"Amazon border patrol (Operação Ágata)",status:"active"},{role:"UN peacekeeping (MINUSTAH legacy, MONUSCO)",status:"active"},{role:"Domestic security (favela ops, Bolsonaro era)",status:"controversial"},{role:"Infrastructure / strategic projects",status:"routine"}],
  "Colombia":    [{role:"Counter-insurgency (ELN, FARC-EMC)",status:"primary"},{role:"Counter-narcotics / Plan Colombia successor",status:"active"},{role:"DDR / Total Peace implementation",status:"active"},{role:"Border security (Venezuela, Ecuador)",status:"active"},{role:"US joint ops / JIATF-South",status:"active"}],
  "Mexico":      [{role:"Counter-narcotics / cartel suppression",status:"primary"},{role:"National Guard (domestic police substitute)",status:"expanded"},{role:"Border enforcement / migration containment",status:"expanded"},{role:"Infrastructure control (AIFA, ports, Tren Maya)",status:"controversial"},{role:"Intelligence (SEDENA mandate since Jul 2025)",status:"expanded"}],
  "Venezuela":   [{role:"Internal regime security / coup-proofing",status:"primary"},{role:"Colectivo coordination (pre-Jan 2026)",status:"controversial"},{role:"Illicit mining protection (Arco Minero)",status:"controversial"},{role:"Tren de Aragua-FANB nexus (documented)",status:"controversial"},{role:"Transition / loyalty posture (post-Jan 2026)",status:"active"}],
  "Argentina":   [{role:"External defence / sovereignty (Malvinas)",status:"primary"},{role:"UN peacekeeping (UNFICYP, MINUSTAH)",status:"active"},{role:"Antarctic territorial presence",status:"routine"},{role:"Disaster relief / civil emergency",status:"routine"}],
  "Chile":       [{role:"External defence / sovereignty",status:"primary"},{role:"UN peacekeeping",status:"active"},{role:"Northern border security (migration)",status:"active"},{role:"2019 social uprising response",status:"controversial"}],
  "Peru":        [{role:"VRAEM counter-narcotics / Sendero Luminoso",status:"primary"},{role:"Illegal mining crackdowns (La Pampa)",status:"active"},{role:"Border security",status:"routine"},{role:"Internal order support (Boluarte protests)",status:"controversial"}],
  "Ecuador":     [{role:"Internal armed conflict framework (Jan 2024–)",status:"primary"},{role:"Anti-gang prison operations",status:"active"},{role:"Border security (Colombia / Peru)",status:"active"},{role:"Maritime drug interdiction",status:"active"}],
  "Bolivia":     [{role:"Counter-narcotics (coca eradication)",status:"primary"},{role:"Border patrol (Chile, Brazil, Argentina)",status:"routine"},{role:"Internal political role (2019 crisis)",status:"controversial"},{role:"Resource security (lithium, gas)",status:"active"}],
  "Cuba":        [{role:"Regime security / FAR political pillar",status:"primary"},{role:"GAESA economic empire (tourism, retail)",status:"primary"},{role:"Civil militia (MTT) mobilisation",status:"active"},{role:"Intelligence / counterintelligence (DGI)",status:"active"}],
  "Honduras":    [{role:"Internal security / anti-gang",status:"primary"},{role:"Border patrol",status:"routine"},{role:"US base hosting (Soto Cano / JTF-Bravo)",status:"active"},{role:"Documented narco-trafficking collusion",status:"controversial"}],
  "Guatemala":   [{role:"Counter-narcotics / border security",status:"primary"},{role:"Internal security / Ixil area operations",status:"active"},{role:"Intelligence (DIM) — civilian oversight disputed",status:"controversial"}],
  "El Salvador": [{role:"Régimen de Excepción mass arrests",status:"primary"},{role:"Prison security / CECOT operations",status:"primary"},{role:"Protest suppression (May 2025)",status:"controversial"},{role:"Joint patrol with National Police",status:"active"}],
  "Nicaragua":   [{role:"Regime security / EPS political role",status:"primary"},{role:"Border patrol",status:"routine"},{role:"Civil society repression (2018–present)",status:"controversial"}],
  "Paraguay":    [{role:"EPP counter-guerrilla (north)",status:"primary"},{role:"Triple Frontera OC interdiction",status:"active"},{role:"Border patrol (Brazil, Argentina, Bolivia)",status:"routine"}],
  "Uruguay":     [{role:"UN peacekeeping (major contributor)",status:"primary"},{role:"External defence",status:"routine"},{role:"Disaster relief",status:"routine"}],
  "Haiti":       [{role:"Gang containment / UN Gang Suppression Force (GSF, from Mar 2026)",status:"primary"},{role:"MSS transition / Kenyan withdrawal (Mar 17)",status:"active"},{role:"UN mission support (BINUH)",status:"active"},{role:"Civilian-military relations severely strained",status:"controversial"}],
  "Dominican Republic": [{role:"External defence",status:"primary"},{role:"Border security (Haiti)",status:"active"},{role:"Counter-narcotics",status:"active"}],
  "Panama":      [{role:"Canal security",status:"primary"},{role:"Counter-narcotics (no standing army)",status:"active"},{role:"Border patrol (Darién)",status:"active"}],
  "Costa Rica":  [{role:"No standing army (1948 constitution)",status:"primary"},{role:"Border police / OIJ",status:"routine"}],
  "Jamaica":     [{role:"Anti-gang operations (JDF)",status:"primary"},{role:"Maritime patrol",status:"routine"},{role:"States of emergency (Zones of Special Operations)",status:"active"}],
  "Trinidad and Tobago": [{role:"Counter-narcotics / maritime patrol",status:"primary"},{role:"Gang suppression (TTPS/TDF)",status:"active"}],
  "Guyana":      [{role:"Border security (Venezuela territorial claim)",status:"primary"},{role:"Oil field protection",status:"active"},{role:"Counter-narcotics",status:"routine"}],
  "Suriname":    [{role:"Border security",status:"primary"},{role:"Counter-narcotics",status:"routine"}],
  "Belize":      [{role:"Border security (Guatemala territorial claim)",status:"primary"},{role:"UK garrison support (historical)",status:"routine"}],
};

// ── COUNTRY PROFILE DATA ─────────────────────────────────────
const COUNTRY_PROFILES = {
  "Brazil":      { capital:"Brasília",      regime:"Federal Republic",        hog:"Luiz Inácio Lula da Silva", cmrStatus:"Stable",        cmrClass:"cp-cmr-stable",       gdpPct:"1.3%",  branches:"Army · Navy · Air Force · EMFA",  note:"Brazil maintains the strongest formal civilian control architecture in South America. The 1988 constitution subordinates the armed forces to civilian authority, though institutional memory of the 1964–1985 military government remains. Ongoing debates center on the military's expanded role under Bolsonaro (2019–2022) and subsequent normalization efforts under Lula. The Escola Superior de Guerra and defense ministry reforms are key SSR indicators to watch." },
  "Mexico":      { capital:"Mexico City",   regime:"Federal Republic",        hog:"Claudia Sheinbaum",         cmrStatus:"Strained",       cmrClass:"cp-cmr-strained",     gdpPct:"0.6%",  branches:"Army (SEDENA) · Navy (SEMAR) · Air Force", note:"Mexico has experienced significant militarization since 2006's Calderón drug war deployment. Under AMLO and now Sheinbaum, the armed forces control the National Guard, oversee infrastructure megaprojects (Tren Maya, Felipe Ángeles Airport), and run the customs agency. This expansion of military economic roles raises structural concerns for democratic civilian control and civil-military theory.", special:true, specialId:"cp-mexico" },
  "Colombia":    { capital:"Bogotá",        regime:"Presidential Republic",   hog:"Gustavo Petro",             cmrStatus:"Complex",        cmrClass:"cp-cmr-strained",     gdpPct:"3.3%",  branches:"Army · Navy · Air Force · Police (National)", note:"Colombia's civil-military environment is defined by its ongoing internal armed conflict and the Petro government's 'Total Peace' doctrine. The armed forces maintain strong institutional cohesion but face friction with a left-wing executive who was himself a former M-19 guerrilla. U.S. cooperation at $461M annually shapes doctrine, equipment, and counter-narcotics strategy.", special:true, specialId:"cp-colombia" },
  "Venezuela":   { capital:"Caracas",       regime:"Transitional / Post-Maduro", hog:"Delcy Rodríguez (acting)",cmrStatus:"Crisis",         cmrClass:"cp-cmr-crisis",       gdpPct:"est. 4%",branches:"FANB: Army · Navy · Air Force · Guard · Militia", note:"As of January 2026, Venezuela is in a post-Maduro transition following Operation Absolute Resolve (Jan 3, 2026), in which US special operations forces captured Nicolás Maduro in Caracas. Maduro was arraigned in New York on narco-terrorism charges Jan 5; Acting President Delcy Rodríguez was sworn in the same day. FANB cohesion is fragile — DGCIM detained 12+ officers suspected of cooperating with US forces (Jan 6). The constitutional six-month window requires elections by ~July 2026. Venezuela is the most critical CMR monitoring case in the hemisphere.", special:true, specialId:"cp-venezuela" },
  "Chile":       { capital:"Santiago",      regime:"Presidential Republic",   hog:"Gabriel Boric",             cmrStatus:"Stable",         cmrClass:"cp-cmr-stable",       gdpPct:"2.0%",  branches:"Army · Navy · Air Force · Carabineros",   note:"Chile has the most professionalized armed forces in South America outside Brazil. Civilian control is robust following the post-Pinochet transition, though the 2019 social uprising and the security forces' human rights abuses during it created ongoing civil-military tension. The Boric government is pursuing accountability for human rights violations while maintaining a cooperative relationship with the institution." },
  "Argentina":   { capital:"Buenos Aires",  regime:"Federal Republic",        hog:"Javier Milei",              cmrStatus:"Stable",         cmrClass:"cp-cmr-stable",       gdpPct:"0.5%",  branches:"Army · Navy · Air Force · GNA · PNA",    note:"Argentina's military has been under firm civilian control since the restoration of democracy in 1983, shaped by the accountability process for Dirty War crimes (1976–1983). The Milei government has proposed deep cuts to defense spending as part of its austerity program. Argentina's defense posture is defensive and regionally cooperative; UNASUR-era multilateral frameworks remain a reference point." },
  "Peru":        { capital:"Lima",          regime:"Presidential Republic",   hog:"Dina Boluarte",             cmrStatus:"Strained",        cmrClass:"cp-cmr-strained",     gdpPct:"1.2%",  branches:"Army · Navy · Air Force · PNP",          note:"Peru has experienced severe executive instability — six presidents in six years — creating growing military institutional influence by default. The Boluarte government, which came to power following Castillo's failed self-coup in December 2022, has relied heavily on the security forces to suppress protests. Illegal mining and narco-trafficking in the VRAEM continue to drive military domestic deployment." },
  "Ecuador":     { capital:"Quito",         regime:"Presidential Republic",   hog:"Daniel Noboa",              cmrStatus:"Crisis",         cmrClass:"cp-cmr-crisis",       gdpPct:"2.4%",  branches:"Army · Navy · Air Force · Police",       note:"Ecuador declared an 'internal armed conflict' in January 2024 following the televised storming of TC Televisión by armed criminal groups. President Noboa militarized internal security, granting the armed forces an expanded domestic mandate. This represents a significant formal shift in civil-military roles and is one of the most important CMR developments in the region in recent years." },
  "Bolivia":     { capital:"Sucre / La Paz",regime:"Presidential Republic",   hog:"Luis Arce",                 cmrStatus:"Strained",        cmrClass:"cp-cmr-strained",     gdpPct:"1.5%",  branches:"Army · Navy (riverine) · Air Force",     note:"Bolivia experienced a contested coup/resignation crisis in November 2019 when Evo Morales fled following military 'suggestions' he resign. The subsequent Arce government and the 2021 coup attempt against Arce himself highlight the persistent vulnerability of civilian control. The military's role in resource nationalization and coca policy creates structural conflict of interest." },
  "Cuba":        { capital:"Havana",        regime:"One-party Socialist State",hog:"Miguel Díaz-Canel",        cmrStatus:"Authoritarian",  cmrClass:"cp-cmr-authoritarian",gdpPct:"est. 3.5%",branches:"FAR: Army · Navy · Air Defense · MTT",   note:"Cuba's Revolutionary Armed Forces (FAR) are the institutional backbone of the Cuban state, owning a major share of the economy through GAESA holding group (tourism, retail, remittances). The civil-military boundary is structurally fused — the party, state, and military are not meaningfully distinct at the senior command level. Post-Castro succession dynamics are a key CMR watch item." },
  "Honduras":    { capital:"Tegucigalpa",   regime:"Presidential Republic",   hog:"Xiomara Castro",            cmrStatus:"Strained",        cmrClass:"cp-cmr-strained",     gdpPct:"1.6%",  branches:"Army · Navy · Air Force · National Police",note:"Honduras has historically exhibited high military institutional autonomy, rooted in its role as a U.S. Cold War platform. The Hernández government (2014–2022) is now facing U.S. drug trafficking charges, having allegedly collaborated with cartels. Under Castro, civil-military reform efforts face significant institutional resistance. The military's constitutional mandate for internal security functions as a structural prerogative." },
  "Guatemala":   { capital:"Guatemala City",regime:"Presidential Republic",   hog:"Bernardo Arévalo",          cmrStatus:"Strained",        cmrClass:"cp-cmr-strained",     gdpPct:"0.4%",  branches:"Army · Air Force · Navy",               note:"Guatemala's military retains significant political influence, particularly via its intelligence apparatus and historical impunity for genocide-era crimes. President Arévalo, a democracy reformist, faced an extraordinary political-legal siege before and after his 2023 election, with actors tied to the military-prosecutor nexus. His government's survival and consolidation of civilian control is the central CMR story in Guatemala." },
  "El Salvador": { capital:"San Salvador",  regime:"Presidential Republic",   hog:"Nayib Bukele",              cmrStatus:"Crisis",         cmrClass:"cp-cmr-crisis",       gdpPct:"1.1%",  branches:"Army · Navy · Air Force · National Police",note:"El Salvador under Nayib Bukele represents a significant democratic backsliding case. Following the 2021 Legislative Assembly takeover by Bukele's party, the Supreme Court was packed and constitutional term limits removed. Bukele has explicitly used the military as a personal political instrument, most notoriously in the February 2020 Legislative Assembly incident. The estado de excepción anti-gang crackdown (March 2022–present) has created mass detention conditions with minimal due process.", special:true, specialId:"cp-elsalvador" },
  "Nicaragua":   { capital:"Managua",       regime:"Authoritarian Presidential",hog:"Daniel Ortega",           cmrStatus:"Authoritarian",  cmrClass:"cp-cmr-authoritarian",gdpPct:"0.6%",  branches:"Army (EPS) · National Police",          note:"Nicaragua under Ortega has constructed an authoritarian civil-military system modeled loosely on Cuba and Venezuela. The Sandinista People's Army (EPS) is institutionally subordinate to the party rather than civilian constitutional oversight. The 2018 suppression of the April uprising, in which over 300 were killed, involved coordinated military, police, and paramilitaries. Regular officer corps promotions reward loyalty over professionalism." },
  "Paraguay":    { capital:"Asunción",      regime:"Presidential Republic",   hog:"Santiago Peña",             cmrStatus:"Stable",         cmrClass:"cp-cmr-stable",       gdpPct:"1.5%",  branches:"Army · Navy · Air Force",               note:"Paraguay's military maintains moderate institutional autonomy under a formally democratic system, but the Colorado Party's 75-year near-continuous rule has created a party-military patron-client network. The eastern border region (Triple Frontera) involves military and police forces in anti-narcotics and smuggling operations, with documented corruption concerns. Paraguay has no international conflict history in the modern era." },
  "Uruguay":     { capital:"Montevideo",    regime:"Presidential Republic",   hog:"Yamandú Orsi",              cmrStatus:"Stable",         cmrClass:"cp-cmr-stable",       gdpPct:"2.0%",  branches:"Army · Navy · Air Force",               note:"Uruguay is consistently the strongest CMR case in Latin America on all civilian control metrics: lowest military spending, no internal deployment, robust accountability for dictatorship-era crimes, and professional civil-military relations. The small armed forces have a UN peacekeeping-heavy focus. Uruguay serves as a benchmark case for democratic civilian control in CMR comparative research." },
  "Haiti":              { capital:"Port-au-Prince", regime:"Transitional (Council-led)", hog:"Alix Didier Fils-Aimé (PM)", cmrStatus:"Crisis", cmrClass:"cp-cmr-crisis", gdpPct:"0.2%", branches:"HNP (police only) — no standing army", note:"Haiti has no functioning elected government since President Moïse's assassination (July 2021). An unelected Transitional Presidential Council has governed since April 2024. The Haitian National Police, severely degraded, operates alongside the US-backed Kenyan-led Multinational Security Support mission (MSS). Gang control of Port-au-Prince exceeded 85% of the capital by 2025. The Haitian Army (FAd'H), reconstituted in 2017, numbers fewer than 2,000 and is largely ineffective. Haiti is the hemisphere's most acute state fragility and security crisis, with CMR secondary to the question of whether any functional state structure can be re-established." },
  "Dominican Republic": { capital:"Santo Domingo", regime:"Presidential Republic", hog:"Luis Abinader", cmrStatus:"Stable", cmrClass:"cp-cmr-stable", gdpPct:"0.7%", branches:"Army · Navy · Air Force · National Police", note:"The Dominican Republic maintains one of the more stable civil-military relationships in the Caribbean. President Abinader (re-elected May 2024 with 57%) maintains a cooperative military posture focused on Haiti border security and counter-narcotics. The military's role in constructing a border wall and managing migrant flows has expanded its domestic infrastructure mission without triggering institutional autonomy concerns. No significant civilian control challenges." },
  "Panama":             { capital:"Panama City", regime:"Presidential Republic", hog:"José Raúl Mulino", cmrStatus:"Stable", cmrClass:"cp-cmr-stable", gdpPct:"0.8%", branches:"National Security Forces — no standing army", note:"Panama abolished its military following the 1989 US intervention (Just Cause). Security functions are performed by civilian National Security Forces. Panama's core security challenge is the Darién Gap — a major migration and narco-trafficking corridor — which has driven increasing securitization of the border zone. President Mulino, a former security minister, has taken a hardline border management approach with US support. Canal sovereignty remains the primary strategic concern and a source of US-Panama security tension under Trump." },
  "Costa Rica":         { capital:"San José", regime:"Presidential Republic", hog:"Rodrigo Chaves", cmrStatus:"Stable", cmrClass:"cp-cmr-stable", gdpPct:"0.6%", branches:"Public Force (police) — no military by constitution", note:"Costa Rica abolished its military in 1948 (Article 12, Constitution). The Public Force and border police perform all security functions. Rising organized crime activity from Central American and South American cartels, and gang expansion from neighboring countries, is straining the civilian police model. Political pressure to expand border military-style operations is increasing, though no constitutional change has occurred." },
  "Jamaica":            { capital:"Kingston", regime:"Constitutional Monarchy", hog:"Andrew Holness (PM)", cmrStatus:"Strained", cmrClass:"cp-cmr-strained", gdpPct:"1.5%", branches:"Jamaica Defence Force (JDF) · Jamaica Constabulary Force (JCF)", note:"Jamaica has the Caribbean's highest per-capita homicide rate among non-conflict states (41/100K in 2023). The Holness government has repeatedly declared Zones of Special Operations (ZOSOs) — joint military-police enforcement zones — normalizing military domestic security roles. Gang-state collusion in garrison communities (West Kingston, Spanish Town) is a long-standing structural issue. JDF capacity is increasing, with US and UK security cooperation." },
  "Trinidad and Tobago":{ capital:"Port of Spain", regime:"Parliamentary Republic", hog:"Keith Rowley (PM)", cmrStatus:"Strained", cmrClass:"cp-cmr-strained", gdpPct:"1.0%", branches:"Trinidad and Tobago Defence Force (TTDF) · TTPS", note:"Trinidad and Tobago has one of the hemisphere's highest murder rates relative to income level, driven by gang activity linked to Venezuela's narco-trafficking networks. The TTDF plays an increasing domestic security role alongside the TTPS. T&T's proximity to post-Maduro Venezuela and its historic Tren de Aragua exposure make it a key Caribbean monitoring case for transnational security threats. SOUTHCOM's Eastern Caribbean counter-narcotics surge (Feb 2025) was partly driven by T&T corridor interdiction." },
  "Guyana":             { capital:"Georgetown", regime:"Presidential Republic", hog:"Irfaan Ali", cmrStatus:"Stable", cmrClass:"cp-cmr-stable", gdpPct:"1.0%", branches:"Guyana Defence Force (GDF) · Guyana Police Force", note:"Guyana's security picture has been transformed by its emergence as a major oil producer (2019 ExxonMobil strike — 700K+ bpd by 2025). The Venezuela-Guyana Essequibo territorial dispute, revived by Maduro's 2023 referendum, drove significant defence investment and a US-Brazil security partnership framework. The GDF is small but receiving rapid equipment and training upgrades. Civil-military relations are stable under Ali; oil-sector protection is the emerging military mission." },
  "Suriname":           { capital:"Paramaribo", regime:"Presidential Republic", hog:"Chan Santokhi", cmrStatus:"Strained", cmrClass:"cp-cmr-strained", gdpPct:"1.2%", branches:"Suriname National Army (SNL) · National Police", note:"Suriname's CMR history is defined by Dési Bouterse — a military coup leader (1980, 1990) who served as president 2010–2020 and was convicted for the 1982 December Murders of 15 political opponents. President Santokhi's government represents democratic transition, but the SNL retains institutional memory of direct rule. Suriname is a significant drug transit state — its ports and airfields are used by South American cocaine networks — with documented links between narco-trafficking interests and political actors." },
  "Belize":             { capital:"Belmopan", regime:"Constitutional Monarchy", hog:"John Briceño (PM)", cmrStatus:"Stable", cmrClass:"cp-cmr-stable", gdpPct:"1.5%", branches:"Belize Defence Force (BDF) · Belize Police Department", note:"Belize has stable civil-military relations under a parliamentary system. The BDF is small (~1,500 personnel) and focuses on the Guatemala border — Belize's territorial dispute with Guatemala, which historically did not recognize Belize's full sovereignty, drove a 2019 ICJ referral. The case is before the ICJ; no active armed friction. US SOUTHCOM and UK garrison support (historically) supplement BDF capacity. Narco-trafficking through Belize's coastline and cays is the primary security challenge." }
};

// ── CMR RISK SCORE ────────────────────────────────────────────
// Event-pressure component: weighted sum of all events in store per country
// Structural component (added when V-Dem loads): mil_exec + (1-mil_constrain_norm) + coup_attempts
const CMR_TYPE_W = {coup:10,coup_proofing:7,purge:6,conflict:5,oc:4,protest:3,
                   coop:2,aid:1,exercise:1,peace:-2,reform:-3,other:0};
const CMR_SAL_M  = {high:1.5,medium:1.0,med:1.0,low:0.5};

let _cmrScores = {};   // {country: {pressure, structural, composite, label}}

function computeCmrScores() {
  const pressure = {};
  (allEvents||[]).forEach(ev => {
    const w = (CMR_TYPE_W[ev.type]||0) * (CMR_SAL_M[ev.salience]||1.0);
    pressure[ev.country] = (pressure[ev.country]||0) + w;
  });
  // Normalize pressure to 0-50 range
  const maxP = Math.max(1, ...Object.values(pressure));
  const scores = {};
  Object.entries(pressure).forEach(([c,p]) => {
    const pNorm = Math.max(0, Math.min(50, (p / maxP) * 50));
    let structural = 0;
    if (_vdemData) {
      const v = _vdemData.countries.find(x => x.country === c);
      if (v) {
        // mil_exec (0-1, higher = military in exec = worse)
        structural += (v.mil_exec || 0) * 20;
        // mil_constrain (ordinal, roughly -2 to 2, higher = more civilian control = better)
        const mcNorm = Math.max(0, Math.min(1, (v.mil_constrain + 2) / 4));
        structural += (1 - mcNorm) * 15;
        // coup_attempts (0-n, recent)
        structural += Math.min(10, (v.coup_attempts || 0) * 5);
        // polity2 (-10 to +10, lower = more autocratic = worse)
        if (v.polity2 != null) structural += Math.max(0, (10 - v.polity2) / 20 * 15);
      }
    }
    const composite = Math.round(pNorm + structural);
    const label = composite >= 60 ? 'Critical' : composite >= 40 ? 'High' : composite >= 20 ? 'Moderate' : 'Low';
    scores[c] = { pressure: Math.round(pNorm), structural: Math.round(structural), composite, label };
  });
  _cmrScores = scores;
}

function cmrScoreColor(label) {
  return label==='Critical'?'var(--coup)':label==='High'?'var(--purge)':label==='Moderate'?'var(--conflict)':'var(--reform)';
}

// ── INDICATOR DATA (V-Dem + World Bank) — lazy-loaded ─────────
let _vdemData = null, _wbData = null, _indicatorLoadStarted = false;
let _currentCpName = null;
let _cpRadarChart = null, _cpPulseChart = null;

async function loadIndicatorData() {
  if (_indicatorLoadStarted) return;
  _indicatorLoadStarted = true;
  try {
    const [vd, wb] = await Promise.all([
      fetch('data/cleaned/vdem.json').then(r => r.json()),
      fetch('data/cleaned/worldbank.json').then(r => r.json())
    ]);
    _vdemData = vd;
    _wbData = wb;
    computeCmrScores();
    // Re-render trends if a profile is currently open
    if (_currentCpName) {
      const el = document.getElementById('cp-trends-' + _currentCpName.replace(/ /g,'_'));
      if (el) el.innerHTML = renderTrends(_currentCpName);
    }
  } catch(e) { console.error('Indicator data load failed', e); }
}

function makeSvgSparkline(series, color, w, h) {
  const pts = series.filter(p => p.value != null).map(p => ({y: +p.value, x: +p.year}));
  if (pts.length < 2) return `<svg width="${w}" height="${h}"><text x="4" y="${h/2+3}" font-size="8" fill="#bbb">no data</text></svg>`;
  const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
  const minX=Math.min(...xs), maxX=Math.max(...xs);
  const minY=Math.min(...ys), maxY=Math.max(...ys);
  const rangeY = maxY - minY || 1;
  const px = x => ((x - minX) / (maxX - minX)) * w;
  const py = y => (h - 3) - ((y - minY) / rangeY) * (h - 6);
  const d = pts.map((p,i) => `${i===0?'M':'L'}${px(p.x).toFixed(1)},${py(p.y).toFixed(1)}`).join(' ');
  const areaD = d + ` L${px(pts[pts.length-1].x).toFixed(1)},${h} L${px(pts[0].x).toFixed(1)},${h} Z`;
  const lx = px(pts[pts.length-1].x), ly = py(pts[pts.length-1].y);
  return `<svg width="${w}" height="${h}" style="overflow:visible;display:block;">
    <path d="${areaD}" fill="${color}" fill-opacity="0.10" stroke="none"/>
    <path d="${d}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round"/>
    <circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2.5" fill="${color}"/>
  </svg>`;
}

function renderTrends(name) {
  if (!_vdemData && !_wbData) return '<div class="cp-trends-loading">Loading…</div>';
  const W = 180, H = 46;
  const rows = [];
  if (_vdemData) {
    const v = _vdemData.countries.find(c => c.country === name);
    if (v && v.series) {
      if (v.series.polyarchy)    rows.push(['Electoral Democracy', v.series.polyarchy,    '#1460b0', '0–1']);
      if (v.series.mil_constrain)rows.push(['Mil. Constraints on Exec.', v.series.mil_constrain, '#7a2e6e', 'ordinal']);
    }
  }
  if (_wbData) {
    const w = _wbData.countries.find(c => c.country === name);
    if (w) {
      if (w.military_expenditure_pct_gdp_series) rows.push(['Defence / GDP', w.military_expenditure_pct_gdp_series, '#c86010', '% GDP']);
      if (w.wgi_rule_of_law_series)              rows.push(['Rule of Law (WGI)', w.wgi_rule_of_law_series,              '#157550', 'score']);
    }
  }
  if (!rows.length) return '<div class="cp-trends-loading">No trend data available.</div>';
  return rows.map(([label, series, color, unit]) => {
    const spark = makeSvgSparkline(series.map(p=>({year:+p.year,value:p.value})), color, W, H);
    const latest = [...series].reverse().find(p => p.value != null);
    const latestStr = latest ? `${(+latest.value).toFixed(2)} (${latest.year})` : '—';
    return `<div class="cp-trend-item">
      <div class="cp-trend-label">${label} <span class="cp-trend-unit">${unit}</span></div>
      <div class="cp-trend-spark">${spark}</div>
      <div class="cp-trend-latest">${latestStr}</div>
    </div>`;
  }).join('');
}

function renderCountryPredictiveOutlook(name){
  const summary = getCountryPredictiveSummary(name);
  const constructs = ['regime_vulnerability','militarization','security_fragmentation']
    .map(code => getCountryRiskConstruct(name, code))
    .filter(Boolean);
  if(!summary && !constructs.length) return '';
  const militarization = constructs.find(item => item.code === 'militarization');
  const militarizationDimensions = militarization
    ? militarization.components
        .filter(item => ['military_domestic_coercion_role','military_governance_administration_role','military_economic_control_role'].includes(item.code))
        .sort((a,b) => (b.weighted_contribution || 0) - (a.weighted_contribution || 0))
    : [];
  const militarizationLabel = code => ({
    military_domestic_coercion_role: 'Domestic coercion',
    military_governance_administration_role: 'Governance administration',
    military_economic_control_role: 'Economic control'
  }[code] || code);
  const constructRows = constructs.map(item => `
    <div class="cp-stat-row">
      <span class="cp-stat-label">${item.label}</span>
      <span class="cp-stat-val" style="color:${getMonitorScoreColor(item.score)};">${formatMonitorValue(item.score) || 0}/100 <span style="color:${getMonitorTrendColor(item.trend_label)};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;">${item.trend_label || 'stable'}</span></span>
    </div>`).join('');
  const militarizationHtml = militarizationDimensions.length
    ? `<div style="display:flex;flex-direction:column;gap:6px;margin-top:12px;padding-top:10px;border-top:1px solid var(--border);">
        <div class="cp-sum-label" style="margin-bottom:0;">Militarization profile</div>
        ${militarizationDimensions.map(item => `
          <div class="cp-stat-row">
            <span class="cp-stat-label">${militarizationLabel(item.code)}</span>
            <span class="cp-stat-val" style="color:${getMonitorScoreColor(item.score)};">${formatMonitorValue(item.score) || 0}/100</span>
          </div>`).join('')}
      </div>`
    : '';
  const watchHtml = (summary?.watchpoints || []).length
    ? `<div style="display:flex;flex-direction:column;gap:6px;">${summary.watchpoints.map(item => `<div class="cp-watch-text" style="font-size:11px;">${item}</div>`).join('')}</div>`
    : '<div class="cp-watch-text">No watchpoints available yet.</div>';
  return `
    <div class="cp-h2">Predictive Outlook</div>
    <div class="cp-summary-strip" style="margin-bottom:18px;">
      <div class="cp-sum-block" style="grid-column:1 / span 2;">
        <div class="cp-sum-label">Country Outlook</div>
        <div class="cp-watch-text" style="line-height:1.7;">${summary?.summary_text || 'No predictive summary is available yet.'}</div>
      </div>
      <div class="cp-sum-block">
        <div class="cp-sum-label">Risk Layers</div>
        ${constructRows}
        ${militarizationHtml}
      </div>
      <div class="cp-sum-block">
        <div class="cp-sum-label">What To Watch</div>
        ${watchHtml}
      </div>
    </div>`;
}

// ── COUNTRY PROFILE RENDERER ──────────────────────────────────
function showCountryProfile(name) {
  document.querySelectorAll('.cp-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.country === name);
  });
  const regional   = document.getElementById('cp-regional');
  const countryDiv = document.getElementById('cp-country');
  const prof = COUNTRY_PROFILES[name];
  if (!prof) return;
  const dossierContext = getCountryPublicContext(name) || {};

  const safeId   = name.replace(/ /g, '_');
  const summary  = getCountryPredictiveSummary(name);
  const stats    = COUNTRY_STATS[name]   || { spending: '—', personnel: '—', usAid: '—' };
  const positions = Array.isArray(dossierContext.key_positions) && dossierContext.key_positions.length
    ? dossierContext.key_positions.map(item => ({
        t: item?.title || 'Position',
        n: item?.name || 'Name pending',
      }))
    : (COUNTRY_POSITIONS[name] || []);
  const hasDossierElection = dossierContext.next_election
    && dossierContext.next_election.date
    && dossierContext.next_election.date !== '1900-01-01'
    && String(dossierContext.next_election.type || '').toLowerCase() !== 'unknown';
  const election = hasDossierElection
    ? {
        type: dossierContext.next_election.type || 'Election',
        date: dossierContext.next_election.date || 'Date pending',
        note: dossierContext.next_election.note || '',
      }
    : (COUNTRY_ELECTIONS[name] || null);
  const watch    = dossierContext.country_watch || COUNTRY_WATCH[name]   || '';
  const overallRiskScore = Number(summary?.overall_risk_score) || 0;
  const overallRiskTone  = getOverallRiskTone(overallRiskScore);
  const cEvs = (allEvents || []).filter(e => matchesProfileCountryEvent(e, name)).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 12);
  const selectedEvent = cEvs[0] || null;
  const leadingConstructLabel = summary?.leading_construct_label || summary?.leading_construct || 'Monitor loading';
  const leadingTrendLabel = summary?.leading_trend || 'steady';
  const latestEventDate = selectedEvent?.date || '';
  const latestEventLabel = latestEventDate ? cpFormatCalendarDate(latestEventDate) : 'No live event';
  const profileCapital = dossierContext.capital || prof.capital || '—';
  const profileRegime = dossierContext.regime || prof.regime || '—';
  const profileCmrStatus = dossierContext.cmr_status || prof.cmrStatus || 'Stable';
  const profileCmrClass = dossierContext.cmr_class || prof.cmrClass || 'stable';
  const profileNote = dossierContext.note || prof.note || '—';
  const watchpoints = (summary?.watchpoints || []).length
    ? summary.watchpoints
    : (watch ? [watch] : ['No watchpoints available yet.']);

  // ── 1. Header ────────────────────────────────────────────────
  const cmrPillClass = String(profileCmrClass || 'stable').toLowerCase();
  const smBtn = prof.special
    ? `<button class="cp2-sm-btn" onclick="showSpecialMonitor('${name.replace(/'/g, "\\'")}')">★ Special Monitor</button>`
    : '';
  const hdrHtml = `
    <div class="cp2-hdr">
      <button class="cp2-back" onclick="showRegionalOverview()">← All Countries</button>
      <div style="margin-left:6px;">
        <div class="cp2-name">${name}</div>
        <div class="cp2-sub">${profileCapital} · ${profileRegime}</div>
      </div>
      <div style="margin-left:auto;display:flex;align-items:center;gap:8px;">
        ${smBtn}
        <span class="cp2-cmr-pill ${cmrPillClass}">${profileCmrStatus} CMR</span>
      </div>
    </div>`;
  const heroHtml = cpBuildHeroSection(name, summary, watchpoints, cEvs.length, latestEventDate);

  // ── 2. Radar + Sources band ──────────────────────────────────
  const radarHtml = cpBuildRadarSection(name, safeId);

  // ── 3. Briefing Panels ───────────────────────────────────────
  const institutionalHtml = cpBuildInstitutionalPanel(profileNote, watchpoints);
  const economyHtml = cpBuildEconomyPanel(name, stats, prof);
  const leadershipHtml = cpBuildLeadershipPanel(positions, election);
  const dataWindowHtml = cpBuildDataWindowPanel(name, latestEventDate);
  const briefingHtml = `
    <section class="cp2-brief-grid">
      <div class="cp2-brief-main">
        ${institutionalHtml}
        ${economyHtml}
      </div>
      <div class="cp2-brief-side">
        ${leadershipHtml}
        ${dataWindowHtml}
      </div>
    </section>`;

  // ── 4. Event Pulse ───────────────────────────────────────────
  const pulseHtml = cpBuildPulseSection(name, safeId);

  // ── 5. Live Events ───────────────────────────────────────────
  const evRows = cEvs.length
    ? cEvs.map(ev => `
        <div class="cp2-event-item${selectedEvent && String(selectedEvent.id) === String(ev.id) ? ' is-open' : ''}" data-profile-id="${safeId}" data-event-id="${ev.id}">
          <button class="cp2-event-row${selectedEvent && String(selectedEvent.id) === String(ev.id) ? ' selected' : ''}" type="button" data-profile-id="${safeId}" data-event-id="${ev.id}" onclick="cpSelectCountryEvent('${safeId}','${ev.id}')">
            <div class="cp2-event-row-top">
              <span class="cp2-event-row-type" style="color:${TC_HEX[ev.type] || '#6a6560'}">${TYPE_LABEL[ev.type] || ev.type}</span>
              <span class="cp2-event-row-date">${escapeHtml(cpFormatCalendarDate(ev.date))}</span>
            </div>
            <div class="cp2-event-row-title">${escapeHtml(ev.title)}</div>
            <div class="cp2-event-row-summary">${escapeHtml(cpTrimCopy(ev.summary || ev.analysis || 'No field-note summary is available yet.', 132))}</div>
            <div class="cp2-event-row-meta">${escapeHtml([ev.source || 'Source pending', ev.location || ev.country || 'Location pending'].filter(Boolean).join(' · '))}</div>
          </button>
          <div class="cp2-event-inline-detail">${selectedEvent && String(selectedEvent.id) === String(ev.id) ? cpEventDetailMarkup(ev) : ''}</div>
        </div>`).join('')
    : '<div class="cp2-event-detail-empty"><div class="cp2-col-kicker">Field Reporting</div><div class="cp2-event-empty-copy">No events in the live data store for this country yet.</div></div>';
  const eventsHtml = `
    <div class="cp2-events-section" data-editorial-block="country-event-accordion">
      <div class="cp2-events-hdr">
        <span class="cp2-events-label">Field Reporting & Event Briefs</span>
        <span class="cp2-events-count">${cEvs.length} events · latest ${escapeHtml(latestEventLabel)}</span>
      </div>
      <div class="cp2-events-layout">
        <div class="cp2-events-list cp2-events-list-accordion">${evRows}</div>
      </div>
    </div>`;

  // ── 6. Structural Trends ─────────────────────────────────────
  const trendsHtml = cpBuildStructuralTrends(name);
  const predictiveTrendsHtml = cpBuildPredictiveTrendSeries(name);
  const pressureHtml = `
    <section class="cp2-pressure-shell">
      <div class="cp2-section-head">
        <div>
          <div class="cp2-col-kicker">Pressure Dashboard</div>
          <div class="cp2-section-title">Predictive pressure, structural conditions, and comparative risk profile</div>
        </div>
        <div class="cp2-section-note">Use this layer to separate near-term pressure from slower institutional and economic conditions.</div>
      </div>
      ${predictiveTrendsHtml}
      ${trendsHtml}
      ${radarHtml}
    </section>`;

  // ── Assemble and render ──────────────────────────────────────
  countryDiv.innerHTML = `<article class="cp2-article editorial-surface editorial-surface-dossier" data-editorial-surface="country-dossier">
    ${hdrHtml}
    ${heroHtml}
    ${briefingHtml}
    ${pressureHtml}
    <section class="cp2-live-field-shell">${pulseHtml + eventsHtml}</section>
  </article>`;

  _currentCpName = name;
  regional.style.display = 'none';
  countryDiv.style.display = 'block';
  countryDiv.scrollTop = 0;

  // Chart.js requires canvas to be visible — defer one tick
  setTimeout(() => {
    cpInitRadar(name, safeId);
    cpInitPulse(name, safeId);
  }, 0);
}

const SM_CAT_COLOR = {
  peace:'#2d8659', military:'#a84000', political:'#1a6e82',
  oc:'#6a4a6e', reform:'#1a538f', intl:'#2e6b8a', live:'#c49a20',
};
const SM_CAT_LABEL = {
  peace:'Peace', military:'Military', political:'Political',
  oc:'Armed Groups', reform:'Reform', intl:'International', live:'Live',
};

function showCountryProfileGeneric(name) {
  // Show the standard profile view even for special countries (bypasses SM auto-redirect)
  document.querySelectorAll('.cp-btn').forEach(b => b.classList.toggle('active', b.dataset.country === name));
  const regional   = document.getElementById('cp-regional');
  const countryDiv = document.getElementById('cp-country');
  const prof = COUNTRY_PROFILES[name];
  if (!prof) return;
  // Continue with normal profile rendering (falls through to showCountryProfile body)
  // by temporarily removing special flag, rendering, then restoring
  const wasSpecial = prof.special;
  prof.special = false;
  showCountryProfile(name);
  prof.special = wasSpecial;
}

function showSpecialMonitor(name) {
  const countryDiv = document.getElementById('cp-country');
  const prof = COUNTRY_PROFILES[name];
  const data = SPECIAL_MONITOR_MILESTONES[name];
  if (!prof || !data) { showCountryProfile(name); return; }

  const cmrClass = (prof.cmrClass || 'stable').toLowerCase();
  const summary  = getCountryPredictiveSummary(name);
  const overallRiskScore = Number(summary?.overall_risk_score) || 0;

  // Merge curated events with live pipeline events (cat='live')
  const startDate = `${data.timelineStart || 2016}-01-01`;
  const liveEvs = (allEvents || [])
    .filter(e => matchesProfileCountryEvent(e, name) && e.date >= startDate)
    .map(e => ({ id: String(e.id), date: e.date, cat: 'live', title: e.title, desc: e.summary || '' }));
  const curatedIds = new Set(data.events.map(e => e.id));
  const merged = [
    ...data.events,
    ...liveEvs.filter(e => !curatedIds.has(e.id)),
  ].sort((a, b) => a.date.localeCompare(b.date));

  // ── Header ──────────────────────────────────────────────────
  const safeName = name.replace(/'/g, "\\'");
  const hdrHtml = `
    <div class="sm-hdr">
      <div>
        <div class="sm-name">${name}</div>
        <div class="sm-sub">${data.subtitle || ''}</div>
      </div>
      <div style="margin-left:auto;display:flex;align-items:center;gap:6px;">
        <button class="cp2-sm-btn sm-active" onclick="showCountryProfile('${safeName}')">★ Special Monitor</button>
        <span class="sm-cmr-pill ${cmrClass}">${prof.cmrStatus} CMR</span>
      </div>
    </div>`;

  // ── Brief + side panel ───────────────────────────────────────
  const metaHtml = (data.meta || []).map(m => `
    <div class="sm-meta-block">
      <div class="sm-meta-kicker">${m.kicker}</div>
      <div class="sm-meta-val">${m.value}</div>
    </div>`).join('');

  const riskColor = getMonitorScoreColor(overallRiskScore);
  const riskBand  = summary?.overall_risk_level || getOverallRiskBand(overallRiskScore);
  const trend     = summary?.leading_trend || 'steady';

  const sidePanelHtml = `
    <div class="sm-side-panel">
      <div class="sm-risk-box">
        <div class="sm-risk-kicker">Overall Risk</div>
        <div class="sm-risk-score" style="color:${riskColor};">${formatMonitorValue(overallRiskScore) || '—'}</div>
        <div class="sm-risk-band">${riskBand}</div>
        <div class="sm-risk-trend">${trend} trend</div>
      </div>
      <div class="sm-meta-stack">${metaHtml}</div>
    </div>`;

  const briefHtml = `
    <div class="sm-body-row">
      <div class="sm-brief">
        <div class="sm-brief-kicker">★ Analytical Brief</div>
        <div class="sm-brief-text">${data.brief || ''}</div>
      </div>
      ${sidePanelHtml}
    </div>`;

  // ── Timeline section (shell — SVG built after innerHTML set) ─
  const smId = name.replace(/ /g, '_');
  const filterBtns = [
    ['All', 'all'], ['Peace', 'peace'], ['Military', 'military'],
    ['Political', 'political'], ['Armed Groups', 'oc'], ['Reform', 'reform'],
    ['International', 'intl'], ['● Live', 'live'],
  ].map(([label, cat]) =>
    `<button class="sm-f-btn${cat === 'all' ? ' active' : ''}" data-c="${cat}" onclick="smSetFilter('${smId}','${cat}')">${label}</button>`
  ).join('');

  const evListRows = [...merged].reverse().map(ev => {
    const color = SM_CAT_COLOR[ev.cat] || '#6a6560';
    const livePip = ev.cat === 'live' ? '<span class="sm-live-pip">live</span>' : '';
    return `
      <div class="sm-ev-row" data-id="${ev.id}" data-cat="${ev.cat}" onclick="smSelectEvent('${smId}','${ev.id}')">
        <div class="sm-ev-cat-bar" style="background:${color}"></div>
        <div class="sm-ev-date">${ev.date.slice(0,7)}</div>
        <div class="sm-ev-cat-lbl" style="color:${color}">${SM_CAT_LABEL[ev.cat] || ev.cat}${livePip}</div>
        <div class="sm-ev-title">${ev.title}</div>
      </div>
      <div class="sm-ev-desc" data-id="${ev.id}">${ev.desc || ''}</div>`;
  }).join('');

  const tlHtml = `
    <div class="sm-tl-sec">
      <div class="sm-tl-top">
        <div class="sm-tl-label">CMR Timeline — ${data.timelineStart} to present</div>
        <div class="sm-filters">${filterBtns}</div>
      </div>
      <div class="sm-tl-figure">
        <svg id="sm-svg-${smId}" xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;"></svg>
      </div>
      <div class="sm-scroll-hint">scroll to explore full timeline</div>
      <div class="sm-ev-list">
        <div class="sm-ev-list-hdr">
          <span class="sm-ev-list-label">Events</span>
          <span class="sm-ev-count" id="sm-ev-count-${smId}">${merged.length} total</span>
        </div>
        <div id="sm-ev-body-${smId}">${evListRows}</div>
      </div>
    </div>`;

  // ── Key Data strip ───────────────────────────────────────────
  const dsHtml = `
    <div class="sm-data-strip">
      <div class="sm-ds-label">Key Data — ${name}</div>
      <div class="sm-ds-grid">
        ${(data.keyData || []).map(d => `
          <div class="sm-ds-cell">
            <div class="sm-ds-name">${d.name}</div>
            <div class="sm-ds-val">${d.value}</div>
            <div class="sm-ds-sub">${d.sub}</div>
          </div>`).join('')}
      </div>
    </div>`;

  countryDiv.innerHTML = `<div class="sm-card">${hdrHtml}${briefHtml}${dsHtml}${tlHtml}</div>`;
  countryDiv.style.display = 'block';
  countryDiv.scrollTop = 0;
  document.getElementById('cp-regional').style.display = 'none';

  setTimeout(() => smBuildSvg(smId, merged), 0);
}

// ── SVG builder ──────────────────────────────────────────────────
function smBuildSvg(smId, events) {
  const svg = document.getElementById(`sm-svg-${smId}`);
  if (!svg) return;

  const PAD_L = 40, PAD_R = 40, YEAR_W = 86;
  const DOT_R = 5.5, STEM_BASE = 20, STEP = 18;

  // Date range from actual events
  const evYears = events.map(e => parseInt(e.date));
  const START = Math.min(...evYears, 2016);
  const END   = Math.max(...evYears, new Date().getFullYear()) + 1;
  const YEARS = END - START;
  const SVG_W = PAD_L + YEARS * YEAR_W + PAD_R;
  const NOW   = new Date().toISOString().slice(0, 10);

  function dateToX(d) {
    const dt = new Date(d + 'T12:00:00');
    const yr = dt.getFullYear();
    const t  = yr + (dt - new Date(yr, 0, 1)) / (new Date(yr + 1, 0, 1) - new Date(yr, 0, 1));
    return PAD_L + ((t - START) / YEARS) * (YEARS * YEAR_W);
  }

  function ns(tag, attrs = {}) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    return el;
  }

  // Collision detection — assign levels
  const sorted = [...events].sort((a, b) => a.date.localeCompare(b.date));
  const placed = [];
  sorted.forEach(ev => {
    const x = dateToX(ev.date);
    let level = 0;
    while (placed.some(p => p.level === level && Math.abs(p.x - x) < 36)) level++;
    placed.push({ ...ev, x, level });
  });

  const maxLevel = placed.reduce((m, p) => Math.max(m, p.level), 0);
  // AXIS_Y is dynamic: enough room for all levels + top padding
  const AXIS_Y = STEM_BASE + maxLevel * STEP + DOT_R + 22;
  const svgH   = AXIS_Y + 30; // space for year labels below axis

  svg.setAttribute('width', SVG_W);
  svg.setAttribute('height', svgH);
  svg.setAttribute('viewBox', `0 0 ${SVG_W} ${svgH}`);
  svg.style.height = svgH + 'px';
  svg.innerHTML = '';

  // Alternating year bands
  for (let yr = START; yr < END; yr++) {
    if ((yr - START) % 2 === 0) {
      svg.appendChild(ns('rect', {
        x: dateToX(`${yr}-01-01`), y: 0,
        width: YEAR_W, height: AXIS_Y,
        fill: 'rgba(0,0,0,0.02)',
      }));
    }
  }

  // Axis line
  svg.appendChild(ns('line', {
    x1: PAD_L, y1: AXIS_Y, x2: SVG_W - PAD_R, y2: AXIS_Y,
    stroke: '#c8bfb0', 'stroke-width': '1.5',
  }));

  // Year ticks + labels
  for (let yr = START; yr <= END; yr++) {
    const x = dateToX(`${yr}-01-01`);
    svg.appendChild(ns('line', { x1: x, y1: AXIS_Y - 3, x2: x, y2: AXIS_Y + 5, stroke: '#c8bfb0', 'stroke-width': '1' }));
    const lbl = ns('text', {
      x, y: AXIS_Y + 18,
      'text-anchor': 'middle', fill: '#8a8278',
      'font-family': 'DM Mono,monospace', 'font-size': '9', 'letter-spacing': '0.2',
    });
    lbl.textContent = yr;
    svg.appendChild(lbl);
  }

  // NOW dashed line
  const nowX = dateToX(NOW);
  if (nowX >= PAD_L && nowX <= SVG_W - PAD_R) {
    svg.appendChild(ns('line', {
      x1: nowX, y1: 4, x2: nowX, y2: AXIS_Y - 2,
      stroke: 'rgba(196,122,32,0.3)', 'stroke-width': '1', 'stroke-dasharray': '3,3',
    }));
    const nowT = ns('text', {
      x: nowX + 4, y: 13, fill: 'rgba(196,122,32,0.45)',
      'font-family': 'DM Mono,monospace', 'font-size': '7.5',
    });
    nowT.textContent = 'NOW';
    svg.appendChild(nowT);
  }

  // Events
  placed.forEach(ev => {
    const color = SM_CAT_COLOR[ev.cat] || '#6a6560';
    const stemH = STEM_BASE + ev.level * STEP;
    const dotY  = AXIS_Y - stemH;

    // Stem
    svg.appendChild(ns('line', {
      x1: ev.x, y1: AXIS_Y - 2, x2: ev.x, y2: dotY + DOT_R + 1,
      stroke: color, 'stroke-width': '1', 'stroke-opacity': '0.28',
      class: `sm-stem sm-stem-${smId}-${ev.id}`,
    }));

    const g = ns('g', {
      transform: `translate(${ev.x},${dotY})`,
      cursor: 'pointer',
      class: `sm-dot-g sm-dot-${smId}-${ev.id}`,
      'data-id': ev.id, 'data-cat': ev.cat,
    });

    // Outer glow ring (hover)
    g.appendChild(ns('circle', { r: '9', fill: 'none', stroke: color, 'stroke-width': '1.5', 'stroke-opacity': '0', class: 'sm-dot-ring' }));
    // Dot: filled with tint, colored stroke
    g.appendChild(ns('circle', {
      r: String(DOT_R), fill: color, 'fill-opacity': '0.18',
      stroke: color, 'stroke-width': '1.8', class: 'sm-dot-circle',
    }));
    // Invisible hit area
    g.appendChild(ns('circle', { r: '12', fill: 'transparent' }));

    // Tooltip — flip to below axis if dot is in top third of chart
    const tipW = 178, tipH = 60;
    const flipBelow = dotY < svgH * 0.3;
    const tipX = ev.x > SVG_W - tipW - 20 ? -(tipW + 8) : 10;
    const tipY = flipBelow ? (AXIS_Y - dotY + 6) : -(stemH + tipH + 6);
    const fo = ns('foreignObject', {
      x: tipX, y: tipY, width: tipW, height: tipH,
      class: `sm-tip-fo sm-tip-${smId}-${ev.id}`,
      style: 'display:none;pointer-events:none;',
    });
    const div = document.createElement('div');
    div.style.cssText = `background:var(--bg,#faf8f4);border:1px solid #d4c8b4;border-radius:5px;padding:7px 9px;font-size:10px;color:#4a453e;line-height:1.45;font-family:'DM Sans',sans-serif;box-shadow:0 3px 10px rgba(26,24,20,0.1);`;
    div.innerHTML = `<div style="font-size:7.5px;font-family:'DM Mono',monospace;color:#8a8278;margin-bottom:2px;">${ev.date}</div>`
      + `<div style="font-size:7.5px;font-family:'DM Mono',monospace;color:${color};margin-bottom:4px;text-transform:uppercase;letter-spacing:.6px;">${SM_CAT_LABEL[ev.cat] || ev.cat}</div>`
      + `<div style="font-size:9.5px;line-height:1.4;">${escapeHtml(ev.title)}</div>`;
    fo.appendChild(div);
    g.appendChild(fo);

    g.addEventListener('mouseenter', () => {
      if (!g._smActive) fo.style.display = '';
      g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0.35');
      document.querySelector(`.sm-stem-${smId}-${ev.id}`)?.setAttribute('stroke-opacity', '0.6');
    });
    g.addEventListener('mouseleave', () => {
      if (!g._smActive) fo.style.display = 'none';
      if (!g._smActive) g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0');
      if (!g._smActive) document.querySelector(`.sm-stem-${smId}-${ev.id}`)?.setAttribute('stroke-opacity', '0.28');
    });
    g.addEventListener('click', () => smSelectEvent(smId, ev.id));
    svg.appendChild(g);
  });
}

// ── Interaction handlers ─────────────────────────────────────────
function smSelectEvent(smId, id) {
  // Deselect if same
  const g = document.querySelector(`.sm-dot-${smId}-${id}`);
  if (g && g._smActive) {
    g._smActive = false;
    g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0');
    g.querySelector('.sm-dot-circle').setAttribute('fill', '#161a22');
    document.querySelector(`.sm-tip-${smId}-${id}`)?.setAttribute('style', 'display:none;pointer-events:none;');
    document.querySelector(`.sm-stem-${smId}-${id}`)?.setAttribute('stroke-opacity', '0.2');
    document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-row[data-id="${id}"]`).forEach(r => { r.classList.remove('highlighted', 'expanded'); });
    document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-desc[data-id="${id}"]`).forEach(d => d.style.display = 'none');
    return;
  }

  // Clear previous active
  document.querySelectorAll(`.sm-dot-g`).forEach(dg => {
    dg._smActive = false;
    dg.querySelector('.sm-dot-ring')?.setAttribute('stroke-opacity', '0');
    dg.querySelector('.sm-dot-circle')?.setAttribute('fill', '#F5F2ED');
  });
  document.querySelectorAll(`[class*="sm-tip-${smId}-"]`).forEach(t => t.setAttribute('style', 'display:none;pointer-events:none;'));
  document.querySelectorAll(`[class*="sm-stem-${smId}-"]`).forEach(s => s.setAttribute('stroke-opacity', '0.12'));
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-row`).forEach(r => r.classList.remove('highlighted', 'expanded'));
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-desc`).forEach(d => d.style.display = 'none');

  // Activate selected
  if (g) {
    g._smActive = true;
    const color = SM_CAT_COLOR[g.dataset.cat] || '#6a6560';
    g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0.35');
    g.querySelector('.sm-dot-circle').setAttribute('fill', color);
    document.querySelector(`.sm-tip-${smId}-${id}`)?.setAttribute('style', 'display:block;pointer-events:none;');
    document.querySelector(`.sm-stem-${smId}-${id}`)?.setAttribute('stroke-opacity', '0.65');
  }
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-row[data-id="${id}"]`).forEach(r => r.classList.add('highlighted', 'expanded'));
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-desc[data-id="${id}"]`).forEach(d => { d.style.display = 'block'; });
  document.querySelector(`#sm-ev-body-${smId} .sm-ev-row[data-id="${id}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function smSetFilter(smId, cat) {
  document.querySelectorAll(`.sm-filters .sm-f-btn`).forEach(b => b.classList.toggle('active', b.dataset.c === cat));
  document.querySelectorAll(`.sm-dot-g`).forEach(g => {
    const show = cat === 'all' || g.dataset.cat === cat;
    g.setAttribute('opacity', show ? '1' : '0.07');
    g.style.pointerEvents = show ? '' : 'none';
  });
  document.querySelectorAll(`[class*="sm-stem-"]`).forEach(s => {
    const cls = [...s.classList].find(c => c.startsWith('sm-stem-'));
    const evId = cls?.split('-').slice(3).join('-');
    const ev   = document.querySelector(`.sm-dot-g[data-id="${evId}"]`);
    s.setAttribute('stroke-opacity', (cat === 'all' || ev?.dataset.cat === cat) ? '0.2' : '0.04');
  });
  const body = document.getElementById(`sm-ev-body-${smId}`);
  if (body) {
    body.querySelectorAll('.sm-ev-row').forEach(r => r.classList.toggle('filtered-out', cat !== 'all' && r.dataset.cat !== cat));
  }
  const visCount = cat === 'all'
    ? document.querySelectorAll(`.sm-dot-g`).length
    : document.querySelectorAll(`.sm-dot-g[data-cat="${cat}"]`).length;
  const countEl = document.getElementById(`sm-ev-count-${smId}`);
  if (countEl) countEl.textContent = `${visCount} shown`;
}

function showRegionalOverview(){
  document.querySelectorAll('.cp-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('cp-regional').style.display='block';
  document.getElementById('cp-country').style.display='none';
  cpMap=null;
  renderRegionalMonitorSummary();
  setTimeout(renderCpRegionalMap,60);
}

// ── COUNTRY PROFILE STATIC MAP ─────────────────────────────────
let cpMap=null;
let cpProfileLayer='overall_risk';
let cpProfileMapContext={name:null, events:[]};
let cpRegionalMap=null;

function renderCpStaticMap(){
  const el=document.getElementById('cp-map-leaf');
  const svgNode=document.getElementById('cp-map-static-svg');
  const name = cpProfileMapContext?.name;
  if(!el || !svgNode || !name) return;
  if(!worldFeatures){
    initExploreMap();
    if(!worldFeatures) return;
  }
  const cpNumId = COUNTRY_NAME_TO_ID[name];
  if(!cpNumId) return;
  const cpFeat = worldFeatures.find(f => +f.id === cpNumId);
  if(!cpFeat) return;

  const w = el.clientWidth || 720;
  const h = el.clientHeight || 320;
  const layerConfig = getRegionalLayerConfig(cpProfileLayer);
  const selectedScore = layerConfig.score(name) || 0;
  const scoreLabel = document.getElementById('cp-map-static-score-label');
  const scoreValue = document.getElementById('cp-map-static-score-value');
  const scoreNote = document.getElementById('cp-map-static-score-note');
  if(scoreLabel) scoreLabel.textContent = layerConfig.label;
  if(scoreValue){
    scoreValue.textContent = `${selectedScore}/100`;
    scoreValue.style.color = getMonitorScoreColor(selectedScore);
  }
  if(scoreNote) scoreNote.textContent = layerConfig.detail(name);

  const svg = d3.select('#cp-map-static-svg')
    .attr('viewBox', `0 0 ${w} ${h}`)
    .attr('width', '100%')
    .attr('height', '100%');
  svg.selectAll('*').remove();

  const proj = d3.geoMercator().fitExtent([[26, 20], [w - 26, h - 24]], cpFeat);
  const path = d3.geoPath().projection(proj);

  svg.append('path')
    .datum(cpFeat)
    .attr('d', path)
    .attr('fill', getMilitarizationColor(selectedScore))
    .attr('fill-opacity', 0.22)
    .attr('stroke', 'rgba(28,43,58,0.44)')
    .attr('stroke-width', 1.6);

  svg.append('path')
    .datum(cpFeat)
    .attr('d', path)
    .attr('fill', 'none')
    .attr('stroke', 'rgba(184,150,62,0.6)')
    .attr('stroke-width', 0.9)
    .attr('stroke-dasharray', '3 3')
    .attr('opacity', 0.8);

  const validEvents = (cpProfileMapContext?.events || []).filter(ev => Array.isArray(ev.coords) && Number.isFinite(ev.coords[0]) && Number.isFinite(ev.coords[1]));
  svg.append('g')
    .selectAll('circle')
    .data(validEvents)
    .enter()
    .append('circle')
    .attr('cx', d => proj([d.coords[1], d.coords[0]])?.[0] ?? -999)
    .attr('cy', d => proj([d.coords[1], d.coords[0]])?.[1] ?? -999)
    .attr('r', d => d.salience === 'high' ? 5.2 : d.salience === 'medium' ? 4.4 : 3.8)
    .attr('fill', d => TC_HEX[d.type] || '#6a6560')
    .attr('stroke', '#fffdf7')
    .attr('stroke-width', 1.2)
    .attr('opacity', 0.9)
    .append('title')
    .text(d => `${getEventTypeLabel(d.type)} · ${d.date}\n${d.title}`);
}

function getVisibleProfileCountries(){
  const data=SUBREGIONS[cpActiveSr]||SUBREGIONS.all;
  return data.countries;
}

function clamp01(n){
  if(!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function getMilitarizationStructuralScore(country){
  const row = COUNTRY_M3[country];
  if(!row) return { score:0, coverage:0 };
  const components = [
    { value: row.conscription, weight:0.12 },
    { value: row.milVeto, weight:0.24 },
    { value: row.milImpunity, weight:0.20 },
    { value: row.milCrimePolice, weight:0.18 },
    { value: row.milEco, weight:0.16 },
    { value: row.hwi == null ? null : clamp01(Math.log1p(row.hwi) / Math.log1p(20)), weight:0.10 }
  ].filter(item=>item.value !== null && item.value !== undefined);
  const totalWeight = components.reduce((sum,item)=>sum + item.weight, 0);
  if(!totalWeight) return { score:0, coverage:0 };
  return {
    score: clamp01(components.reduce((sum,item)=>sum + (Number(item.value) || 0) * item.weight, 0) / totalWeight),
    coverage: totalWeight
  };
}

function getMilitarizationMetrics(visibleCountries){
  const liveRawByCountry = new Map();
  let maxLiveRaw = 0;

  visibleCountries.forEach(country=>{
    const raw = allEvents
      .filter(ev=>ev.country===country)
      .reduce((sum,ev)=>{
        const typeWeight = LIVE_MIL_WEIGHT[ev.type] ?? LIVE_MIL_WEIGHT.other;
        const salienceWeight = LIVE_SALIENCE_WEIGHT[ev.salience] ?? LIVE_SALIENCE_WEIGHT.low;
        return sum + (typeWeight * salienceWeight);
      }, 0);
    liveRawByCountry.set(country, raw);
    maxLiveRaw = Math.max(maxLiveRaw, raw);
  });

  const metrics = new Map();
  visibleCountries.forEach(country=>{
    const structural = getMilitarizationStructuralScore(country);
    const liveRaw = liveRawByCountry.get(country) || 0;
    const liveNorm = maxLiveRaw > 0 ? clamp01(liveRaw / maxLiveRaw) : 0;
    const combined = clamp01((structural.score * 0.7) + (liveNorm * 0.3));
    const countryEvents = allEvents.filter(ev=>ev.country===country);
    const topTypeEntry = Object.entries(countryEvents.reduce((acc,ev)=>{
      acc[ev.type] = (acc[ev.type] || 0) + 1;
      return acc;
    }, {})).sort((a,b)=>b[1]-a[1])[0];

    metrics.set(country, {
      score: Math.round(combined * 100),
      structuralScore: Math.round(structural.score * 100),
      liveScore: Math.round(liveNorm * 100),
      eventCount: countryEvents.length,
      high: countryEvents.filter(ev=>ev.salience==='high').length,
      medium: countryEvents.filter(ev=>ev.salience==='medium').length,
      topType: topTypeEntry ? topTypeEntry[0] : null,
      coverageLabel: structural.coverage > 0 ? 'M3 + SENTINEL live events' : 'SENTINEL live events only'
    });
  });
  return metrics;
}

function getRegionalMonitorMetrics(visibleCountries){
  const metrics = new Map();
  visibleCountries.forEach(country => {
    const regime = getCountryRiskConstruct(country, 'regime_vulnerability');
    const militarization = getCountryRiskConstruct(country, 'militarization');
    const fragmentation = getCountryRiskConstruct(country, 'security_fragmentation');
    if(regime){
      metrics.set(country, {
        score: formatMonitorValue(regime.score) || 0,
        baseline: formatMonitorValue(getCountryMonitor(country, 'cmr_balance')?.baseline_score) || 0,
        pulse: formatMonitorValue(getCountryMonitor(country, 'cmr_balance')?.pulse_score) || 0,
        trend: regime.trend_label || 'stable',
        dominantRecentSignal: getCountryMonitor(country, 'security_pressure')?.dominant_recent_signal || getCountryMonitor(country, 'cmr_balance')?.dominant_recent_signal || null,
        militarizationScore: formatMonitorValue(militarization?.score) || 0,
        fragmentationScore: formatMonitorValue(fragmentation?.score) || 0,
        coverageLabel: 'Layered risk model'
      });
      return;
    }
    const legacy = getMilitarizationMetrics([country]).get(country);
    metrics.set(country, {
      score: legacy?.score || 0,
      baseline: legacy?.structuralScore || 0,
      pulse: legacy?.liveScore || 0,
      trend: 'stable',
      dominantRecentSignal: legacy?.topType || null,
      securityScore: 0,
      alignmentScore: 0,
      coverageLabel: legacy?.coverageLabel || 'Legacy fallback'
    });
  });
  return metrics;
}

function getRegionalLayerConfig(layer){
  const configs = {
    overall_risk: {
      label:'Overall Risk',
      score: country => Number(getCountryPredictiveSummary(country)?.overall_risk_score) || 0,
      detail: country => {
        const summary = getCountryPredictiveSummary(country);
        return `${summary?.overall_risk_level || getOverallRiskBand(summary?.overall_risk_score || 0)} · ${summary?.leading_trend || 'steady'} leading trend`;
      }
    },
    regime_vulnerability: {
      label:'Regime Vulnerability',
      score: country => formatMonitorValue(getCountryRiskConstruct(country, 'regime_vulnerability')?.score) || 0,
      detail: country => {
        const construct = getCountryRiskConstruct(country, 'regime_vulnerability');
        return `${construct?.trend_label || 'stable'} trend · ${construct?.horizon_days || 90}-day horizon`;
      }
    },
    militarization: {
      label:'Militarization',
      score: country => formatMonitorValue(getCountryRiskConstruct(country, 'militarization')?.score) || 0,
      detail: country => {
        const construct = getCountryRiskConstruct(country, 'militarization');
        return `${construct?.trend_label || 'stable'} trend · ${construct?.horizon_days || 90}-day horizon`;
      }
    },
    security_fragmentation: {
      label:'Security Fragmentation',
      score: country => formatMonitorValue(getCountryRiskConstruct(country, 'security_fragmentation')?.score) || 0,
      detail: country => {
        const construct = getCountryRiskConstruct(country, 'security_fragmentation');
        return `${construct?.trend_label || 'stable'} trend · ${construct?.horizon_days || 90}-day horizon`;
      }
    }
  };
  return configs[layer] || configs.overall_risk;
}

function getMilitarizationColor(score){
  if(score >= 80) return '#556b2f';
  if(score >= 65) return '#6f7f3d';
  if(score >= 50) return '#8e9a58';
  if(score >= 35) return '#a8ae72';
  if(score >= 20) return '#c9cc9b';
  return '#f1f0e1';
}

function renderCpRegionalMap(){
  const wrap=document.getElementById('cp-regional-map-wrap');
  const svgEl=document.getElementById('cp-regional-map-svg');
  if(!wrap || !svgEl) return;
  const visibleCountries=getVisibleProfileCountries();
  const visibleIds=new Set(visibleCountries.map(c=>COUNTRY_NAME_TO_ID[c]).filter(Boolean));
  const metrics=getRegionalMonitorMetrics(visibleCountries);
  const layerConfig = getRegionalLayerConfig(cpRegionalLayer);
  const legendTitle = document.getElementById('cp-map-legend-title');
  if(legendTitle) legendTitle.textContent = layerConfig.label;
  const mapLabel = wrap.querySelector('.context-map-label');
  if(mapLabel) mapLabel.textContent = `Regional ${layerConfig.label}`;

  if(!worldFeatures){
    initExploreMap();
    return;
  }

  const w = wrap.clientWidth || 700;
  const h = wrap.clientHeight || 440;
  const svg = d3.select('#cp-regional-map-svg')
    .attr('viewBox', `0 0 ${w} ${h}`)
    .attr('width','100%')
    .attr('height','100%');
  svg.selectAll('*').remove();

  const latamFeat = worldFeatures.filter(f => LATAM_IDS.has(+f.id));
  const proj = d3.geoMercator().fitExtent([[20,20],[w-20,h-20]], {
    type:'FeatureCollection', features:latamFeat
  });
  const path = d3.geoPath().projection(proj);
  const tooltip = d3.select('#cp-regional-tooltip');

  svg.append('g').selectAll('path')
    .data(latamFeat).enter().append('path')
    .attr('d', path)
    .attr('fill', d => {
      const name = COUNTRY_NAMES_MAP[+d.id];
      const score = name ? layerConfig.score(name) : 0;
      return visibleIds.has(+d.id) ? getMilitarizationColor(score || 0) : '#e8e4dc';
    })
    .attr('stroke','#b8b2a4')
    .attr('stroke-width',0.8)
    .style('cursor', d => visibleIds.has(+d.id) ? 'pointer' : 'default')
    .on('mouseover', function(evt, d) {
      if(!visibleIds.has(+d.id)) return;
      d3.select(this).attr('stroke','#54504a').attr('stroke-width',2);
      const countryName = COUNTRY_NAMES_MAP[+d.id];
      const metric = metrics.get(countryName);
      const topTypeLabel = metric?.dominantRecentSignal ? (TYPE_LABEL[metric.dominantRecentSignal] || metric.dominantRecentSignal) : 'No dominant live signal';
      const selectedLayerScore = layerConfig.score(countryName);
      const rect = wrap.getBoundingClientRect();
      tooltip.html(
        `<strong style="font-size:12px;color:var(--text);">${countryName}</strong>` +
        `<br><span style="font-family:var(--mono);font-size:10px;color:var(--text-muted);">${layerConfig.label}</span> <strong style="color:${getMonitorScoreColor(selectedLayerScore || 0)};">${selectedLayerScore || 0}/100</strong>` +
        `<br><span style="font-size:10.5px;color:var(--text-muted);">${layerConfig.detail(countryName)}</span>` +
        `<br><span style="font-size:10.5px;color:var(--text-muted);">Underlying CMR baseline ${metric?.baseline || 0} · pulse ${metric?.pulse || 0} · trend ${metric?.trend || 'stable'}</span>` +
        `<br><span style="font-size:10.5px;color:var(--text-muted);">Militarization ${metric?.militarizationScore || 0} · Security fragmentation ${metric?.fragmentationScore || 0}</span>` +
        `<br><span style="font-size:10.5px;color:var(--text-muted);">Dominant recent signal: ${topTypeLabel}</span>`
      )
      .style('display','block')
      .style('left', (evt.clientX - rect.left + 14) + 'px')
      .style('top',  (evt.clientY - rect.top  - 12) + 'px');
    })
    .on('mousemove', function(evt) {
      const rect = wrap.getBoundingClientRect();
      tooltip.style('left', (evt.clientX - rect.left + 14) + 'px')
             .style('top',  (evt.clientY - rect.top  - 12) + 'px');
    })
    .on('mouseout', function() {
      d3.select(this).attr('stroke','#b8b2a4').attr('stroke-width',0.8);
      tooltip.style('display','none');
    })
    .on('click', function(evt, d) {
      const countryName = COUNTRY_NAMES_MAP[+d.id];
      if(!countryName || !visibleIds.has(+d.id)) return;
      showCountryProfile(countryName);
    });

  svg.append('g').attr('pointer-events','none').selectAll('text')
    .data(Object.entries(COUNTRY_LABELS))
    .enter().append('text')
    .attr('x', d => proj(d[1][1])[0])
    .attr('y', d => proj(d[1][1])[1])
    .text(d => d[1][0])
    .attr('font-family','DM Mono,monospace')
    .attr('font-size','8.5px')
    .attr('fill','rgba(28,26,23,0.55)')
    .attr('text-anchor','middle');
}

// Wire up country profile buttons
document.querySelectorAll('.cp-btn[data-country]').forEach(btn=>{
  btn.addEventListener('click',()=>{
    setProfilesNavOpen(false);
    showCountryProfile(btn.dataset.country);
  });
});

// ── WORLD BANK SUBREGIONS ────────────────────────────────────
// Source: World Bank LAC classification (LCN)
const SUBREGIONS = {
  "all": {
    label:"Latin America & Caribbean",
    countries:["Brazil","Colombia","Mexico","Venezuela","Chile","Argentina","Peru","Ecuador","Bolivia","Cuba","Honduras","Guatemala","El Salvador","Nicaragua","Paraguay","Uruguay","Haiti","Dominican Republic","Panama","Costa Rica","Jamaica","Trinidad and Tobago","Guyana","Suriname","Belize"],
    spending:"$98.4B", personnel:"1.84M", gdpPct:"1.3%", countries_n:"25",
    note:"Latin America and the Caribbean is a region of 25 tracked states spanning roughly 20 million km², with a combined population of over 670 million. The region accounts for roughly 4.5% of global military spending; Brazil ($29.4B) and Colombia ($14.1B) are the dominant spenders, while the average defense burden (1.3% of GDP) sits well below the NATO target of 2%, reflecting post-Cold War demilitarization and relatively low external threat environments for most states. Civil-military relations histories are deeply heterogeneous — ranging from active armed conflict and formal internal security frameworks in Colombia, Ecuador, Mexico, and Haiti, to authoritarian civil-military fusion regimes in Venezuela and Cuba, and robust civilian control in Uruguay and Costa Rica. Country profiles synthesize structural indicators — regime type, military spending, personnel levels, conflict index, and CMR status — with analytical assessments grounded in CMR theory. Four deep-dive monitors (Colombia, Venezuela, El Salvador, Mexico) provide extended case analysis."
  },
  "south-andean": {
    label:"Andean South America",
    countries:["Colombia","Peru","Ecuador","Bolivia","Venezuela"],
    spending:"$23.8B", personnel:"556K", gdpPct:"1.9%", countries_n:"5",
    note:"Andean South America (World Bank: LAC — Andean subgroup) — Colombia, Peru, Ecuador, Bolivia, Venezuela. This subregion has the region's highest conflict density: Colombia's internal armed conflict, Ecuador's 2024 internal armed conflict declaration, Peru's VRAEM insurgency, Bolivia's political-military fragility, and Venezuela's authoritarian CMR fusion. U.S. counternarcotics cooperation is the primary engagement vector."
  },
  "south-cone": {
    label:"Southern Cone",
    countries:["Argentina","Chile","Paraguay","Uruguay"],
    spending:"$13.4B", personnel:"211K", gdpPct:"1.2%", countries_n:"4",
    note:"Southern Cone (World Bank: LAC — Southern Cone subgroup) — Argentina, Chile, Paraguay, Uruguay. This subregion has the strongest civilian control record in Latin America outside Brazil. Uruguay is the benchmark case; Chile's post-Pinochet transition is among the most studied in CMR theory. Argentina's 1983 transition and subsequent accountability trials are foundational references for transitional justice and civil-military reform."
  },
  "central": {
    label:"Central America",
    countries:["Honduras","Guatemala","El Salvador","Nicaragua","Panama","Costa Rica","Belize"],
    spending:"$2.1B", personnel:"106K", gdpPct:"0.9%", countries_n:"7",
    note:"Central America (World Bank: LAC — Central America subgroup) — Honduras, Guatemala, El Salvador, Nicaragua, Panama, Costa Rica, Belize. This subregion includes several of SENTINEL's highest-priority cases: El Salvador under Bukele (democratic backsliding, militarization), Nicaragua's authoritarian civil-military fusion, Guatemala's fragile democratic transition under Arévalo, and Honduras's legacy of military-cartel collusion. Costa Rica and Panama are outliers — both lack standing armies."
  },
  "caribbean": {
    label:"Caribbean",
    countries:["Cuba","Haiti","Dominican Republic","Jamaica","Trinidad and Tobago","Guyana","Suriname"],
    spending:"$3.2B", personnel:"182K", gdpPct:"1.5%", countries_n:"7",
    note:"Caribbean (World Bank: LAC — Caribbean subgroup) — Cuba, Haiti, Dominican Republic, Jamaica, Trinidad and Tobago, Guyana, Suriname. Cuba dominates CMR interest given the FAR's institutional role in the state economy and post-Castro succession dynamics. Haiti's UN-backed security transition (MSS) following the 2021 assassination of President Moïse and the collapse of the National Police is the region's acute security governance failure."
  },
  "brazil": {
    label:"Brazil",
    countries:["Brazil"],
    spending:"$29.4B", personnel:"366K", gdpPct:"1.3%", countries_n:"1",
    note:"Brazil (World Bank: classified separately as largest LAC economy — LCN). Brazil is a subregion unto itself in any CMR analysis. As the only Portuguese-speaking country in the region and the dominant military spender ($29.4B — 30% of LatAm total), Brazil warrants separate treatment. The Bolsonaro years (2019–2022) brought unprecedented military institutional involvement in civilian government; the Lula III administration's re-normalization is the key ongoing CMR question."
  },
  "mexico": {
    label:"Mexico",
    countries:["Mexico"],
    spending:"$9.4B", personnel:"277K", gdpPct:"0.6%", countries_n:"1",
    note:"Mexico (World Bank: Upper Middle Income LAC — often classified separately). Mexico straddles Central America and South America geopolitically. Its military's expanding role in infrastructure, customs, the National Guard, and internal security under AMLO represents the most significant structural shift in a major LAC military in a decade. Mexico's 277,000 active personnel and NORTHCOM partnership with the U.S. make it the dominant CMR case in the northern LAC corridor."
  }
};

let cpActiveSr='all', cpRegionalLayer='overall_risk';
let profilesNavOpen = false;

function setProfilesNavOpen(open){
  profilesNavOpen = !!open;
  const dock = document.getElementById('profiles-nav-dock');
  const trigger = document.getElementById('profiles-nav-trigger');
  const panel = document.getElementById('profiles-nav-panel');
  if(!dock || !trigger || !panel) return;
  dock.classList.toggle('is-open', profilesNavOpen);
  trigger.setAttribute('aria-expanded', profilesNavOpen ? 'true' : 'false');
  panel.hidden = !profilesNavOpen;
}

function toggleProfilesNav(force){
  setProfilesNavOpen(typeof force === 'boolean' ? force : !profilesNavOpen);
}

function updateProfilesNavSummary(){
  const data = SUBREGIONS[cpActiveSr] || SUBREGIONS.all;
  const count = getVisibleProfileCountries().length;
  const countEl = document.getElementById('profiles-visible-count');
  const summaryEl = document.getElementById('profiles-nav-summary');
  const activeBtn = document.querySelector(`#sr-tabs [data-sr="${cpActiveSr}"]`);
  const shortLabel = activeBtn?.textContent?.trim() || data.label;
  if(countEl) countEl.textContent = count;
  if(summaryEl) summaryEl.textContent = `${shortLabel} · ${count} visible`;
}

function applyProfileFilters(){
  const data=SUBREGIONS[cpActiveSr]||SUBREGIONS.all;
  document.getElementById('sr-title').textContent=data.label;
  renderRegionalMonitorSummary();
  document.querySelectorAll('.cp-btn[data-country]').forEach(btn=>{
    const c=btn.dataset.country;
    const inSr=cpActiveSr==='all'||data.countries.includes(c);
    btn.style.display=inSr?'':'none';
  });
  updateProfilesNavSummary();
  if(document.getElementById('cp-regional')?.style.display!=='none') setTimeout(renderCpRegionalMap,40);
}

document.querySelectorAll('[data-sr]').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const targetSr = btn.dataset.sr;
    document.querySelectorAll('[data-sr]').forEach(b=>{
      b.classList.toggle('active', b.dataset.sr === targetSr);
    });
    cpActiveSr=targetSr;
    applyProfileFilters();
    setProfilesNavOpen(false);
  });
});

document.addEventListener('click', evt => {
  if(!profilesNavOpen) return;
  const dock = document.getElementById('profiles-nav-dock');
  if(dock && !dock.contains(evt.target)) setProfilesNavOpen(false);
});

document.addEventListener('keydown', evt => {
  if(evt.key === 'Escape' && profilesNavOpen) setProfilesNavOpen(false);
});

document.querySelectorAll('#cp-map-layer-switch [data-layer]').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('#cp-map-layer-switch [data-layer]').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    cpRegionalLayer = btn.dataset.layer;
    renderCpRegionalMap();
  });
});

// Init
applyProfileFilters();

let ovProjection=null, ovSvg=null, ovTopoLoaded=false, _drawChoropleth=null;
let exCurrentMapLayer = 'overall_risk';

function getEventCountryKey(ev){
  return ev?.display_country || ev?.country || null;
}

async function initExploreMap(){
  const wrap=document.getElementById('explore-map-wrap');
  if(!wrap||ovTopoLoaded) return;
  ovTopoLoaded=true;

  const w=wrap.clientWidth||700, h=wrap.clientHeight||640;
  ovSvg=d3.select('#ov-svg').attr('viewBox',`0 0 ${w} ${h}`);
  ovSvg.selectAll('*').remove();

  const defs = ovSvg.append('defs');
  const gradient = defs.append('linearGradient')
    .attr('id','ov-ocean-gradient')
    .attr('x1','0%').attr('y1','0%')
    .attr('x2','0%').attr('y2','100%');
  gradient.append('stop').attr('offset','0%').attr('stop-color','#fbf8f2');
  gradient.append('stop').attr('offset','100%').attr('stop-color','#f3ecdf');
  ovSvg.append('rect')
    .attr('x',0).attr('y',0)
    .attr('width',w).attr('height',h)
    .attr('fill','url(#ov-ocean-gradient)');

  let world;
  try { world=await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'); }
  catch(e){ console.error('TopoJSON load failed',e); return; }

  const allFeat=topojson.feature(world,world.objects.countries).features;
  worldFeatures=allFeat;
  const latamFeat=allFeat.filter(f=>LATAM_IDS.has(+f.id));
  if(document.getElementById('cp-regional')) setTimeout(renderCpRegionalMap,40);

  ovProjection=d3.geoMercator().fitExtent([[56,34],[w-52,h-44]],{type:'FeatureCollection',features:latamFeat});
  const path=d3.geoPath().projection(ovProjection);
  const graticule=d3.geoGraticule().step([20,20]);
  ovSvg.append('path')
    .datum(graticule())
    .attr('d',path)
    .attr('fill','none')
    .attr('stroke','rgba(162,151,132,0.16)')
    .attr('stroke-width',0.6)
    .attr('stroke-dasharray','2 6');

  const choroplethG=ovSvg.append('g').attr('id','ov-choropleth');
  ovSignalLayer=ovSvg.append('g').attr('id','ov-signal-layer').attr('pointer-events','none');
  ovLabelLayer=ovSvg.append('g').attr('id','ov-label-layer').attr('pointer-events','none');
  const overviewLabelSet = new Set(['Mexico','Colombia','Brazil','Venezuela','Peru','Chile','Argentina','Haiti','El Salvador','Ecuador']);

  function eventCounts(){
    const c={};
    allEvents.forEach(ev=>{
      const country = getEventCountryKey(ev);
      if(country) c[country]=(c[country]||0)+1;
    });
    return c;
  }

  function getAnalyticalTrend(name, layer){
    if(layer === 'overall_risk'){
      return getCountryPredictiveSummary(name)?.leading_trend || 'stable';
    }
    if(['regime_vulnerability','militarization','security_fragmentation'].includes(layer)){
      return getCountryRiskConstruct(name, layer)?.trend_label || 'stable';
    }
    return 'stable';
  }

  function addPaths(colorFn, styleFn = null) {
    choroplethG.selectAll('path').remove();
    choroplethG.selectAll('path').data(latamFeat).enter().append('path')
      .attr('class','ov-country-path')
      .attr('d', path)
      .attr('fill', d => { const n = COUNTRY_NAMES_MAP[+d.id]; return colorFn(n); })
      .attr('stroke', d => {
        const n = COUNTRY_NAMES_MAP[+d.id];
        return styleFn?.(n)?.stroke || 'rgba(141,132,116,0.58)';
      })
      .attr('stroke-width', d => {
        const n = COUNTRY_NAMES_MAP[+d.id];
        return styleFn?.(n)?.strokeWidth || 0.9;
      })
      .attr('stroke-dasharray', d => {
        const n = COUNTRY_NAMES_MAP[+d.id];
        return styleFn?.(n)?.dasharray || null;
      })
      .style('cursor', 'pointer')
      .on('mouseover', function(evt, d) {
        const n = COUNTRY_NAMES_MAP[+d.id];
        d3.select(this)
          .attr('stroke', styleFn?.(n)?.hoverStroke || '#3f4038')
          .attr('stroke-width', (styleFn?.(n)?.strokeWidth || 0.9) + 0.9);
      })
      .on('mouseout',  function(evt, d) {
        const n = COUNTRY_NAMES_MAP[+d.id];
        d3.select(this)
          .attr('stroke', styleFn?.(n)?.stroke || 'rgba(141,132,116,0.58)')
          .attr('stroke-width', styleFn?.(n)?.strokeWidth || 0.9);
      })
      .on('click', function(evt, d) { showOvPopup(evt, d); });
  }

  function renderOverviewLabels(){
    ovLabelLayer.selectAll('*').remove();
    Object.entries(COUNTRY_LABELS)
      .filter(([, [name]]) => overviewLabelSet.has(name))
      .forEach(([id,[name,lonlat]])=>{
        const [x,y]=ovProjection(lonlat);
        ovLabelLayer.append('text')
          .attr('x',x)
          .attr('y',y + 4)
          .text(name)
          .attr('font-family','DM Mono,monospace')
          .attr('font-size','8px')
          .attr('letter-spacing','0.55px')
          .attr('fill','rgba(49,44,39,0.62)')
          .attr('text-anchor','middle');
      });
  }

  function renderOverviewSignalOverlay(layer){
    ovSignalLayer.selectAll('*').remove();
    if(!['overall_risk','regime_vulnerability','militarization','security_fragmentation','events'].includes(layer)) return;
    Object.entries(COUNTRY_LABELS).forEach(([, [name,lonlat]])=>{
      const [x,y]=ovProjection(lonlat);
      let badge = null;
      let accent = '#7b756b';
      let trend = 'stable';
      let score = 0;
      if(['overall_risk','regime_vulnerability','militarization','security_fragmentation'].includes(layer)){
        const meta = layer === 'overall_risk'
          ? getLeadingConstructMeta(name)
          : {
              code:layer,
              short:getConstructShortCode(layer),
              color:getConstructAccent(layer),
              trend:getAnalyticalTrend(name, layer),
              score:getRegionalLayerConfig(layer).score(name)
            };
        if(!meta || !meta.score) return;
        badge = meta.short;
        accent = meta.color;
        trend = meta.trend || 'stable';
        score = Number(meta.score) || 0;
      } else if(layer === 'events'){
        const recentCount = allEvents.filter(ev=>getEventProfileCountries(ev).includes(name) && matchesDateRange(ev, '30d')).length;
        if(!recentCount) return;
        const dominantType = Object.entries(
          allEvents
            .filter(ev=>getEventProfileCountries(ev).includes(name) && matchesDateRange(ev, '30d'))
            .reduce((acc, ev)=>{
              acc[ev.type] = (acc[ev.type] || 0) + 1;
              return acc;
            }, {})
        ).sort((a,b)=>b[1]-a[1])[0]?.[0] || 'other';
        badge = String(Math.min(recentCount, 99));
        accent = TC_HEX[dominantType] || '#6a6560';
        score = recentCount;
      }
      const group = ovSignalLayer.append('g')
        .attr('class','ov-signal-badge')
        .attr('transform', `translate(${x},${y - 18})`);
      group.append('circle')
        .attr('r', 15)
        .attr('fill', 'rgba(255,251,244,0.92)')
        .attr('stroke', accent)
        .attr('stroke-width', layer === 'events' ? 2.4 : 2.1);
      if(layer !== 'events'){
        group.append('circle')
          .attr('r', trend === 'rising' ? 19 : 18)
          .attr('fill', 'none')
          .attr('stroke', accent)
          .attr('stroke-opacity', trend === 'rising' ? 0.4 : trend === 'easing' ? 0.28 : 0.14)
          .attr('stroke-width', trend === 'rising' ? 2 : 1.2)
          .attr('stroke-dasharray', trend === 'easing' ? '3 2' : null);
      }
      group.append('text')
        .attr('text-anchor','middle')
        .attr('dy','0.32em')
        .attr('fill', layer === 'events' ? accent : '#1f2920')
        .text(badge);
    });
  }

  function updateLegend(layer) {
    const ltEl = document.getElementById('ov-legend-types');
    if (!ltEl) return;
    if(['overall_risk','regime_vulnerability','militarization','security_fragmentation'].includes(layer)){
      const labels = {
        overall_risk:['Lower risk','#f1f0e1','Guarded','#a8ae72','Elevated','#556b2f'],
        regime_vulnerability:['Stable','#f1f0e1','Stressed','#a8ae72','Vulnerable','#556b2f'],
        militarization:['Low','#f1f0e1','Moderate','#a8ae72','High','#556b2f'],
        security_fragmentation:['Low','#f1f0e1','Fragmented','#a8ae72','High','#556b2f']
      }[layer];
      ltEl.innerHTML = `
        <div class="ov-legend-row">
          <span class="ov-legend-swatch"><span class="ov-legend-bar" style="background:linear-gradient(90deg, ${labels[1]}, ${labels[3]}, ${labels[5]});"></span></span>
          <span>${labels[0]} to ${labels[4]} fill scale</span>
        </div>
        <div class="ov-legend-row">
          <span class="ov-legend-badge">R</span>
          <span>Badge marks the dominant pressure family: <strong>R</strong> regime, <strong>M</strong> militarization, <strong>S</strong> fragmentation.</span>
        </div>
        <div class="ov-legend-row">
          <span class="ov-legend-badge" style="border-style:dashed;">◌</span>
          <span>Outer halo shows trend direction. Strong halo = rising. Dashed halo = easing.</span>
        </div>
      `;
      return;
    }
    if(layer === 'events'){
      ltEl.innerHTML = `
        <div class="ov-legend-row">
          <span class="ov-legend-swatch"><span class="ov-legend-bar" style="background:linear-gradient(90deg, rgba(184,112,16,0.14), rgba(184,112,16,0.42), rgba(184,112,16,0.82));"></span></span>
          <span>Fill intensity shows volume of event activity.</span>
        </div>
        <div class="ov-legend-row">
          <span class="ov-legend-badge">12</span>
          <span>Country badges show the number of recent events. Badge color tracks the dominant event family.</span>
        </div>
      `;
      return;
    }
    if(layer === 'cmr'){
      ltEl.innerHTML = `
        <div class="ov-legend-row"><span class="ov-legend-swatch"><span class="ov-legend-bar" style="background:linear-gradient(90deg, #1a6e52, #c46e12, #8a1a1a);"></span></span><span>CMR fill moves from stable to authoritarian.</span></div>
        <div class="ov-legend-row"><span class="ov-legend-badge">i</span><span>Click any country to open a monitor brief with watchpoints and linked events.</span></div>
      `;
      return;
    }
    if(layer === 'aid'){
      ltEl.innerHTML = `
        <div class="ov-legend-row"><span class="ov-legend-swatch"><span class="ov-legend-bar" style="background:linear-gradient(90deg, rgba(26,83,143,0.12), rgba(26,83,143,0.42), rgba(26,83,143,0.86));"></span></span><span>Darker blue indicates heavier military-aid exposure.</span></div>
      `;
      return;
    }
    ltEl.innerHTML = `
      <div class="ov-legend-row"><span class="ov-legend-swatch"><span class="ov-legend-bar" style="background:linear-gradient(90deg, rgba(168,64,0,0.12), rgba(168,64,0,0.42), rgba(168,64,0,0.86));"></span></span><span>Darker fill indicates stronger conflict and militarized stress.</span></div>
    `;
  }

  function drawChoropleth() {
    const layer = exCurrentMapLayer;
    if (['overall_risk','regime_vulnerability','militarization','security_fragmentation'].includes(layer)) {
      const cfg = getRegionalLayerConfig(layer);
      const scores = {};
      Object.keys(COUNTRY_PROFILES).forEach(n => { scores[n] = cfg.score(n) || 0; });
      addPaths(
        n => n && scores[n] != null ? getMilitarizationColor(scores[n]) : '#e0d8cc',
        n => {
          const trend = getAnalyticalTrend(n, layer);
          return {
            stroke: trend === 'rising' ? 'rgba(154,87,48,0.75)' : trend === 'easing' ? 'rgba(26,110,82,0.55)' : 'rgba(110,102,88,0.54)',
            hoverStroke: trend === 'rising' ? '#7c3924' : trend === 'easing' ? '#16593f' : '#454238',
            strokeWidth: trend === 'rising' ? 1.4 : 0.95,
            dasharray: trend === 'easing' ? '4 2' : null
          };
        }
      );
      renderOverviewSignalOverlay(layer);
      renderOverviewLabels();
      updateLegend(layer);
      return;
    }
    if (layer === 'cmr') {
      const CMR_COLOR = { Authoritarian:'#8a1a1a', Crisis:'#b83232', Strained:'#c46e12', Stable:'#1a6e52' };
      addPaths(n => n ? (CMR_COLOR[COUNTRY_PROFILES[n]?.cmrStatus] || '#c0b89a') : '#e0d8cc');
      renderOverviewSignalOverlay(layer);
      renderOverviewLabels();
      updateLegend(layer);
    } else if (layer === 'events') {
      const counts = eventCounts();
      const maxC = Math.max(1, ...Object.values(counts));
      const scale = d3.scaleSequential().domain([0,maxC]).interpolator(d3.interpolate('#f0ebe0','#b87010'));
      addPaths(n => scale(n ? counts[n]||0 : 0));
      renderOverviewSignalOverlay(layer);
      renderOverviewLabels();
      updateLegend(layer);
    } else if (layer === 'aid') {
      const gbC = window.greenbookData ? (window.greenbookData.countries || []) : [];
      const byName = {}; gbC.forEach(c => { byName[c.country] = c.total_military || 0; });
      const maxA = Math.max(1, ...Object.values(byName));
      const scale = d3.scaleSequential().domain([0,maxA]).interpolator(d3.interpolate('#f0ebe0','#1a538f'));
      addPaths(n => scale(n ? byName[n]||0 : 0));
      renderOverviewSignalOverlay(layer);
      renderOverviewLabels();
      updateLegend(layer);
    } else { // conflict — V-Dem mil_exec
      const vdC = window.vdemData ? (window.vdemData.countries || []) : [];
      const byName = {}; vdC.forEach(c => { byName[c.country] = c.mil_exec != null ? c.mil_exec : 0; });
      const maxV = Math.max(0.01, ...Object.values(byName));
      const scale = d3.scaleSequential().domain([0,maxV]).interpolator(d3.interpolate('#f0ebe0','#a84000'));
      addPaths(n => scale(n ? byName[n]||0 : 0));
      renderOverviewSignalOverlay(layer);
      renderOverviewLabels();
      updateLegend(layer);
    }
  }
  _drawChoropleth = drawChoropleth;

  drawChoropleth();

  // Close popup on SVG background click
  ovSvg.on('click',function(evt){
    if(evt.target===this||evt.target.tagName==='svg') document.getElementById('ov-popup').style.display='none';
  });
}

function ovRefreshMarkers(){
  if(!ovTopoLoaded){ initExploreMap(); return; }
  if(_drawChoropleth) _drawChoropleth();
}

function showOvPopup(evt,d){
  const name=COUNTRY_NAMES_MAP[+d.id];
  if(!name) return;
  const wrap=document.getElementById('explore-map-wrap');
  const rect=wrap.getBoundingClientRect();
  const NAV_H=56, POPUP_W=288, PAD=14;
  const availH=wrap.clientHeight-NAV_H-PAD;
  let px=evt.clientX-rect.left+12, py=evt.clientY-rect.top-10;
  if(px+POPUP_W>wrap.clientWidth) px=Math.max(PAD,evt.clientX-rect.left-POPUP_W-8);
  if(py<PAD) py=PAD;
  const maxH=availH-py;
  const clampH=Math.max(120,Math.min(380,maxH));

  const layer=exCurrentMapLayer||'cmr';
  const prof=COUNTRY_PROFILES[name]||{};
  const stats=COUNTRY_STATS[name]||{spending:'—',personnel:'—',usAid:'—'};
  const thirtyAgo=new Date(Date.now()-30*864e5).toISOString().slice(0,10);
  const cEvs=allEvents.filter(ev=>matchesProfileCountryEvent(ev, name));
  const predictiveSummary=getCountryPredictiveSummary(name);
  const predictiveWatchpoints=Array.isArray(predictiveSummary?.watchpoints)?predictiveSummary.watchpoints.slice(0,2):[];
  const leadingMeta=getLeadingConstructMeta(name);

  // Layer label shown in header
  const LAYER_LABELS={
    cmr:'CMR Status',events:'Event Feed',aid:'US Security Aid',conflict:'Conflict Index',
    overall_risk:'Overall Risk',regime_vulnerability:'Regime Vulnerability',
    militarization:'Militarization',security_fragmentation:'Security Fragmentation'
  };
  const LAYER_COLORS={
    cmr:'var(--olive-mid)',events:'var(--purge)',aid:'var(--aid)',conflict:'var(--coup)',
    overall_risk:'#6f7f3d',regime_vulnerability:'var(--purge)',
    militarization:'var(--exercise)',security_fragmentation:'var(--oc)'
  };
  const layerLabel=LAYER_LABELS[layer]||'Overview';
  const layerColor=LAYER_COLORS[layer]||'var(--text-muted)';

  let statGrid='', bodyHtml='';

  // ── Analytical layer popups ──
  if(['overall_risk','regime_vulnerability','militarization','security_fragmentation'].includes(layer)){
    const cfg=getRegionalLayerConfig(layer);
    const score=cfg.score(name)||0;
    const scoreColor=getMonitorScoreColor(score);
    const detail=cfg.detail(name);
    const rv=getCountryRiskConstruct(name,'regime_vulnerability');
    const mil=getCountryRiskConstruct(name,'militarization');
    const sf=getCountryRiskConstruct(name,'security_fragmentation');

    if(layer==='overall_risk'){
      statGrid=`
        <div class="ov-stat" style="grid-column:1/-1;border-left:3px solid ${scoreColor};">
          <div class="ov-stat-val" style="color:${scoreColor};">${score}/100</div>
          <div class="ov-stat-lbl">Overall Risk Score</div>
        </div>
        <div class="ov-stat"><div class="ov-stat-val" style="color:${getMonitorScoreColor(rv?.score||0)};">${rv?.score||'—'}</div><div class="ov-stat-lbl">Regime Vuln.</div></div>
        <div class="ov-stat"><div class="ov-stat-val" style="color:${getMonitorScoreColor(mil?.score||0)};">${mil?.score||'—'}</div><div class="ov-stat-lbl">Militarization</div></div>
        <div class="ov-stat"><div class="ov-stat-val" style="color:${getMonitorScoreColor(sf?.score||0)};">${sf?.score||'—'}</div><div class="ov-stat-lbl">Sec. Fragmentation</div></div>`;
      const outlook=predictiveSummary?.overall_risk_level||'—';
      const trend=predictiveSummary?.leading_trend||'steady';
      const summaryText=predictiveSummary?.summary_text||detail;
      bodyHtml=`
        <div class="ov-popup-kicker">Monitor outlook</div>
        <div class="ov-popup-summary">${outlook} risk posture with a ${trend} trajectory. ${summaryText||''}</div>
        ${predictiveWatchpoints.length?`<div class="ov-popup-watch">
          <div class="ov-popup-kicker">Watch next</div>
          ${predictiveWatchpoints.map(point=>`<div class="ov-popup-watchpoint">${point}</div>`).join('')}
        </div>`:''}`;

    }else if(layer==='regime_vulnerability'){
      const rc=rv;
      statGrid=`
        <div class="ov-stat" style="grid-column:1/-1;border-left:3px solid ${scoreColor};">
          <div class="ov-stat-val" style="color:${scoreColor};">${score}/100</div>
          <div class="ov-stat-lbl">Regime Vulnerability</div>
        </div>
        <div class="ov-stat"><div class="ov-stat-val">${rc?.trend_label||'stable'}</div><div class="ov-stat-lbl">Trend</div></div>
        <div class="ov-stat"><div class="ov-stat-val">${prof.cmrStatus||'—'}</div><div class="ov-stat-lbl">CMR Status</div></div>
        <div class="ov-stat"><div class="ov-stat-val">${prof.regime||'—'}</div><div class="ov-stat-lbl">Regime type</div></div>`;
      const coupEvs=cEvs.filter(ev=>['coup','purge'].includes(ev.type));
      const coupHtml=coupEvs.slice().sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))).slice(0,3).map(ev=>`
        <div class="ov-popup-ev" data-id="${ev.id}">
          <div class="ov-popup-ev-dot" style="background:${TC_HEX[ev.type]||'#6a6560'}"></div>
          <div><span style="font-family:var(--mono);font-size:7.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">${ev.type} · ${ev.date}</span><br>${(ev.standard_title||ev.title||'Untitled').substring(0,68)}…</div>
        </div>`).join('');
      bodyHtml=`
        <div class="ov-popup-kicker">Why pressure is building</div>
        <div class="ov-popup-summary">${detail||'Executive-military friction and succession risk are the primary watchpoints.'}</div>
        ${coupHtml?`<div class="ov-popup-watch"><div class="ov-popup-kicker">Recent rupture signals</div>${coupHtml}</div>`:'<div class="ov-popup-summary">No coup- or purge-coded events are currently in the public store.</div>'}`;

    }else if(layer==='militarization'){
      const rc=mil;
      statGrid=`
        <div class="ov-stat" style="grid-column:1/-1;border-left:3px solid ${scoreColor};">
          <div class="ov-stat-val" style="color:${scoreColor};">${score}/100</div>
          <div class="ov-stat-lbl">Militarization</div>
        </div>
        <div class="ov-stat"><div class="ov-stat-val">${stats.spending}</div><div class="ov-stat-lbl">Mil. % GDP</div></div>
        <div class="ov-stat"><div class="ov-stat-val">${stats.personnel}</div><div class="ov-stat-lbl">Personnel</div></div>
        <div class="ov-stat"><div class="ov-stat-val">${rc?.trend_label||'stable'}</div><div class="ov-stat-lbl">Trend</div></div>`;
      bodyHtml=`
        <div class="ov-popup-kicker">What the indicator is capturing</div>
        <div class="ov-popup-summary">${detail||'The armed forces are taking on a wider operational or political footprint.'}</div>
        ${predictiveSummary?.summary_text?`<div class="ov-popup-watch"><div class="ov-popup-kicker">Monitor context</div><div class="ov-popup-summary">${predictiveSummary.summary_text}</div></div>`:''}`;

    }else{ // security_fragmentation
      const rc=sf;
      const ocConflEvs=cEvs.filter(ev=>['oc','conflict'].includes(ev.type));
      statGrid=`
        <div class="ov-stat" style="grid-column:1/-1;border-left:3px solid ${scoreColor};">
          <div class="ov-stat-val" style="color:${scoreColor};">${score}/100</div>
          <div class="ov-stat-lbl">Security Fragmentation</div>
        </div>
        <div class="ov-stat"><div class="ov-stat-val">${ocConflEvs.length}</div><div class="ov-stat-lbl">OC/conflict events</div></div>
        <div class="ov-stat"><div class="ov-stat-val">${ocConflEvs.filter(ev=>ev.date>=thirtyAgo).length}</div><div class="ov-stat-lbl">Active (30d)</div></div>
        <div class="ov-stat"><div class="ov-stat-val">${rc?.trend_label||'stable'}</div><div class="ov-stat-lbl">Trend</div></div>`;
      const fragHtml=ocConflEvs.slice().sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))).slice(0,3).map(ev=>`
        <div class="ov-popup-ev" data-id="${ev.id}">
          <div class="ov-popup-ev-dot" style="background:${TC_HEX[ev.type]||'#6a6560'}"></div>
          <div><span style="font-family:var(--mono);font-size:7.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">${ev.type} · ${ev.date}</span><br>${(ev.standard_title||ev.title||'Untitled').substring(0,68)}…</div>
        </div>`).join('');
      bodyHtml=`
        <div class="ov-popup-kicker">Fragmentation pattern</div>
        <div class="ov-popup-summary">${detail||'Armed non-state pressure and state weakness are elevating the coercive environment.'}</div>
        ${fragHtml?`<div class="ov-popup-watch"><div class="ov-popup-kicker">Recent security signals</div>${fragHtml}</div>`:'<div class="ov-popup-summary">No OC- or conflict-coded events are currently in the public store.</div>'}`;
    }

  }else if(layer==='cmr'){
    const CMR_COLOR={Authoritarian:'#8a1a1a',Crisis:'#b83232',Strained:'#c46e12',Stable:'#1a6e52'};
    const sc=CMR_COLOR[prof.cmrStatus]||'#6a6560';
    statGrid=`
      <div class="ov-stat" style="grid-column:1/-1;border-left:3px solid ${sc};">
        <div class="ov-stat-val" style="color:${sc};">${prof.cmrStatus||'—'}</div>
        <div class="ov-stat-lbl">CMR Status</div>
      </div>
      <div class="ov-stat"><div class="ov-stat-val">${prof.regime||'—'}</div><div class="ov-stat-lbl">Regime type</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${stats.spending}</div><div class="ov-stat-lbl">Mil. % GDP</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${stats.personnel}</div><div class="ov-stat-lbl">Personnel</div></div>`;
    const watch=typeof COUNTRY_WATCH!=='undefined'&&COUNTRY_WATCH[name];
    bodyHtml=watch
      ?`<div class="ov-popup-kicker">Analyst watch</div><div class="ov-popup-summary">${watch}</div>`
      :`<div class="ov-popup-summary">No watch note is currently available for this country.</div>`;

  }else if(layer==='events'){
    const count30=cEvs.filter(ev=>ev.date>=thirtyAgo).length;
    const typeCts={};
    cEvs.forEach(ev=>{ typeCts[ev.type]=(typeCts[ev.type]||0)+1; });
    const topType=Object.entries(typeCts).sort((a,b)=>b[1]-a[1])[0]?.[0]||'—';
    const highSal=cEvs.filter(ev=>ev.salience==='high').length;
    statGrid=`
      <div class="ov-stat"><div class="ov-stat-val">${count30}</div><div class="ov-stat-lbl">Events (30d)</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${cEvs.length}</div><div class="ov-stat-lbl">Total events</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${topType}</div><div class="ov-stat-lbl">Top type</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${highSal}</div><div class="ov-stat-lbl">High salience</div></div>`;
    const recent=cEvs.slice().sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))).slice(0,4);
    const evHtml=recent.map(ev=>`
      <div class="ov-popup-ev" data-id="${ev.id}">
        <div class="ov-popup-ev-dot" style="background:${TC_HEX[ev.type]||'#6a6560'}"></div>
        <div><span style="font-family:var(--mono);font-size:7.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">${ev.type} · ${ev.date}</span><br>${(ev.standard_title||ev.title||'Untitled').substring(0,68)}${(ev.standard_title||ev.title||'').length>68?'…':''}</div>
      </div>`).join('');
    bodyHtml=`
      <div class="ov-popup-kicker">Events pulse</div>
      <div class="ov-popup-summary">${count30} events in the last 30 days, led by ${topType==='—'?'mixed activity':`${topType} activity`}. ${highSal} of the current event set is high salience.</div>
      ${evHtml?`<div class="ov-popup-watch"><div class="ov-popup-kicker">Latest developments</div>${evHtml}</div>`:'<div class="ov-popup-summary">No events are currently stored for this country.</div>'}`;

  }else if(layer==='aid'){
    const gbC=(window.greenbookData?.countries||[]).find(c=>c.country===name);
    const totalMil=gbC?'$'+(gbC.total_military/1e6).toFixed(1)+'M':'—';
    const totalEco=gbC?'$'+((gbC.series||[]).reduce((s,r)=>s+(r.economic||0),0)/1e6).toFixed(1)+'M':'—';
    const aidEvs=cEvs.filter(ev=>ev.type==='aid');
    statGrid=`
      <div class="ov-stat"><div class="ov-stat-val">${stats.usAid}</div><div class="ov-stat-lbl">FY25 est.</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${totalMil}</div><div class="ov-stat-lbl">Military (all-time)</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${totalEco}</div><div class="ov-stat-lbl">Economic (all-time)</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${aidEvs.length}</div><div class="ov-stat-lbl">Aid events</div></div>`;
    const recentAid=aidEvs.slice().sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))).slice(0,3);
    const aidHtml=recentAid.map(ev=>`
      <div class="ov-popup-ev" data-id="${ev.id}">
        <div class="ov-popup-ev-dot" style="background:var(--aid)"></div>
        <div><span style="font-family:var(--mono);font-size:7.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">aid · ${ev.date}</span><br>${(ev.standard_title||ev.title||'Untitled').substring(0,68)}${(ev.standard_title||ev.title||'').length>68?'…':''}</div>
      </div>`).join('');
    bodyHtml=`
      <div class="ov-popup-kicker">Security cooperation picture</div>
      <div class="ov-popup-summary">Current aid posture is estimated at ${stats.usAid}, with ${totalMil} in all-time military obligations and ${totalEco} in economic support.</div>
      ${aidHtml?`<div class="ov-popup-watch"><div class="ov-popup-kicker">Recent cooperation signals</div>${aidHtml}</div>`:'<div class="ov-popup-summary">No aid-coded events are currently in the public store.</div>'}`;

  }else{ // conflict
    const vC=(window.vdemData?.countries||[]).find(c=>c.country===name);
    const milExec=vC&&vC.mil_exec!=null?vC.mil_exec.toFixed(2):'—';
    const polyarchy=vC&&vC.polyarchy!=null?vC.polyarchy.toFixed(2):'—';
    const conflEvs=cEvs.filter(ev=>['conflict','coup','protest'].includes(ev.type));
    const count30=conflEvs.filter(ev=>ev.date>=thirtyAgo).length;
    statGrid=`
      <div class="ov-stat"><div class="ov-stat-val">${milExec}</div><div class="ov-stat-lbl">Mil. constraint (V-Dem)</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${polyarchy}</div><div class="ov-stat-lbl">Polyarchy</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${conflEvs.length}</div><div class="ov-stat-lbl">Conflict events</div></div>
      <div class="ov-stat"><div class="ov-stat-val">${count30}</div><div class="ov-stat-lbl">Active (30d)</div></div>`;
    const recentConfl=conflEvs.slice().sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))).slice(0,3);
    const conflHtml=recentConfl.map(ev=>`
      <div class="ov-popup-ev" data-id="${ev.id}">
        <div class="ov-popup-ev-dot" style="background:${TC_HEX[ev.type]||'#6a6560'}"></div>
        <div><span style="font-family:var(--mono);font-size:7.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">${ev.type} · ${ev.date}</span><br>${(ev.standard_title||ev.title||'Untitled').substring(0,68)}${(ev.standard_title||ev.title||'').length>68?'…':''}</div>
      </div>`).join('');
    bodyHtml=`
      <div class="ov-popup-kicker">Conflict pressure</div>
      <div class="ov-popup-summary">${count30} conflict-relevant events in the last 30 days. The broader democratic environment is ${polyarchy==='—'?'not available':`tracked at ${polyarchy} on V-Dem polyarchy`}, while military executive constraint is ${milExec}.</div>
      ${conflHtml?`<div class="ov-popup-watch"><div class="ov-popup-kicker">Recent conflict and political signals</div>${conflHtml}</div>`:'<div class="ov-popup-summary">No conflict-relevant events are currently in the public store.</div>'}`;
  }

  const popup=document.getElementById('ov-popup');
  popup.innerHTML=`
    <div class="ov-popup-hdr">
      <div>
        <div class="ov-popup-kicker" style="color:${layerColor};">${layerLabel}</div>
        <span class="ov-popup-country">${name}</span>
      </div>
      <button class="ov-popup-close" id="ov-popup-x">×</button>
    </div>
    <div class="ov-popup-scroll">
      <div class="ov-stat-grid">${statGrid}</div>
      <div class="ov-popup-body">${bodyHtml}</div>
    </div>
    <div class="ov-popup-footer">
      <button class="ov-view-profile" data-country="${name}">Open full profile · ${leadingMeta.label} focus</button>
    </div>`;

  popup.style.display='flex';
  popup.style.left=px+'px';
  popup.style.top=py+'px';
  popup.style.maxHeight=clampH+'px';

  popup.querySelector('#ov-popup-x').onclick=()=>{ popup.style.display='none'; };
  popup.querySelectorAll('.ov-popup-ev').forEach(row=>{
    row.onclick=()=>{
      const ev=allEvents.find(e=>String(e.id)===row.dataset.id);
      if(!ev) return;
      popup.style.display='none';
      switchTab('events');
      selectEvent(ev);
    };
  });
  popup.querySelector('.ov-view-profile').onclick=function(){
    const country=this.dataset.country;
    popup.style.display='none';
    switchTab('profiles');
    setTimeout(()=>showCountryProfile(country),100);
  };
}

// ── TRANSNATIONAL SECURITY ───────────────────────────────────
function renderTsEvents(){
  const ocEvs=allEvents.filter(ev=>ev.type==='oc'||ev.type==='conflict');
  const el=document.getElementById('ts-event-list');
  const cnt=document.getElementById('ts-count');
  const card=document.getElementById('ts-card-count');
  if(cnt) cnt.textContent=ocEvs.length||'—';
  if(card) card.textContent=ocEvs.length||'—';
  if(!el||!ocEvs.length) return;
  el.innerHTML=ocEvs.slice(0,8).map(ev=>{
    const c=TC_HEX[ev.type]||'#6a6560';
    return `<div class="ev-item">
      <div class="ev-row1"><div class="ev-dot" style="background:${c}"></div><span class="ev-type" style="color:${c}">${ev.type}</span><span class="ev-country">${ev.country}</span></div>
      <div class="ev-title">${ev.title}</div>
      <div class="ev-meta"><span>${ev.date}</span><span>${ev.source}</span></div>
    </div>`;
  }).join('');
}

let _securityMapLoaded = false;

async function initSecurityMap() {
  if (_securityMapLoaded) return;
  _securityMapLoaded = true;
  const wrap = document.getElementById('security-map-wrap');
  if (!wrap) { _securityMapLoaded = false; return; }

  if (!worldFeatures) {
    try {
      const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
      worldFeatures = topojson.feature(world, world.objects.countries).features;
    } catch(e) {
      console.error('Security map: TopoJSON load failed', e);
      _securityMapLoaded = false; return;
    }
  }

  const acledWeights = { Extreme: 24, High: 16, Turbulent: 10, Low: 4 };
  const ocEvents = allEvents.filter(ev => ev.type === 'oc' || ev.type === 'conflict');
  const w = wrap.clientWidth || 700;
  const h = wrap.clientHeight || 440;
  const svg = d3.select('#security-map-svg')
    .attr('viewBox', `0 0 ${w} ${h}`)
    .attr('width','100%').attr('height','100%');
  const latamFeat = worldFeatures.filter(f => LATAM_IDS.has(+f.id));
  const proj = d3.geoMercator().fitExtent([[20,20],[w-20,h-20]], {
    type:'FeatureCollection', features:latamFeat
  });
  const path = d3.geoPath().projection(proj);
  const tooltip = d3.select('#security-map-tooltip');

  const pressureByCountry = {};
  (SUBREGIONS.all?.countries || []).forEach(country => {
    const evs = ocEvents.filter(ev => ev.country === country);
    const scoreFromEvents = evs.reduce((sum, ev) => {
      const base = ev.type === 'oc' ? 4 : 3;
      const salienceWeight = ev.salience === 'high' ? 3 : ev.salience === 'medium' ? 2 : 1;
      return sum + (base * salienceWeight);
    }, 0);
    const acledLevel = COUNTRY_ACLED[country]?.level;
    const acledScore = acledWeights[acledLevel] || 0;
    const total = scoreFromEvents + acledScore;
    pressureByCountry[country] = {
      score: total,
      ocEvents: evs.length,
      acledLevel: acledLevel || 'n/a'
    };
  });

  const maxScore = Math.max(1, ...Object.values(pressureByCountry).map(item => item.score));
  const colorScale = d3.scaleSequential()
    .domain([0, maxScore])
    .interpolator(d3.interpolate('#efe6f7','#6e2ea8'));

  svg.append('g').selectAll('path')
    .data(latamFeat).enter().append('path')
    .attr('d', path)
    .attr('fill', d => {
      const name = COUNTRY_NAMES_MAP[+d.id];
      const score = pressureByCountry[name]?.score || 0;
      return score ? colorScale(score) : '#ece7df';
    })
    .attr('stroke','#b8b2a4').attr('stroke-width',0.8)
    .style('cursor','pointer')
    .on('mouseover', function(evt, d) {
      d3.select(this).attr('stroke','#54504a').attr('stroke-width',2);
      const name = COUNTRY_NAMES_MAP[+d.id];
      if (!name) return;
      const item = pressureByCountry[name] || { score:0, ocEvents:0, acledLevel:'n/a' };
      const html = `<strong style="font-size:12px;color:var(--text);">${name}</strong>
        <br><span style="font-family:var(--mono);font-size:10px;color:var(--text-muted);">Pressure index</span> <strong style="color:var(--oc);">${item.score}</strong>
        <br><span style="font-size:10.5px;color:var(--text-muted);">${item.ocEvents} OC/conflict events · ACLED ${item.acledLevel}</span>`;
      const rect = wrap.getBoundingClientRect();
      tooltip.html(html)
        .style('display','block')
        .style('left', (evt.clientX - rect.left + 14) + 'px')
        .style('top',  (evt.clientY - rect.top  - 12) + 'px');
    })
    .on('mousemove', function(evt) {
      const rect = wrap.getBoundingClientRect();
      tooltip.style('left', (evt.clientX - rect.left + 14) + 'px')
             .style('top',  (evt.clientY - rect.top  - 12) + 'px');
    })
    .on('mouseout', function() {
      d3.select(this).attr('stroke','#b8b2a4').attr('stroke-width',0.8);
      tooltip.style('display','none');
    });

  svg.append('g').attr('pointer-events','none').selectAll('text')
    .data(Object.entries(COUNTRY_LABELS))
    .enter().append('text')
    .attr('x', d => proj(d[1][1])[0])
    .attr('y', d => proj(d[1][1])[1])
    .text(d => d[1][0])
    .attr('font-family','DM Mono,monospace').attr('font-size','8.5px')
    .attr('fill','rgba(28,26,23,0.55)').attr('text-anchor','middle');
}

// ── US COOPERATION LIVE EVENTS ────────────────────────────
function renderUsEvents(){
  const container=document.getElementById('us-live-evs');
  if(!container||!allEvents) return;
  const usEvs=allEvents.filter(ev=>ev.type==='aid'||ev.type==='coop'||ev.type==='exercise').sort((a,b)=>b.date.localeCompare(a.date)).slice(0,8);
  if(!usEvs.length) return;
  container.innerHTML=usEvs.map(ev=>`
    <div class="ev-item" style="cursor:pointer;" onclick="switchTab('events');setTimeout(()=>selectEvent(allEvents.find(e=>String(e.id)==='${ev.id}')),100)">
      <div class="ev-row1"><div class="ev-dot" style="background:${TC_HEX[ev.type]||'#6a6560'}"></div>
        <span class="ev-type" style="color:${TC_HEX[ev.type]||'#6a6560'}">${TYPE_LABEL[ev.type]||ev.type}</span>
        <span class="ev-country">${ev.country} · ${ev.date}</span>
      </div>
      <div class="ev-title">${ev.title}</div>
      <div class="ev-meta"><span>${ev.source||''}</span></div>
    </div>`).join('');
}

// ── US COOPERATION INTENSITY MAP ─────────────────────────────
let _usCoopMapLoaded = false;

async function initUsCoopMap() {
  if (_usCoopMapLoaded) return;
  _usCoopMapLoaded = true;
  const wrap = document.getElementById('us-coop-map-wrap');
  if (!wrap) { _usCoopMapLoaded = false; return; }

  // Reuse cached topology; lazy-load if Overview hasn't run yet
  if (!worldFeatures) {
    try {
      const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
      worldFeatures = topojson.feature(world, world.objects.countries).features;
    } catch(e) {
      console.error('US coop map: TopoJSON load failed', e);
      _usCoopMapLoaded = false; return;
    }
  }

  const US_AID_M = {
    "Colombia":461, "Mexico":332, "Haiti":187, "Peru":175,
    "Ecuador":138, "Honduras":83, "Guatemala":69, "Brazil":102,
    "El Salvador":46, "Costa Rica":20, "Dominican Republic":15,
    "Panama":15, "Guyana":4, "Jamaica":3, "Belize":2
  };
  const SANCTIONED = new Set(["Cuba","Venezuela","Nicaragua"]);

  const w = wrap.clientWidth || 700;
  const h = wrap.clientHeight || 440;

  const svg = d3.select('#us-coop-svg')
    .attr('viewBox', `0 0 ${w} ${h}`)
    .attr('width', '100%').attr('height', '100%');

  const latamFeat = worldFeatures.filter(f => LATAM_IDS.has(+f.id));
  const proj = d3.geoMercator().fitExtent([[20,20],[w-20,h-20]], {
    type:'FeatureCollection', features:latamFeat
  });
  const path = d3.geoPath().projection(proj);

  const maxAid = Math.max(...Object.values(US_AID_M));
  const colorScale = d3.scaleSequential()
    .domain([0, maxAid])
    .interpolator(d3.interpolate('#d4e4f5','#1a538f'));

  function fillColor(d) {
    const name = COUNTRY_NAMES_MAP[+d.id];
    if (!name) return '#e8e4dc';
    if (SANCTIONED.has(name)) return '#c9b8a4';
    const aid = US_AID_M[name];
    if (!aid) return '#e8e4dc';
    return colorScale(aid);
  }

  const tooltip = d3.select('#us-coop-tooltip');

  svg.append('g').selectAll('path')
    .data(latamFeat).enter().append('path')
    .attr('d', path)
    .attr('fill', fillColor)
    .attr('stroke','#b8b2a4').attr('stroke-width',0.8)
    .style('cursor','pointer')
    .on('mouseover', function(evt, d) {
      d3.select(this).attr('stroke','#54504a').attr('stroke-width',2);
      const name = COUNTRY_NAMES_MAP[+d.id];
      if (!name) return;
      const aid = US_AID_M[name];
      let html = `<strong style="font-size:12px;color:var(--text);">${name}</strong>`;
      if (SANCTIONED.has(name)) {
        html += `<br><span style="color:#c46e12;font-size:10.5px;">Sanctioned — no active coop</span>`;
      } else if (aid) {
        html += `<br><span style="font-family:var(--mono);font-size:10px;color:var(--text-muted);">FY2025 est.</span> <strong style="color:var(--aid);">$${aid}M</strong>`;
      } else {
        html += `<br><span style="color:var(--text-muted);font-size:10.5px;">No direct cooperation on record</span>`;
      }
      const rect = wrap.getBoundingClientRect();
      tooltip.html(html)
        .style('display','block')
        .style('left', (evt.clientX - rect.left + 14) + 'px')
        .style('top',  (evt.clientY - rect.top  - 12) + 'px');
    })
    .on('mousemove', function(evt) {
      const rect = wrap.getBoundingClientRect();
      tooltip.style('left', (evt.clientX - rect.left + 14) + 'px')
             .style('top',  (evt.clientY - rect.top  - 12) + 'px');
    })
    .on('mouseout', function() {
      d3.select(this).attr('stroke','#b8b2a4').attr('stroke-width',0.8);
      tooltip.style('display','none');
    });

  // Country labels (major countries only, same as Overview)
  svg.append('g').attr('pointer-events','none').selectAll('text')
    .data(Object.entries(COUNTRY_LABELS))
    .enter().append('text')
    .attr('x', d => proj(d[1][1])[0])
    .attr('y', d => proj(d[1][1])[1])
    .text(d => d[1][0])
    .attr('font-family','DM Mono,monospace').attr('font-size','8.5px')
    .attr('fill','rgba(28,26,23,0.55)').attr('text-anchor','middle')
    .attr('pointer-events','none');
}

// ── TOOLTIP ──────────────────────────────────────────────────
(function(){
  const tt=document.createElement('div');
  tt.className='tt';
  document.body.appendChild(tt);
  function pos(e){
    const x=e.clientX+14, y=e.clientY-10;
    tt.style.left=(x+tt.offsetWidth>window.innerWidth-10?e.clientX-tt.offsetWidth-14:x)+'px';
    tt.style.top=(y+tt.offsetHeight>window.innerHeight-10?e.clientY-tt.offsetHeight-10:y)+'px';
  }
  document.addEventListener('mouseover',e=>{
    const t=e.target.closest('[data-tooltip]');
    if(!t){tt.style.display='none';return;}
    tt.textContent=t.dataset.tooltip;
    tt.style.display='block';
    pos(e);
  });
  document.addEventListener('mousemove',e=>{ if(tt.style.display==='block') pos(e); });
  document.addEventListener('mouseout',e=>{
    const t=e.target.closest('[data-tooltip]');
    if(t&&!t.contains(e.relatedTarget)) tt.style.display='none';
  });
})();

// CMR Indicator definitions
const CMR_DEFS={
  'Conscription':'Country maintains mandatory military service. Indicates a mass-mobilization model with implications for civil-military ties and the socialization of civilians into military culture. (M3 Dataset, 2020)',
  'Military veto':'Military retains formal or informal veto over key civilian policy decisions — security appointments, defense budgets, or foreign policy. A core indicator of reserved military domains beyond civilian control. (M3 Dataset, 2020)',
  'Military impunity':'Military personnel are exempt from civilian judicial processes for offenses committed in the course of duty. Weakens accountability and civilian oversight mechanisms. (M3 Dataset, 2020)',
  'Crime policing':'Military is formally tasked with domestic law enforcement and crime control roles. Blurs the constitutional line between internal security and external defense. (M3 Dataset, 2020)',
  'Economic role':'Military owns or operates significant economic enterprises — corporations, businesses, or land holdings. Creates institutional interests independent of civilian budget authority. (M3 Dataset, 2020)',
  'HWI score':'Hybrid Warfare Index — composite score measuring institutional capacity for operations spanning conventional, cyber, information, and proxy domains. Higher values indicate greater hybrid capability. (M3 Dataset, 2020)',
};

// Mission status definitions
const MISSION_STATUS_DEFS={
  primary:    'Core constitutional mission — the primary justification for the military\'s existence, budget, and force structure.',
  active:     'Currently deployed or operationally engaged.',
  expanded:   'Mission scope has grown beyond historical or constitutional mandate, often reflecting militarization of civilian functions.',
  controversial:'Deployment faces political, legal, or human rights scrutiny.',
  routine:    'Recurring mission with low political salience and stable institutional role.',
};

// ── LANGUAGE ─────────────────────────────────────────────────
let currentLang='en';
const STRINGS={
  en:{
    'tab.events':'Events','tab.explore':'Explore','tab.profiles':'Countries','tab.transnational':'Organized Crime',
    'tab.us':'US-LatAm','tab.procurement':'Arms & Procurement','tab.timeline':'Timeline','tab.about':'About',
    'logo.sub':'LatAm Civil-Military Monitor',
    'label.events-loaded':'Events Loaded','label.countries-tracked':'Countries Tracked',
    'label.active-deals':'Active Deals (2024–26)','label.oc-events':'OC-Military Events (30d)',
    'label.timeline-events':'Events (Timeline)','label.latam-recipients':'All-time LatAm Recipients',
    'filter.subregion':'Subregion','filter.type':'Type','filter.domain':'Domain','filter.category':'Category','filter.signal':'Signal','filter.country':'Country',
    'filter.confidence':'Confidence','filter.date-range':'Date Range','filter.event-type':'Event Type',
    'filter.salience':'Salience','filter.conflict-level':'Conflict Level (ACLED)',
    'intro.events':'Events Feed','intro.us':'US-LatAm',
    'intro.procurement':'Procurement & Arms Transfers',
    'intro.transnational':'Organized Crime, Illicit Economies & Political Order',
    'intro.events.body':'Recent civil-military and security developments drawn from open-source reporting, organized into a public event monitor with confidence, sources, and country-level interpretation.',
    'log.pfx':'Log','ui.search':'Search','ui.search.placeholder':'Search events, countries…','ui.no-results':'No results found.',
    'lang.switch':'ES',
    'label.cmr-status':'CMR Status','label.key-stats':'Key Stats','label.key-positions':'Key Positions',
    'label.next-election':'Next Election','label.what-to-watch':'What to Watch',
    'label.cmr-indicators':'CMR Indicators','label.mil-missions':'Military Missions & Roles',
    'label.recent-events':'Recent Events','label.context':'Context',
    'label.all-countries':'All Countries','label.special-monitors':'Special Monitors',
    'label.regional-spending':'Regional Military Spending','label.top-spenders':'Top Military Spenders',
    'label.cmr-distribution':'CMR Status Distribution','label.coup-events':'Coup Events Since 1990',
    'label.mil-domestic':'Military in Domestic Security','label.us-aid-alltime':'All-Time US Security Aid',
    'label.stable':'Stable','label.strained':'Strained','label.crisis':'Crisis','label.authoritarian':'Authoritarian',
    'label.type-activity':'Type Activity','label.country-activity':'Country Activity',
    'filter.salience.high':'High','filter.salience.medium':'Medium','filter.salience.low':'Low',
    'filter.conf.green':'Verified','filter.conf.yellow':'Probable','filter.conf.red':'Unconfirmed',
    'label.events-feed':'Events Feed','label.map':'Map',
    'label.about-title':'About Sentinel.','label.about-sub':'A Latin American Civil-Military Events Monitor',
    'label.timeline-title':'Historical & Live Timeline',
    'label.timeline-body':'This timeline merges two layers: live events ingested nightly from open-source reporting and classified by AI, and historical milestones — coups, constitutions, peace accords, elections, and episodes of repression curated by the SENTINEL research team from 1988 to the present. Unlike the Events feed, which shows only recent pipeline output, the timeline is the longitudinal record. Milestones are marked with a square indicator and a category badge; live events with a colored dot by type. All filters apply to both layers.',
  },
  es:{
    'tab.events':'Eventos','tab.explore':'Explorar','tab.profiles':'Países','tab.transnational':'Crimen Organizado',
    'tab.us':'EE.UU.-LatAm','tab.procurement':'Armas y Adquisiciones','tab.timeline':'Cronología','tab.about':'Acerca de',
    'logo.sub':'Monitor Cívico-Militar de LatAm',
    'label.events-loaded':'Eventos Cargados','label.countries-tracked':'Países Monitoreados',
    'label.active-deals':'Acuerdos Activos (2024–26)','label.oc-events':'Eventos OC-Militares (30d)',
    'label.timeline-events':'Eventos (Cronología)','label.latam-recipients':'Receptores Históricos LatAm',
    'filter.subregion':'Subregión','filter.type':'Tipo','filter.domain':'Dominio','filter.category':'Categoría','filter.signal':'Señal','filter.country':'País',
    'filter.confidence':'Confianza','filter.date-range':'Rango de Fechas','filter.event-type':'Tipo de Evento',
    'filter.salience':'Relevancia','filter.conflict-level':'Nivel de Conflicto (ACLED)',
    'intro.events':'Boletín de Eventos','intro.us':'EE.UU.-LatAm',
    'intro.procurement':'Adquisiciones y Transferencias de Armas',
    'intro.transnational':'Crimen Organizado, Economías Ilícitas y Relaciones Cívico-Militares',
    'intro.events.body':'Desarrollos recientes de seguridad y relaciones cívico-militares a partir de fuentes abiertas, organizados en un monitor público con niveles de confianza, fuentes e interpretación por país.',
    'log.pfx':'Reg.','ui.search':'Buscar','ui.search.placeholder':'Buscar eventos, países…','ui.no-results':'Sin resultados.',
    'lang.switch':'EN',
    'label.cmr-status':'Estado RCM','label.key-stats':'Indicadores Clave','label.key-positions':'Cargos Clave',
    'label.next-election':'Próxima Elección','label.what-to-watch':'A Seguir',
    'label.cmr-indicators':'Indicadores RCM','label.mil-missions':'Misiones y Roles Militares',
    'label.recent-events':'Eventos Recientes','label.context':'Contexto',
    'label.all-countries':'Todos los Países','label.special-monitors':'Monitores Especiales',
    'label.regional-spending':'Gasto Militar Regional','label.top-spenders':'Mayores Gastos Militares (2025)',
    'label.cmr-distribution':'Distribución de Estado RCM','label.coup-events':'Golpes de Estado desde 1990',
    'label.mil-domestic':'Ejército en Seguridad Interna','label.us-aid-alltime':'Ayuda Militar EE.UU. (Histórica)',
    'label.stable':'Estable','label.strained':'Tensión','label.crisis':'Crisis','label.authoritarian':'Autoritario',
    'label.type-activity':'Actividad por Tipo','label.country-activity':'Actividad por País',
    'filter.salience.high':'Alta','filter.salience.medium':'Media','filter.salience.low':'Baja',
    'filter.conf.green':'Verificado','filter.conf.yellow':'Probable','filter.conf.red':'Sin confirmar',
    'label.events-feed':'Boletín de Eventos','label.map':'Mapa',
    'label.about-title':'Acerca de Sentinel.','label.about-sub':'Un Monitor Cívico-Militar de América Latina',
    'label.timeline-title':'Cronología Histórica y en Vivo',
    'label.timeline-body':'Esta cronología combina dos capas: eventos en vivo ingestados noche a noche a partir de fuentes abiertas y clasificados por IA, e hitos históricos — golpes, constituciones, acuerdos de paz, elecciones y episodios de represión — curados por el equipo de investigación de SENTINEL desde 1988. A diferencia del boletín de eventos, que muestra solo los resultados recientes del pipeline, la cronología es el registro longitudinal. Los hitos se marcan con un indicador cuadrado y una etiqueta de categoría; los eventos en vivo con un punto de color según el tipo. Todos los filtros aplican a ambas capas.',
  }
};

function toggleLang(){ setLang(currentLang==='en'?'es':'en'); }

function setLang(lang){
  currentLang=lang;
  const S=STRINGS[lang];
  // Tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn=>{
    const k='tab.'+btn.dataset.tab;
    if(S[k]) btn.textContent=S[k];
  });
  // Logo sub
  const _logoSub=document.querySelector('.logo-sub'); if(_logoSub) _logoSub.textContent=S['logo.sub'];
  // Lang button
  const lb=document.getElementById('lang-btn');
  lb.textContent=S['lang.switch'];
  lb.classList.toggle('lang-active',lang==='es');
  // All data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(el=>{
    const k=el.dataset.i18n;
    if(S[k]) el.textContent=S[k];
  });
  // Log prefix
  const pfx=document.querySelector('.log-pfx');
  if(pfx) pfx.textContent=S['log.pfx'];
  // Search placeholder
  const si=document.getElementById('search-input');
  if(si) si.placeholder=S['ui.search.placeholder'];
  document.documentElement.lang=lang;
}

// ── SEARCH ───────────────────────────────────────────────────
function openSearch(){
  document.getElementById('search-overlay').classList.add('open');
  const si=document.getElementById('search-input');
  si.value=''; document.getElementById('search-results').innerHTML='';
  setTimeout(()=>si.focus(),40);
}
function closeSearch(){ document.getElementById('search-overlay').classList.remove('open'); }

document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){ closeSearch(); closeFeedback(); }
  if((e.metaKey||e.ctrlKey)&&e.key==='k'){ e.preventDefault(); openSearch(); }
});

const TYPE_COLORS_S={coup:'var(--coup)',purge:'var(--purge)',conflict:'var(--conflict)',reform:'var(--reform)',aid:'var(--aid)',exercise:'var(--exercise)',oc:'var(--oc)',protest:'var(--protest)',peace:'var(--peace)',other:'var(--other)'};

function runSearch(q){
  const el=document.getElementById('search-results');
  const S=STRINGS[currentLang];
  q=q.trim().toLowerCase();
  if(!q){ el.innerHTML=''; return; }
  const results=[];
  // Events
  if(allEvents){
    allEvents.filter(ev=>
      (ev.title||'').toLowerCase().includes(q)||
      (ev.country||'').toLowerCase().includes(q)||
      (ev.summary||'').toLowerCase().includes(q)||
      (ev.location||'').toLowerCase().includes(q)
    ).slice(0,10).forEach(ev=>results.push({kind:'event',ev}));
  }
  // Country profiles
  Object.keys(COUNTRY_PROFILES||{}).filter(c=>c.toLowerCase().includes(q))
    .forEach(c=>results.push({kind:'country',name:c}));
  if(!results.length){ el.innerHTML=`<div class="s-empty">${S['ui.no-results']}</div>`; return; }
  el.innerHTML=results.map(r=>{
    if(r.kind==='event'){
      const ev=r.ev;
      const col=TYPE_COLORS_S[ev.type]||'var(--other)';
      return `<div class="s-item" onclick="closeSearch();switchTab('events');setTimeout(()=>selectEvent(allEvents.find(e=>e.id==='${ev.id}')),150)">
        <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:3px;">
          <span style="font-family:var(--mono);font-size:10px;letter-spacing:1px;text-transform:uppercase;color:${col}">${ev.type}</span>
          <span style="font-family:var(--mono);font-size:10px;color:var(--text-muted)">${ev.country}</span>
          <span style="font-family:var(--mono);font-size:10px;color:var(--text-faint);margin-left:auto">${ev.date}</span>
        </div>
        <div style="font-size:12.5px;color:var(--text);line-height:1.4">${ev.title}</div>
      </div>`;
    }
    return `<div class="s-item" onclick="closeSearch();switchTab('profiles');setTimeout(()=>showCountryProfile('${r.name}'),100)">
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--text-muted);margin-bottom:3px;">Country Profile</div>
      <div style="font-size:12.5px;color:var(--text)">${r.name}</div>
    </div>`;
  }).join('');
}

function isTrustedAnalystHost(){
  const host = String(window.location.hostname || '').toLowerCase();
  if(!host || host==='localhost' || host==='127.0.0.1' || host==='::1') return true;
  if(host.endsWith('.local')) return true;
  if(/^10\./.test(host)) return true;
  if(/^192\.168\./.test(host)) return true;
  const match = host.match(/^172\.(\d+)\./);
  if(match){
    const second = Number(match[1]);
    if(second >= 16 && second <= 31) return true;
  }
  return false;
}

function configureAnalystLoginLink(){
  const link = document.getElementById('analyst-login-link');
  if(!link) return;
  if(isTrustedAnalystHost()) return;
  link.classList.add('disabled');
  link.setAttribute('aria-disabled','true');
  link.removeAttribute('href');
  link.setAttribute('title','Private analyst access is available only from a trusted local or private host.');
  const label = link.querySelector('span');
  if(label) label.textContent = 'Private Analyst Access';
}

// ── INIT ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>{
  configureAnalystLoginLink();
  initEventFilterControls();
  initFeedbackPickers();
  loadEvents();
  fetch('data/cleaned/worldbank.json')
    .then(r => r.json())
    .then(d => {
      window.wbData = d;
      if (typeof exCurrentScene !== 'undefined' && exCurrentScene === 2) exRenderSpending();
    })
    .catch(() => { window.wbData = {}; });
  fetch('data/cleaned/greenbook.json')
    .then(r => r.json())
    .then(d => {
      window.greenbookData = d;
      if (typeof exCurrentScene !== 'undefined' && exCurrentScene === 3) exRenderAid();
    })
    .catch(() => { window.greenbookData = []; });
  fetch('data/cleaned/vdem.json')
    .then(r => r.json())
    .then(d => {
      window.vdemData = d;
      if (typeof exCurrentScene !== 'undefined' && exCurrentScene === 4) exRenderCmr();
    })
    .catch(() => { window.vdemData = {}; });
  updatePipelineAge();
  setInterval(updatePipelineAge, 1000);
  setInterval(loadEvents, 15*60*1000);
  setTimeout(renderCpRegionalMap,120);
  if(document.getElementById('events')?.classList.contains('active')) ensureEventMap();
  // Overview fade-up observer
  if(document.getElementById('overview') && document.getElementById('overview').classList.contains('active')) {
    const ovObs = new IntersectionObserver(entries => {
      entries.forEach(e => { if(e.isIntersecting){ e.target.classList.add('visible'); ovObs.unobserve(e.target); } });
    }, { threshold: 0.07 });
    document.querySelectorAll('.ov-fade').forEach(el => ovObs.observe(el));
  }
});

// ── Feedback Button ────────────────────────────────────
const FORMSPREE_ENDPOINT = 'https://formspree.io/f/xkopdkwd';

function toggleFeedback() {
  const panel = document.getElementById('fb-panel');
  panel.classList.contains('open') ? closeFeedback() : openFeedback();
}
function openFeedback() {
  const panel = document.getElementById('fb-panel');
  const btn = document.getElementById('fb-trigger');
  syncFeedbackPicker('category');
  syncFeedbackPicker('country');
  panel.classList.add('open');
  panel.removeAttribute('aria-hidden');
  btn.classList.add('is-active');
  btn.setAttribute('aria-expanded', 'true');
  document.getElementById('fb-category-picker-trigger')?.focus();
}
function closeFeedback() {
  const panel = document.getElementById('fb-panel');
  const btn = document.getElementById('fb-trigger');
  panel.classList.remove('open');
  panel.setAttribute('aria-hidden', 'true');
  btn.classList.remove('is-active');
  btn.setAttribute('aria-expanded', 'false');
  btn.focus();
}
function resetFeedbackForm() {
  document.getElementById('fb-form').reset();
  document.getElementById('fb-form').style.display = '';
  document.getElementById('fb-success').style.display = 'none';
  document.getElementById('fb-error').style.display = 'none';
  document.getElementById('fb-submit').disabled = false;
  syncFeedbackPicker('category');
  syncFeedbackPicker('country');
}
async function submitFeedback(e) {
  e.preventDefault();
  const category = document.getElementById('fb-category').value;
  const country  = document.getElementById('fb-country').value;
  const message  = document.getElementById('fb-message').value;
  const email    = document.getElementById('fb-email').value.trim();
  const errorEl  = document.getElementById('fb-error');
  const submitBtn = document.getElementById('fb-submit');

  const payload = {
    category,
    message,
    _subject: `SENTINEL Feedback — ${category}`
  };
  if (country) payload.country = country;
  if (email)   payload.email   = email;

  submitBtn.disabled = true;
  errorEl.style.display = 'none';

  try {
    const res = await fetch(FORMSPREE_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      document.getElementById('fb-form').style.display = 'none';
      document.getElementById('fb-success').style.display = 'block';
      setTimeout(() => { closeFeedback(); setTimeout(resetFeedbackForm, 300); }, 2000);
    } else {
      let msg = 'Something went wrong — try again.';
      try { const d = await res.json(); if (d.error) msg = d.error; } catch {}
      throw new Error(msg);
    }
  } catch(err) {
    errorEl.textContent = err.message || 'Something went wrong — try again.';
    errorEl.style.display = 'block';
    submitBtn.disabled = false;
  }
}

// Close panel on outside click
document.addEventListener('click', function(e) {
  const panel = document.getElementById('fb-panel');
  const btn   = document.getElementById('fb-trigger');
  if (panel.classList.contains('open') && !panel.contains(e.target) && !btn.contains(e.target)) {
    closeFeedback();
  }
});

// ── EXPLORE TAB ────────────────────────────────────────────────
const EX_SCENES = [
  { id: 'ex-scene-1', name: 'Regional Map',        onActivate: exActivateMap },
  { id: 'ex-scene-2', name: 'Event Timeline',      onActivate: exActivateTimeline },
  { id: 'ex-scene-3', name: 'Military Spending',   onActivate: exActivateSpending },
  { id: 'ex-scene-4', name: 'US Security Aid',     onActivate: exActivateAid },
  { id: 'ex-scene-5', name: 'Civil-Military Index',onActivate: exActivateCmr },
];
let exCurrentScene = 0;
let exMapInitialized = false;

function exSetScene(idx) {
  document.querySelectorAll('.ex-scene').forEach(s => s.classList.remove('ex-active'));
  document.getElementById(EX_SCENES[idx].id).classList.add('ex-active');
  document.querySelectorAll('.ex-dot').forEach((d, i) => d.classList.toggle('ex-dot-active', i === idx));
  exCurrentScene = idx;
  document.getElementById('ex-step').textContent = `Scene ${idx + 1} of ${EX_SCENES.length}`;
  document.getElementById('ex-prev-name').textContent = idx === 0 ? 'Home' : EX_SCENES[idx - 1].name;
  document.getElementById('ex-next-name').textContent = idx === EX_SCENES.length - 1 ? 'Events' : EX_SCENES[idx + 1].name;
  EX_SCENES[idx].onActivate();
}

function exGoPrev() {
  if (exCurrentScene === 0) { switchTab('overview'); }
  else { exSetScene(exCurrentScene - 1); }
}

function exGoNext() {
  if (exCurrentScene === EX_SCENES.length - 1) { switchTab('events'); }
  else { exSetScene(exCurrentScene + 1); }
}

function exInitDots() {
  const el = document.getElementById('ex-dots');
  if (el.children.length) return;
  EX_SCENES.forEach((s, i) => {
    const d = document.createElement('div');
    d.className = 'ex-dot' + (i === 0 ? ' ex-dot-active' : '');
    d.title = s.name;
    d.onclick = () => exSetScene(i);
    el.appendChild(d);
  });
}

// Wire control groups in Explore tab
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('#explore .ex-ctrl-group').forEach(group => {
    group.querySelectorAll('.ex-ctrl-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        group.querySelectorAll('.ex-ctrl-btn').forEach(b => b.classList.remove('ex-active-ctrl'));
        btn.classList.add('ex-active-ctrl');
      });
    });
  });

  const spendMetricGroup = document.getElementById('ex-spend-metric');
  if (spendMetricGroup) {
    spendMetricGroup.querySelectorAll('.ex-ctrl-btn').forEach(btn => {
      btn.addEventListener('click', () => { exSpendYear = 2024; exRenderSpending(); });
    });
  }
});

// Placeholder activate functions (filled in subsequent tasks)
function exActivateMap()      { if (!exMapInitialized) { initExploreMap(); exMapInitialized = true; } }
function exActivateTimeline() { renderTimeline(); }
function exActivateSpending() { exRenderSpending(); }
function exActivateAid()      { exRenderAid(); }
function exActivateCmr()      { exRenderCmr(); }
let exSpendMetric = 'pct_gdp';
let exSpendYear = 2024;
let exSpendPlaying = false;
let exSpendTimer = null;

function exCmrColor(country) {
  const p = COUNTRY_PROFILES[country];
  if (!p) return 'var(--text-muted)';
  if (p.cmrStatus === 'Crisis' || p.cmrStatus === 'Authoritarian') return 'var(--coup)';
  if (p.cmrStatus === 'Strained') return 'var(--purge)';
  return 'var(--reform)';
}

function exRenderSpending() {
  const container = document.getElementById('ex-spend-chart');
  const yearEl = document.getElementById('ex-spend-year');
  if (!container || !window.wbData) return;

  const metricBtn = document.querySelector('#ex-spend-metric .ex-active-ctrl');
  exSpendMetric = metricBtn ? metricBtn.dataset.metric : 'pct_gdp';

  const fmt = {
    pct_gdp:    v => v != null ? v.toFixed(1) + '%' : '—',
    usd:        v => v != null ? '$' + (v/1e9).toFixed(1) + 'B' : '—',
    per_capita: v => v != null ? '$' + Math.round(v).toLocaleString() : '—',
  };

  const wbCountries = window.wbData.countries || [];
  const yearStr = String(exSpendYear);

  const rows = wbCountries
    .map(c => {
      let value = null;
      if (exSpendMetric === 'per_capita') {
        const milSeries = c['military_expenditure_current_usd_series'] || [];
        const popSeries = c['population_total_series'] || [];
        const milData = milSeries.find(d => d.year === yearStr);
        const popData = popSeries.find(d => d.year === yearStr);
        if (milData && popData && popData.value > 0) value = milData.value / popData.value;
      } else {
        const key = exSpendMetric === 'pct_gdp' ? 'military_expenditure_pct_gdp' : 'military_expenditure_current_usd';
        const series = c[key + '_series'] || [];
        const yearData = series.find(d => d.year === yearStr);
        value = yearData ? yearData.value : null;
      }
      return { country: c.country, value };
    })
    .filter(r => r.value != null)
    .sort((a, b) => b.value - a.value)
    .slice(0, 15);

  if (!rows.length) {
    container.innerHTML = '<p style="padding:20px;color:var(--text-muted);font-family:var(--mono);font-size:10px;">No data available for selected year/metric.</p>';
    return;
  }

  const maxVal = rows[0].value;
  if (yearEl) yearEl.textContent = exSpendYear;

  container.innerHTML = rows.map((r, i) => `
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:var(--mono);font-size:10px;color:var(--text-muted);width:18px;text-align:right;flex-shrink:0;">${i+1}</span>
      <span style="font-family:var(--sans);font-size:12px;font-weight:600;width:120px;flex-shrink:0;text-align:right;">${r.country}</span>
      <div style="flex:1;height:26px;background:var(--surface);border-radius:4px;overflow:hidden;">
        <div style="height:100%;border-radius:4px;background:${exCmrColor(r.country)};width:${(r.value/maxVal*100).toFixed(1)}%;transition:width 0.8s ease-in-out;display:flex;align-items:center;justify-content:flex-end;padding-right:8px;">
          <span style="font-family:var(--mono);font-size:10px;color:rgba(255,255,255,0.85);">${fmt[exSpendMetric](r.value)}</span>
        </div>
      </div>
    </div>
  `).join('');
}

function exSpendTogglePlay() {
  exSpendPlaying = !exSpendPlaying;
  const btn = document.getElementById('ex-spend-play');
  if (exSpendPlaying) {
    btn.textContent = '⏸ Pause';
    if (exSpendYear >= 2024) exSpendYear = 1990;
    exSpendTimer = setInterval(() => {
      exSpendYear++;
      exRenderSpending();
      if (exSpendYear >= 2024) {
        exSpendPlaying = false;
        clearInterval(exSpendTimer);
        btn.textContent = '▶ Animate 1990–2024';
      }
    }, 600);
  } else {
    clearInterval(exSpendTimer);
    btn.textContent = '▶ Animate 1990–2024';
  }
}
function exRenderAid() {
  const container = document.getElementById('ex-aid-chart');
  if (!container || !window.greenbookData) return;

  const typeBtn   = document.querySelector('#ex-aid-type .ex-active-ctrl');
  const periodBtn = document.querySelector('#ex-aid-period .ex-active-ctrl');
  const aidType   = typeBtn   ? typeBtn.dataset.aid    : 'military';
  const period    = periodBtn ? periodBtn.dataset.period : 'all';

  const PERIOD_START = { all: 0, '2020': 2020, '2010': 2010 };
  const startYear = PERIOD_START[period] || 0;
  const endYear   = period === '2020' ? 2025 : period === '2010' ? 2019 : 9999;

  const gbCountries = (window.greenbookData.countries || window.greenbookData || []);
  const totals = {};
  gbCountries.forEach(c => {
    const name = c.country;
    if (!name) return;
    const series = c.series || [];
    series.forEach(s => {
      if (s.year < startYear || s.year > endYear) return;
      if (!totals[name]) totals[name] = { military: 0, economic: 0 };
      totals[name].military += (s.military || 0);
      totals[name].economic += (s.economic || 0);
    });
  });

  const rows = Object.entries(totals)
    .map(([country, v]) => ({
      country,
      military: v.military,
      economic: v.economic,
      total: aidType === 'military' ? v.military : aidType === 'economic' ? v.economic : v.military + v.economic,
    }))
    .filter(r => r.total > 0)
    .sort((a, b) => b.total - a.total)
    .slice(0, 12);

  if (!rows.length) {
    container.innerHTML = '<p style="padding:20px;color:var(--text-muted);font-family:var(--mono);font-size:10px;">No data for selected filters.</p>';
    return;
  }

  const maxVal = rows[0].total;
  const fmtB = v => '$' + (v / 1e9).toFixed(1) + 'B';

  const legendHtml = aidType === 'both'
    ? `<div style="display:flex;gap:18px;margin-bottom:12px;">
        <span style="display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;color:var(--text-dim)"><span style="width:10px;height:10px;border-radius:2px;background:var(--aid);display:inline-block;"></span>Military</span>
        <span style="display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;color:var(--text-dim)"><span style="width:10px;height:10px;border-radius:2px;background:var(--reform);display:inline-block;"></span>Economic</span>
      </div>` : '';

  container.innerHTML = legendHtml + rows.map(r => {
    if (aidType === 'both') {
      const milPct = (r.military / maxVal * 100).toFixed(1);
      const ecoPct = (r.economic / maxVal * 100).toFixed(1);
      return `<div style="display:flex;align-items:center;gap:10px;">
        <span style="font-family:var(--sans);font-size:12px;font-weight:600;width:130px;flex-shrink:0;text-align:right;">${r.country}</span>
        <div style="flex:1;display:flex;height:22px;border-radius:3px;overflow:hidden;background:var(--surface);">
          <div style="width:${milPct}%;background:var(--aid);opacity:0.85;transition:width 0.8s ease-in-out;"></div>
          <div style="width:${ecoPct}%;background:var(--reform);opacity:0.85;transition:width 0.8s ease-in-out;"></div>
        </div>
        <span style="font-family:var(--mono);font-size:10px;color:var(--text-muted);width:50px;">${fmtB(r.total)}</span>
      </div>`;
    }
    const color = aidType === 'military' ? 'var(--aid)' : 'var(--reform)';
    return `<div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:var(--sans);font-size:12px;font-weight:600;width:130px;flex-shrink:0;text-align:right;">${r.country}</span>
      <div style="flex:1;height:22px;background:var(--surface);border-radius:3px;overflow:hidden;">
        <div style="height:100%;background:${color};opacity:0.85;width:${(r.total/maxVal*100).toFixed(1)}%;transition:width 0.8s ease-in-out;border-radius:3px;"></div>
      </div>
      <span style="font-family:var(--mono);font-size:10px;color:var(--text-muted);width:50px;">${fmtB(r.total)}</span>
    </div>`;
  }).join('');
}
const EX_CMR_INDICATORS = [
  { key: 'polyarchy',     label: 'Polyarchy',       invert: false },
  { key: 'mil_constrain', label: 'Mil. constraint',  invert: false },
  { key: 'physinteg',     label: 'Phys. integrity',  invert: false },
  { key: 'cs_repress',    label: 'CS repression',    invert: true  },
];

const EX_COUNTRY_REGION = {
  'Brazil':'Brazil','Colombia':'Andean','Mexico':'Mexico','Venezuela':'Andean',
  'Chile':'Southern Cone','Argentina':'Southern Cone','Peru':'Andean','Ecuador':'Andean',
  'Bolivia':'Andean','Cuba':'Caribbean','Honduras':'Central America','Guatemala':'Central America',
  'El Salvador':'Central America','Nicaragua':'Central America','Paraguay':'Southern Cone',
  'Uruguay':'Southern Cone','Haiti':'Caribbean','Dominican Republic':'Caribbean',
  'Panama':'Central America','Costa Rica':'Central America','Jamaica':'Caribbean',
  'Trinidad and Tobago':'Caribbean','Guyana':'Caribbean','Suriname':'Caribbean',
  'Belize':'Central America',
};

function exRenderCmr() {
  const container = document.getElementById('ex-cmr-chart');
  const summary = document.getElementById('ex-cmr-summary');
  if (!container || !window.vdemData) return;

  const regionBtn = document.querySelector('#ex-cmr-region .ex-active-ctrl');
  const yearBtn   = document.querySelector('#ex-cmr-year .ex-active-ctrl');
  const region    = regionBtn ? regionBtn.dataset.region : 'all';
  const year      = yearBtn   ? parseInt(yearBtn.dataset.year) : 2023;

  const vdemCountries = window.vdemData.countries || [];
  const filtered = vdemCountries.filter(c => {
    if (region === 'all') return true;
    return EX_COUNTRY_REGION[c.country] === region;
  });

  if (!filtered.length) {
    if (summary) summary.innerHTML = '';
    container.innerHTML = '<p style="padding:20px;color:var(--text-muted);font-family:var(--mono);font-size:10px;">No data.</p>';
    return;
  }

  const statusCounts = filtered.reduce((acc, c) => {
    const status = COUNTRY_PROFILES[c.country]?.cmrStatus || 'Stable';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});
  const dominantStatusEntry = Object.entries(statusCounts).sort((a, b) => b[1] - a[1])[0] || ['Stable', filtered.length];
  const dominantColor = dominantStatusEntry[0] === 'Crisis' || dominantStatusEntry[0] === 'Authoritarian'
    ? 'var(--coup)'
    : dominantStatusEntry[0] === 'Strained'
      ? 'var(--purge)'
      : 'var(--reform)';

  if (summary) {
    summary.innerHTML = `
      <div class="ex-cmr-summary-card lead">
        <div class="ex-cmr-summary-kicker">Monitor brief</div>
        <div class="ex-cmr-summary-title">Civil-military posture at a glance</div>
        <div class="ex-cmr-summary-copy">This scene compares core institutional indicators across the selected subregion. Use it to scan where civilian control is holding, where institutional strain is accumulating, and where coercive governance is becoming the dominant pattern.</div>
      </div>
      <div class="ex-cmr-summary-card">
        <div class="ex-cmr-summary-kicker">Visible set</div>
        <div class="ex-cmr-summary-stat">
          <div class="ex-cmr-summary-value">${filtered.length}</div>
          <div class="ex-cmr-summary-note">${region === 'all' ? 'all monitored countries' : `${region} focus`}</div>
        </div>
      </div>
      <div class="ex-cmr-summary-card">
        <div class="ex-cmr-summary-kicker">Dominant posture</div>
        <div class="ex-cmr-summary-stat">
          <div class="ex-cmr-summary-value" style="color:${dominantColor};">${dominantStatusEntry[0]}</div>
          <div class="ex-cmr-summary-note">${dominantStatusEntry[1]} of ${filtered.length} in ${year}</div>
        </div>
      </div>`;
  }

  container.innerHTML = filtered.map(c => {
    const country = c.country;
    const profile = COUNTRY_PROFILES[country] || {};
    const cmrStatus = profile.cmrStatus || 'Stable';
    const borderColor = cmrStatus === 'Crisis' || cmrStatus === 'Authoritarian' ? 'var(--coup)'
                      : cmrStatus === 'Strained' ? 'var(--purge)' : 'var(--reform)';

    const bars = EX_CMR_INDICATORS.map(ind => {
      const indSeries = (c.series && c.series[ind.key]) || [];
      const yearData = indSeries.find(d => d.year === year);
      let val = yearData ? yearData.value : (c[ind.key] != null ? c[ind.key] : 0);
      if (val == null) val = 0;
      if (ind.invert) val = 1 - val;
      const pct = Math.min(100, Math.max(0, val * 100)).toFixed(0);
      return `<div class="ex-cmr-bar-row">
        <span class="ex-cmr-bar-label">${ind.label}</span>
        <div class="ex-cmr-bar-track">
          <div class="ex-cmr-bar-fill" style="width:${pct}%;color:${borderColor};"></div>
        </div>
      </div>`;
    }).join('');

    return `<div class="ex-cmr-card" style="border-left-color:${borderColor};">
      <div class="ex-cmr-card-head">
        <div class="ex-cmr-country">${country}</div>
        <div class="ex-cmr-status" style="color:${borderColor};">${cmrStatus}</div>
      </div>
      <div class="ex-cmr-bars">${bars}</div>
    </div>`;
  }).join('');
}

// Map layer select for Scene 1 — handled via inline onchange
document.addEventListener('DOMContentLoaded', () => {
  ['ex-aid-type', 'ex-aid-period'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.querySelectorAll('.ex-ctrl-btn').forEach(btn => {
      btn.addEventListener('click', () => exRenderAid());
    });
  });

  ['ex-cmr-region', 'ex-cmr-year'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.querySelectorAll('.ex-ctrl-btn').forEach(btn => {
      btn.addEventListener('click', () => exRenderCmr());
    });
  });
});

function toggleUsSF(evt) {
  const body = document.getElementById('us-sf-body');
  const icon = document.getElementById('us-sf-toggle-icon');
  if (!body) return;
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : 'block';
  if (icon) icon.textContent = open ? '▼ Read full analysis' : '▲ Collapse';
}

function toggleProfilesSF(evt) {
  const body = document.getElementById('profiles-sf-body');
  const icon = document.getElementById('profiles-sf-toggle-icon');
  if (!body) return;
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : 'block';
  if (icon) icon.textContent = open ? '▼ Read full focus' : '▲ Collapse';
}

function exUpdateMapLayer(layer) {
  exCurrentMapLayer = layer;
  const sel = document.getElementById('ex-map-layer-select');
  if (sel && sel.value !== layer) sel.value = layer;
  if (_drawChoropleth) _drawChoropleth();
}
