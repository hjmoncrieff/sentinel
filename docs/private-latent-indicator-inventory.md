# Private Latent Indicator Inventory

## Purpose

This file is the standing annual indicator inventory for:

- `civilian_control_latent`
- `militarization_latent`

Each candidate input is tagged as:

- `live_now`
  already available in current SENTINEL data layers
- `derivable_now`
  can be assembled now from existing local files with a dedicated build step
- `missing_later`
  not yet assembled locally and should be treated as later-stage work

This is a private design artifact. It is for measurement assembly, not public
publication.

## Status Rule

- `live_now` variables can be used immediately in inventory tests
- `derivable_now` variables should be assembled before the first static latent
  fit
- `missing_later` variables should not block the first prototype unless they
  are conceptually indispensable

## Civilian Control

| Variable | Source layer | Status | Notes |
| --- | --- | --- | --- |
| `mil_constrain` | V-Dem cleaned layer | `live_now` | Best current direct annual proxy for military constraint on executive |
| `mil_exec` | V-Dem cleaned layer | `live_now` | Captures military executive profile / fusion |
| `coup_event` | V-Dem cleaned layer | `live_now` | Annual coup occurrence |
| `coup_attempts` | V-Dem cleaned layer | `live_now` | Annual coup-attempt count |
| `regime_type` | V-Dem cleaned layer | `live_now` | Regime background |
| `polyarchy` | V-Dem cleaned layer | `live_now` | Democratic openness baseline |
| `judicial_constraints` | V-Dem cleaned layer | `live_now` | Horizontal constraint layer |
| `legislative_constraints` | V-Dem cleaned layer | `live_now` | Horizontal constraint layer |
| `rule_of_law_vdem` | V-Dem cleaned layer | `live_now` | Legal-institutional control background |
| `cs_repress` | V-Dem cleaned layer | `live_now` | Coercive treatment of civil society |
| `election_repression` | V-Dem cleaned layer | `live_now` | Coercion around political competition |
| `political_violence` | V-Dem cleaned layer | `live_now` | Background coercive contestation |
| `mil_origin` | M3 -> country-year layer | `live_now` | Strong reserved-domain / military-origin signal |
| `mil_leader` | M3 -> country-year layer | `live_now` | Direct military-leadership signal |
| `mil_mod` | M3 -> country-year layer | `live_now` | Military role in defense-ministry control |
| `mil_veto` | M3 -> country-year layer | `live_now` | Reserved military veto domain |
| `mil_impun` | M3 -> country-year layer | `live_now` | Military impunity / weak civilian legal control |
| `mil_repress` | M3 -> country-year layer | `live_now` | Military role in repression |
| `mil_repress_count` | M3 -> country-year layer | `live_now` | Frequency/intensity companion to `mil_repress` |
| `milpol_crime` | M3 -> country-year layer | `live_now` | Military role in domestic crime policing |
| `milpol_law` | M3 -> country-year layer | `live_now` | Military role in law-enforcement functions |
| `milpol_peace` | M3 -> country-year layer | `live_now` | Military role in domestic order / peace-preservation |
| `mil_police` | M3 -> country-year layer | `live_now` | Military-police overlap / hybrid role |
| `coup_count_5y` | country-year derived panel | `live_now` | Already built in `scripts/build_country_year.py` |
| `coup_attempt_count_5y` | country-year derived panel | `live_now` | Already built in `scripts/build_country_year.py` |
| `sentinel_purge_family_count_y` | SENTINEL -> country-year layer | `live_now` | Annualized purge / reshuffle events |
| `sentinel_coup_family_count_y` | SENTINEL -> country-year layer | `live_now` | Annualized coup-family event counts |
| `military_veto_episode_count_y` | SENTINEL event layer | `missing_later` | Still needs a distinct veto-specific annual rollup |
| `sentinel_domestic_military_role_count_y` | SENTINEL -> country-year layer | `live_now` | Annual rollup from militarization-related subcategories |
| `civilian_defense_minister_status` | official political roster layer | `missing_later` | Not yet assembled systematically |
| `promotion_control_indicator` | institutional / official-source layer | `missing_later` | Valuable but not yet structured annually |
| `budget_autonomy_indicator` | budget / institutional layer | `missing_later` | Not yet assembled as annual comparable panel |

## Militarization

| Variable | Source layer | Status | Notes |
| --- | --- | --- | --- |
| `mil_exec` | V-Dem cleaned layer | `live_now` | Useful background but not sufficient alone |
| `mil_constrain` | V-Dem cleaned layer | `live_now` | Lower constraint can support militarization inference |
| `cs_repress` | V-Dem cleaned layer | `live_now` | Coercive state usage background |
| `political_violence` | V-Dem cleaned layer | `live_now` | Contestation environment |
| `election_repression` | V-Dem cleaned layer | `live_now` | Coercive politics background |
| `regime_type` | V-Dem cleaned layer | `live_now` | Regime context |
| `polyarchy` | V-Dem cleaned layer | `live_now` | Constraint background |
| `com_mil_serv` | M3 -> country-year layer | `live_now` | Conscription / compulsory military service |
| `com_mil_serv_gen` | M3 -> country-year layer | `live_now` | Gender structure of military service |
| `com_mil_serv_dur_max` | M3 -> country-year layer | `live_now` | Duration / burden indicator |
| `com_mil_serv_dur_min` | M3 -> country-year layer | `live_now` | Duration / burden indicator |
| `alt_civ_serv` | M3 -> country-year layer | `live_now` | Civilian-service alternative context |
| `milpol_crime` | M3 -> country-year layer | `live_now` | Military role in crime policing |
| `milpol_law` | M3 -> country-year layer | `live_now` | Military role in domestic law enforcement |
| `milpol_peace` | M3 -> country-year layer | `live_now` | Military role in domestic peace/order enforcement |
| `mil_police` | M3 -> country-year layer | `live_now` | Military-police overlap |
| `mil_repress` | M3 -> country-year layer | `live_now` | Military role in repression |
| `mil_repress_count` | M3 -> country-year layer | `live_now` | Intensity companion |
| `mil_impun` | M3 -> country-year layer | `live_now` | Impunity can reinforce militarized order |
| `mil_eco_dummy` | M3 -> country-year layer | `live_now` | Military economic role present |
| `mil_eco_own` | M3 -> country-year layer | `live_now` | Ownership role |
| `mil_eco_share` | M3 -> country-year layer | `live_now` | Share/intensity of military economic role |
| `mil_eco_dom` | M3 -> country-year layer | `live_now` | Domestic economic entrenchment |
| `milex_gdp` | M3 -> country-year layer | `live_now` | Military expenditure burden |
| `milex_healthexp` | M3 -> country-year layer | `live_now` | Spending tradeoff signal |
| `pers_to_pop` | M3 -> country-year layer | `live_now` | Military personnel burden |
| `pers_to_phy` | M3 -> country-year layer | `live_now` | Personnel intensity |
| `reserve_pop` | M3 -> country-year layer | `live_now` | Reserve burden |
| `hwi` | M3 -> country-year layer | `live_now` | Hybrid-warfare / military-capacity index |
| `sentinel_domestic_military_role_count_y` | SENTINEL -> country-year layer | `live_now` | Annual rollup from coded militarization subcategories |
| `sentinel_military_policing_role_count_y` | SENTINEL -> country-year layer | `live_now` | Annual rollup from internal-security role events |
| `prison_border_customs_role_count_y` | SENTINEL event layer | `missing_later` | Still needs a narrower dedicated annual rollup |
| `sentinel_exception_rule_militarization_count_y` | SENTINEL -> country-year layer | `live_now` | Annual rollup from exception/emergency subcategories |
| `militarized_protest_response_count_y` | SENTINEL event layer | `missing_later` | Still needs a protest-specific annual rollup instead of the broader domestic-role count |
| `security_fragmentation_pressure_y` | SENTINEL model layer | `derivable_now` | Use cautiously; related but distinct construct |
| `military_expenditure_series` | World Bank / SIPRI style layer | `missing_later` | Current local World Bank layer should be checked for exact series fit |
| `military_personnel_series` | official structural layer | `missing_later` | Not yet confirmed as a clean annual comparative panel |
| `police_personnel_series` | UNODC / OAS / national police layer | `missing_later` | Important but not yet assembled |
| `police_militarization_design_indicator` | institutional layer | `missing_later` | Needs dedicated coding project |

## Immediate Build Priorities

1. Build a first private annual panel using only:
   - `live_now`
   - selective `derivable_now`
2. Add narrower later-stage annual rollups for:
   - veto-specific episodes
   - prison / border / customs roles
   - protest-specific militarized response
3. Leave `missing_later` variables out of the v0 static latent fit.

## Working Rule

For the first prototype:

- `live_now` and `derivable_now` are enough
- `missing_later` should improve later versions, not block the first one
- the first model should be annual and static
- drift/dynamic versions come only after the v0 annual panel behaves well
