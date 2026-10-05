# Codebook v3 And The Event Classifier

This note describes how SENTINEL turns news reports into coded events. The machine-readable
codebook is `config/taxonomy/codebook_v3.json` (version 3.0, approved 2026-09-29).
`scripts/codebook.py` loads it, builds the classifier's output schema from it, and validates
every coding against it. The prompts are in `prompts/` (`relevance_gate.md`,
`code_event_v3_system.md`, `code_event_v3.md`).

## What Gets Coded

Each report is first assigned a content type: `event` (something happened), `analysis`
(commentary or explainer), `profile` (background on a person or institution), or `relevance`
(outside the monitor's scope). Only in-scope reports are coded further.

In scope are civil–military relations and the security sector in Latin America and the
Caribbean. Ordinary domestic policing and crime reporting are out of scope unless the armed
forces, emergency powers, or organized crime's relationship with the state are involved.

## The 18 Event Types

| Domain | Code | Label | Legacy family |
| --- | --- | --- | --- |
| Civil–military control | `coup` | Coup or coup plot | `coup` |
| Civil–military control | `purge` | Command change or purge | `purge` |
| Civil–military control | `coup_proofing` | Coup-proofing | `coup_proofing` |
| Civil–military control | `military_role` | Military role expansion | `other` |
| Civil–military control | `friction` | Civil–military friction | `other` |
| Security governance and accountability | `reform` | Security sector reform | `reform` |
| Security governance and accountability | `accountability` | Accountability and justice | `other` |
| Security governance and accountability | `procurement` | Procurement and arms | `procurement` |
| Coercion and rights | `repression` | State repression | `other` |
| Coercion and rights | `protest` | Protest and mobilization | `protest` |
| Armed violence and organized crime | `conflict` | Armed conflict | `conflict` |
| Armed violence and organized crime | `oc` | Organized crime and the state | `oc` |
| Armed violence and organized crime | `peace` | Peace process | `peace` |
| External security relations | `cooperation` | Security cooperation and foreign operations | `coop` |
| External security relations | `aid` | Security assistance | `aid` |
| Political context with a security dimension | `emergency_rule` | Emergency rule | `other` |
| Political context with a security dimension | `electoral_security` | Elections and security | `other` |
| Political context with a security dimension | `other` | Other | `other` |

The legacy family is the v2 code (`config/taxonomy/event_types.json`) that the current
dashboard still reads. Every v3 event stores both: the v2-compatible fields at the top level
and the full v3 coding under `v3`. Military exercises and port visits are subtypes of
`cooperation` in v3 and map back to the legacy `exercise` family.

Key definitions follow published sources: `coup` follows the Colpus definition, and `purge`
follows the Military Purges in Dictatorships (MPD) definition.

## Other Coded Fields

- **Subtype**, from a fixed list per type.
- **Country** (one of the 28 monitored countries, or none), place and first-level
  administrative unit.
- **Event date** and its precision (day, month, or unknown). The report's publication date
  is stored separately.
- **Salience** (high, medium, low). High is reserved for events that change who controls
  the coercive apparatus or how; the target share is roughly 10–15% of events.
- **Certainty** of the coding.
- **DEED type and category.** For events about democratic erosion or resistance, a DEED event
  type and one of 35 curated DEED v7 categories. The axis is derived from the
  category.
- **Actors**: each with a group (one of 19) and a role (one of 9).
- **Relationship signal** between civilian authorities and the armed forces, when the report
  shows one.
- **Summary** in English, and short **evidence quotes** from the report that support the
  coding.

## How Classification Runs

1. **Keyword pre-filter** (`RELEVANCE_KEYWORDS`), tuned for recall.
2. **Headline gate.** Claude Haiku 4.5 screens 25 headlines per request and drops reports
   that are clearly out of scope. The prompt tells it that a missed relevant item costs more
   than a false pass.
3. **Opening text.** For reports that arrive as a bare headline, the pipeline fetches the
   publisher's opening paragraphs where the publisher allows it. Sources that block
   automated requests are coded from the headline alone. No paywall or login is bypassed.
4. **Coding.** Claude Sonnet 5.5 codes one report per request. The full codebook is the
   system prompt (cached between requests), and the reply must match a JSON schema generated
   from the codebook.
5. **Clustering.** Reports of the same incident in a country are merged into one event.

The nightly pipeline (`scripts/run_pipeline.py`, `--classifier v3` by default) and the
historical backfill (`scripts/classify_v3.py` plus `scripts/apply_v3_codes.py`) use the same
codebook, prompts and models.

## Model Choice

On 2026-09-30 three models coded the same stratified sample of 300 reports (220 the gate
kept, 80 it rejected). Share of reports on which all three agreed, by field:

| Field | All three agree |
| --- | --- |
| `relevant` | 77% |
| `content_type` | 84% |
| `type` | 64% |
| `subtype` | 58% |
| `country` | 75% |
| `event_month` | 71% |
| `salience` | 58% |
| `deed_type` | 58% |
| `deed_category` | 68% |
| `relationship_signal` | 99% |

Across the disputed fields, Haiku 4.5 was the lone dissenter 518 times, Sonnet 5.5 146 times,
and Opus 5.5 133 times. Sonnet 5.5 was chosen for coding: it agrees with the strongest model
far more often than Haiku does, at about $0.006 per report. The disagreements were not
adjudicated by a human, so these are agreement figures, not accuracy figures. A
human-adjudicated gold set remains a follow-up.

## Limits

- About half of gate-kept reports can be coded with opening text; the rest are coded from
  the headline, which lowers certainty and makes dates less precise.
- Events coded before October 2026 used the v2 prompt and Haiku. About 41% of those are
  rated high salience, so salience is not comparable across the two periods.
- Evidence tiers (weighting sources by reliability inside the coding) were considered and
  deferred.
