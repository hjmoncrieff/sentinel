# Private Source Enrichment And Latent Variable Note

## Purpose

This note records the next concrete work around:

- event-content enrichment after event discovery
- official US military cooperation monitoring through SOUTHCOM
- police-force information for Latin America and the Caribbean
- latent-variable design for civilian control and militarization

The goal is to improve both:

- the factual depth of event records
- the medium-term modeling base for coercive politics and political risk

## Local-Only Materials Rule

The Kenwick replication materials and any raw `dataverse*` archives are for
local inspection only.

Never commit or push:

- `data/raw/Coup Latent Variable/`
- `data/raw/dataverse*`

## 1. Open Source Enrichment Strategy

The working rule is:

- do not depend on unlawful paywall bypassing
- instead, use open wire services, official statements, and open secondary
  coverage to reconstruct event context once the event is identified

Best enrichment layer:

- `EFE`
- `AP`
- `AFP`
- `Reuters`
- `Agência Brasil`
- `BBC Mundo`
- `El País América`
- official ministry / command / press-release pages

These sources are often sufficient to recover:

- event description
- actors
- place
- official response
- mechanism
- immediate consequences

### Event-enrichment workflow

Once an event is detected:

1. keep the source article as the discovery trigger
2. expand context through:
   - wire coverage
   - official statements
   - open secondary reporting
   - Google News site-scoped discovery
3. store enriched article context in the canonical article layer
4. keep the public/dashboard analysis grounded in those enriched article
   descriptions rather than only the headline or initial snippet

## 2. Google News Use

Google News should be treated as a discovery layer, not a truth layer.

Best use:

- site-scoped RSS for sources with weak or missing native RSS
- official-site discovery
- fast event-context expansion around a known event

Priority uses:

- `EFE`
- `Notimérica`
- `Agência Brasil`
- defense ministries
- public-security ministries
- command and press-release pages

Working rule:

- direct RSS first
- Google News site-scoped RSS second
- targeted scraping third

## 3. SOUTHCOM Official Monitoring

SOUTHCOM should remain a dedicated official-source channel for:

- military cooperation
- exercises
- partner-force assistance
- logistics and support
- humanitarian and disaster-response security operations
- command visits
- policy and signaling tied to US regional force posture

### Minimum official SOUTHCOM layer

- `SOUTHCOM News`
- `SOUTHCOM Press Releases`
- `SOUTHCOM RSS`
  - `https://www.southcom.mil/RSS/`
- `DVIDS` items tied to SOUTHCOM

### SOUTHCOM rule

The project should treat SOUTHCOM as:

- official cooperation reporting
- not neutral baseline reporting

Its value is:

- documenting the official US military cooperation channel in the region
- identifying exercises, deployments, partnerships, and doctrine signals
- improving coverage of `US-LatAm` cooperation events

## 4. Official Defense And Security Sources

The current ministry expansion logic should continue to distinguish:

- defense ministries where they exist
- public-security ministries where defense ministries are structurally weak,
  absent, or not the right analogue

This is especially important for:

- Costa Rica
- Panama

These sources should be used primarily for:

- command changes
- exercises
- cooperation agreements
- procurement and acquisition announcements
- public-security missions
- state security framing

## 5. Police Information In The Region

Reliable regional police information exists, but it is patchy.

Best baseline sources:

- `UNODC`
  - criminal justice personnel and police-related capacity data
  - `https://dataunodc.un.org`
- `OAS Inter-American Security Observatory`
  - police personnel indicators
  - `https://www.oas.org/ios/`
- `Our World in Data` / Hanson-Sigman derived police personnel series
  - useful as a processed comparison layer

These are good for:

- structural comparison
- country-level staffing baselines
- slower-moving comparative indicators

They are not sufficient alone for:

- current operational posture
- mission creep
- police militarization
- hybrid-force use

For those, the system should also use:

- national police annual reports
- public-security ministry reports
- police budget documents
- force-strength statements where official and attributable

## 6. Latent Variable Direction

## 6.0 Kenwick Model Structure And Reuse

The local replication materials in:

- `data/raw/Coup Latent Variable/`

show that Kenwick's civilian-control work is built as:

- a static ordinal IRT model
- plus a dynamic `drift` version that carries the latent score forward
  regime-year by regime-year

Core local files:

- `data/raw/Coup Latent Variable/irt_modeling/data_prep.R`
- `data/raw/Coup Latent Variable/irt_modeling/static_model.stan`
- `data/raw/Coup Latent Variable/irt_modeling/drift_model.stan`
- `data/raw/Coup Latent Variable/Data/civiliancontrolscores.csv`

The released score file includes:

- `ccs_static`
- `ccs_static_sd`
- `ccs_dynamic`
- `ccs_dynamic_sd`

### Kenwick manifest indicators

The appendix and replication files show the following indicator families:

- military entry into office
- military leader in office
- military participation in government
- military involvement in politics
- militarism index
- military regime coding
- prior military regime coding
- military leader experience

These are highly useful as a template, but should not be copied wholesale into
SENTINEL. The right adaptation path is:

- keep the modeling structure
- rebuild the indicator layer for a Latin America and Caribbean political-risk
  application

### 6.0A M3 structural layer

The local `M3` dataset should be treated as a major structural input layer for
both latent-variable projects.

Local files:

- `data/raw/M3-Dataset-V1.xlsx`
- `data/raw/M3-Codebook-V1.pdf`

Most useful current M3 fields for SENTINEL:

- `com_mil_serv`
- `com_mil_serv_gen`
- `com_mil_serv_dur_max`
- `com_mil_serv_dur_min`
- `alt_civ_serv`
- `mil_origin`
- `mil_leader`
- `mil_mod`
- `mil_veto`
- `mil_repress`
- `mil_repress_count`
- `mil_impun`
- `milpol_crime`
- `milpol_law`
- `milpol_peace`
- `mil_police`
- `mil_eco_dummy`
- `mil_eco_own`
- `mil_eco_share`
- `mil_eco_dom`
- `milex_gdp`
- `milex_healthexp`
- `pers_to_pop`
- `pers_to_phy`
- `reserve_pop`
- `hwi`

Interpretive rule:

- `V-Dem` anchors long-run regime and accountability conditions
- `M3` anchors military role structure and reserved domains
- `SENTINEL` event coding anchors temporal escalation and operational practice

### 6A. Civilian Control latent variable

A medium-term latent-variable project is feasible.

The idea would be similar in spirit to Michael Kenwick-style latent modeling:

- combine multiple imperfect indicators
- estimate a cleaner underlying dimension
- use it as a private/internal analytic and modeling input

Candidate indicator families for `civilian_control_latent`:

- defense minister civilian status
- executive control over promotions and appointments
- purge / reshuffle frequency in coercive institutions
- military veto episodes
- coup attempts / coup exposure
- emergency-rule reliance
- military domestic deployment intensity
- military role in policing, prisons, borders, protest management
- autonomy over procurement and budget
- judicial or legal impunity around military abuse

Interpretive meaning:

- how strongly civilian authorities control coercive institutions in practice
- not merely in constitutional form

### 6A.1 V-Dem candidates for a long-run civilian-control backbone

The current cleaned V-Dem layer already contains several variables that can
anchor a long historical series.

Most useful current V-Dem candidates in `data/cleaned/vdem.json`:

- `mil_constrain`
  - military constraints on executive
  - strongest current direct proxy for civilian control
- `mil_exec`
  - whether the executive is a military officer
  - useful as a direct military-political fusion indicator
- `coup_event`
  - coup event occurrence
- `coup_attempts`
  - attempted coups
- `coup_total_events`
  - broader coup-event load
- `regime_type`
  - background regime context
- `polyarchy`
  - democratic openness baseline
- `executive_direct_election`
  - executive selection context
- `legislative_constraints`
  - horizontal constraints background
- `judicial_constraints`
  - horizontal constraints background
- `rule_of_law_vdem`
  - legal-institutional baseline
- `cs_repress`
  - coercive management of dissent
- `political_violence`
  - coercive contestation context
- `election_repression`
  - coercive manipulation around political competition
- `exec_confidence`
  - executive-legislative confidence structure
- `executive_corruption`
  - executive abuse / patrimonialization context

Best immediate long-run backbone:

- `mil_constrain`
- `mil_exec`
- `coup_event`
- `coup_attempts`
- `regime_type`
- `polyarchy`
- `judicial_constraints`
- `legislative_constraints`
- `rule_of_law_vdem`

### 6A.2 M3 candidates for civilian-control design

Most useful current M3 candidates for `civilian_control_latent`:

- `mil_origin`
- `mil_leader`
- `mil_mod`
- `mil_veto`
- `mil_impun`
- `mil_repress`
- `mil_repress_count`
- `milpol_crime`
- `milpol_law`
- `milpol_peace`
- `mil_police`

How M3 helps here:

- V-Dem is stronger on regime-level accountability and contestation
- M3 is stronger on reserved military domains and formal or informal military
  encroachment
- together they get much closer to the practical meaning of civilian control

### 6A.3 Recommended structure for SENTINEL civilian control

For a first SENTINEL version, the item families should probably be divided into:

- direct coercive-autonomy indicators
  - `mil_constrain`
  - `mil_exec`
  - coup attempt / coup event load
- institutional constraint indicators
  - `judicial_constraints`
  - `legislative_constraints`
  - `rule_of_law_vdem`
- coercive-political stress indicators
  - `cs_repress`
  - `election_repression`
  - `political_violence`
- SENTINEL event-derived escalation indicators
  - coup-coded events
  - purge / reshuffle patterns
  - military domestic-role expansion
  - military veto or refusal episodes

The clean modeling rule is:

- V-Dem provides the long-run annual backbone
- SENTINEL events provide the higher-frequency update layer
- the latent variable should remain annual at first, with later bridging into
  private monthly modeling if justified

### 6B. Militarization latent variable

A separate latent variable should be built for militarization.

Candidate indicator families for `militarization_latent`:

- military domestic-security deployment
- constabularization / police substitution
- internal-security mission burden
- defense spending and procurement tempo
- special legal authorities for military use
- military role in prisons, borders, intelligence, protest control
- police militarization / hybrid force structure
- armed-force role in executive governance

Interpretive meaning:

- the extent to which political order and internal security are being organized
  through military institutions or military-style coercion

### 6B.1 V-Dem candidates for a long-run militarization backbone

V-Dem is weaker for militarization than for civilian control, but still useful
for part of the construct.

Most useful current V-Dem candidates:

- `mil_exec`
  - military officer as executive
- `mil_constrain`
  - lower civilian constraint can support militarization inference
- `cs_repress`
  - coercive use of the state against civil society
- `political_violence`
  - coercive contestation environment
- `election_repression`
  - coercive use during political competition
- `regime_type`
  - regime context
- `polyarchy`
  - democratic constraint background

But militarization will require more non-V-Dem inputs than civilian control.

### 6B.2 M3 candidates for militarization design

Most useful current M3 candidates for `militarization_latent`:

- `com_mil_serv`
- `com_mil_serv_gen`
- `com_mil_serv_dur_max`
- `com_mil_serv_dur_min`
- `alt_civ_serv`
- `milpol_crime`
- `milpol_law`
- `milpol_peace`
- `mil_police`
- `mil_repress`
- `mil_repress_count`
- `mil_eco_dummy`
- `mil_eco_own`
- `mil_eco_share`
- `mil_eco_dom`
- `milex_gdp`
- `milex_healthexp`
- `pers_to_pop`
- `pers_to_phy`
- `reserve_pop`
- `hwi`

How M3 helps here:

- it directly captures militarized institutional design, not just regime stress
- it provides annual structural inputs on military size, domestic role, and
  institutional autonomy
- it should be one of the main anchors of `militarization_latent`, alongside
  event-derived SENTINEL measures

### 6B.3 Recommended structure for SENTINEL militarization

For `militarization_latent`, the likely design should combine:

- V-Dem annual background
  - `mil_exec`
  - `mil_constrain`
  - `cs_repress`
  - `political_violence`
  - `election_repression`
- M3 annual structural role indicators
- structural slow-moving inputs
  - military expenditure
  - military personnel
  - police personnel, where available
  - police / military institutional design
- SENTINEL annualized event indicators
  - domestic military deployment
  - military role in public order
  - role in prisons / borders / policing
  - exceptional-rule militarization
  - militarized protest response
  - security-cooperation patterns that directly expand domestic military role

### 6B.4 Police-force information in the latent design

Police information is likely to be essential for the militarization side.

The most useful role for police data is:

- identifying where the state is police-led vs military-led in domestic order
- distinguishing militarization from simple coercive capacity
- capturing police substitution or hybridization

Best candidate baseline inputs:

- UNODC police / criminal justice personnel
- OAS police personnel indicators
- national police annual reports
- public-security ministry publications

This is especially important because militarization is partly about whether the
military is replacing or overshadowing police institutions in internal order.

### 6C. Separation rule

The project should keep these constructs separate:

- `civilian_control_latent`
- `militarization_latent`

They are related but not identical.

Examples:

- a country can have weak civilian control without a maximally militarized
  domestic order
- a country can be highly militarized even where executive control over the
  military is still relatively strong

## 7. Recommended Next Implementation Sequence

### Near term

1. strengthen the event-content enrichment layer
2. keep SOUTHCOM as a dedicated official cooperation channel
3. improve police baseline data collection
4. document candidate inputs for civilian control and militarization
5. make M3 a formal structural input in that design layer

### Medium term

1. build a police / public-security structural input layer
2. assemble candidate annual indicators for:
   - civilian control
   - militarization
3. add M3 variables explicitly to that annual inventory
4. test a first private latent-variable prototype

### Rule

Do not start latent-variable fitting until:

- actor quality is stronger
- source enrichment is more stable
- police and official-defense input coverage is documented
- M3 variable coverage is documented

The next stage is design and data assembly, not immediate fitting.

## 8. First Concrete SENTINEL Design Proposal

### 8A. Civilian control v0

Recommended first annual indicator basket:

- `mil_constrain`
- `mil_exec`
- `coup_event`
- `coup_attempts`
- `judicial_constraints`
- `legislative_constraints`
- `rule_of_law_vdem`
- `cs_repress`
- `election_repression`
- M3-derived:
  - `mil_origin`
  - `mil_leader`
  - `mil_mod`
  - `mil_veto`
  - `mil_impun`
  - `milpol_crime`
  - `milpol_law`
  - `milpol_peace`
  - `mil_police`
- event-derived:
  - coup-coded events
  - purge / reshuffle events
  - military veto / refusal coding
  - military domestic-governance role coding

### 8B. Militarization v0

Recommended first annual indicator basket:

- `mil_exec`
- `mil_constrain`
- `cs_repress`
- `political_violence`
- M3-derived:
  - `com_mil_serv`
  - `milpol_crime`
  - `milpol_law`
  - `milpol_peace`
  - `mil_police`
  - `mil_repress`
  - `mil_impun`
  - `mil_eco_dummy`
  - `milex_gdp`
  - `pers_to_pop`
  - `reserve_pop`
  - `hwi`
- military expenditure
- military personnel
- police personnel
- event-derived:
  - domestic military deployment
  - military policing role
  - prison / border / customs role
  - exception-rule militarization
  - military protest-response role

### 8C. Recommended modeling order

1. document all candidate annual indicators
2. map which are available for all `25` countries
3. assemble an annual design panel
4. test a simple static latent version first
5. only then test a drift / dynamic version

The main lesson from Kenwick for SENTINEL is:

- start with a transparent annual measurement design
- then add temporal dynamics only after the item layer is solid

The main lesson from M3 for SENTINEL is:

- militarization and civilian control cannot be built from event data alone
- a serious design needs a structural layer on military role, veto power,
  impunity, domestic policing role, economic autonomy, and force burden
- M3 is one of the strongest current candidates for that structural layer
