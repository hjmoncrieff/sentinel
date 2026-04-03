# NSVA Knowledge Notes

## Purpose

This note translates the internal PDF `Mapping Non-State Violent Actors in Latin America for Geolocated Event Data` into repo-ready design guidance for SENTINEL.

It is not a full literature review. It captures the parts that are immediately useful for actor coding, event coding, and future country-year measures.

## Why This Matters For SENTINEL

The PDF is a strong fit for one specific part of SENTINEL:

- named non-state violent actor identification
- aliases, splinters, and factions
- actor roles in events
- territorial and governance-oriented coding
- explicit uncertainty handling

It is not a full framework for SENTINEL on its own because SENTINEL also tracks state actors, civil-military relations, security cooperation, reform, purges, and coup risk.

Use it as a module inside the broader SENTINEL knowledge system.

## Core Design Takeaways

The PDF argues that event-data work should distinguish:

- actor identity: names, aliases, splinters, factions
- actor role in the event: perpetrator, target, co-governor, colluder, enforcement proxy
- territorial and governance behavior: taxation/extortion, market control, prison governance, social regulation
- state interaction mode: confrontation, collusion, delegation, negotiated coexistence

For SENTINEL, these are highly actionable.

## Immediate Implications For The Repo

### 1. Build a named-actor registry

Use a registry file as the backbone for actor normalization.

Current repo seed:

- `config/actors/nsva_registry_seed.json`
- `config/actors/broad_actor_registry_seed.json`

The NSVA seed is now only one registry module. The broader seed carries state,
civil-society, economic, media, protest, and international actors so the full
actor registry is not skewed toward organized crime and armed groups.

This should grow into a fuller actor module inside the broader actor registry with:

- `actor_id`
- `canonical_name`
- `actor_category`
- `actor_group`
- `aliases`
- `country`
- `actor_type`
- `subtype`
- `registry_status`
- `source_confidence`
- `primary_activities`

### Hierarchy rule

SENTINEL should preserve actor hierarchy explicitly:

- `actor_category`: broad top-level class such as `state_actor` or `non_state_actor`
- `actor_group`: mid-level branch such as `military`, `executive`, `civil_society`, `economic_group`, `armed_non_state_actor`
- `actor_type`: specific actor class such as `organized_crime`, `armed_group`, `state_security_force`, `state_institution`
- `actor_subtype`: fine-grained subtype
- `actor_canonical_name`: specific named actor

Example:

- `actor_category = non_state_actor`
- `actor_group = armed_non_state_actor`
- `actor_type = organized_crime`
- `actor_subtype = transnational_network`
- `actor_canonical_name = Tren de Aragua`

This matters because the NSVA seed is only one branch of SENTINEL's actor world. It should not define the top-level actor ontology for the full project.

### 2. Keep uncertainty explicit

The PDF is very clear that uncertainty should be coded, not hidden.

For SENTINEL, that means:

- use `unspecified` rather than inventing names
- distinguish named detection from generic actor typing
- record whether an actor match is heuristic, model-inferred, or analyst-reviewed

### 3. Separate actor identity from actor role

An event should store both:

- who the actor is
- what role the actor played in the event

The role layer should eventually expand beyond `initiator` and `target` to include:

- `co_governor`
- `colluder`
- `enforcement_proxy`
- `victim`
- `security_partner`

### 4. Treat splinters carefully

The PDF recommends coding separate factions only when reporting clearly distinguishes them.

For SENTINEL:

- create separate `actor_id`s only when reporting clearly names distinct factions
- otherwise preserve alias linkage and uncertainty

### 5. Plan for governance coding later

The PDF goes beyond violent events and emphasizes:

- territorial presence
- prison governance
- criminal governance presence
- governance acts in text

SENTINEL is not yet ready to operationalize those measures fully, but the canonical data model should leave room for them.

## Suggested Actor-Type Extensions

The current actor taxonomy is workable, but this PDF suggests the need for more explicit NSVA subtypes such as:

- `cartel`
- `gang`
- `insurgent`
- `dissident_faction`
- `prison_gang`
- `alliance`
- `cartel_successor`
- `transnational_network`

These do not all need to become top-level actor types. They can be maintained as `subtype` values.

For state-side actors, SENTINEL should also use subtypes where possible, for example:

- `state_security_force`
- `state_institution`
- `external_state_actor`
- `civilian_group`
- `criminal_network`

## Suggested Coding Dimensions To Add Later

For actor-coded events, add fields like:

- `named_actor_confidence`
- `alias_matched`
- `alias_source`
- `faction_status`
- `state_interaction_mode`
- `governance_behavior_tags`

Recommended `state_interaction_mode` values:

- `confrontation`
- `collusion`
- `delegation`
- `negotiated_coexistence`
- `unclear`

Recommended `governance_behavior_tags` examples:

- `extortion`
- `market_control`
- `checkpoint_control`
- `prison_governance`
- `social_regulation`
- `territorial_control`

## Seed Registry Scope

The current seed registry is intentionally partial.

It currently prioritizes:

- major Mexico-based cartels named in the PDF excerpt
- major Colombia-based NSVAs named in the PDF excerpt
- a few high-value regional actors already useful for SENTINEL event coding

This is enough to improve internal knowledge immediately without pretending the registry is already complete.

## Recommended Next Step

The next good knowledge step is:

1. expand the broader state/non-state registry modules country by country
2. deepen named institutional coverage beyond the current reusable seed templates
3. add `state_interaction_mode` and `governance_behavior_tags` scaffolding to the actor-coded layer
4. expose those fields in the future analyst review workflow
