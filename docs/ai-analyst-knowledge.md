# AI Analyst Knowledge

This note translates the external deep-research markdowns into project-native
guidance for the SENTINEL AI analyst layer.

## Purpose

These knowledge assets are meant to inform:

- event classification logic
- actor coding logic
- council analysis
- QA reasoning
- public-facing interpretation and analyst review

They do not replace human validation, and they should not override structured
codebook rules.

## Core CMR Concepts

The project should interpret civil-military relations through four distinct
domains:

- external defense
- public security
- governance tasks
- political influence

The key analytical distinction is between:

- what the military is doing
- how the military relates to civilian authority while doing it

That means role coding and relationship coding should remain separate.

## Relationship Types

The most useful relationship types for the analyst layer are:

- subordinate
- bargaining
- tutelary veto
- partisan pillar
- fractured
- praetorian
- corruption capture

These should guide explanation and interpretation, especially in higher-order
analysis, even when they are not stored as final event labels.

## CMR–Organized Crime Concepts

The combined CMR/organized-crime research is most useful for:

- structured actor typing
- hybrid actor logic
- collusion and corruption reasoning
- prison control and criminal governance concepts
- military domestic deployment against criminal actors

This is especially valuable when distinguishing:

- confrontation
- deployment
- governance role
- negotiation or truce
- collusion
- corruption case
- refusal or defection

## Evidence Discipline

The analyst layer should keep three evidence tiers in mind:

- `documented`
- `credible`
- `alleged`

This matters most for:

- collusion
- corruption capture
- leader-removal claims
- covert bargaining
- hybrid state-linked armed actors

Weak evidence should widen uncertainty, not produce overconfident AI outputs.

## Rules For AI Analysts

- AI-generated analysis must always be labeled as such.
- AI analysts interpret events; they do not validate them.
- Public-security roles should not be collapsed into governance roles.
- High salience does not automatically mean low credibility.
- Low-confidence events should be treated cautiously and may require human corroboration before publication.
- Collusion and corruption labels should use the strongest available evidence standard.

## Role-Specific Use

### CMR analyst

Best informed by the CMR-only report’s role ladder, relationship types, and
inclusion/exclusion rules.

### Political risk analyst

Best informed by the CMR-only report’s attention to leader selection,
institutional stress, repression, and executive-military interaction.

### Regional security analyst

Best informed by the CMR/organized-crime report’s actor typology, hybrid actor
logic, cross-border threat dynamics, and deployment/cooperation patterns.

### Synthesis analyst

Should integrate the three lenses while preserving uncertainty and clearly
labeling the result as AI-generated analysis.

## Repo Assets

The structured versions of this knowledge live in:

- `config/agents/analyst_knowledge.json`
- `config/agents/council_guidance.json`
- `config/agents/council_roles.json`

These should be treated as the system-facing distillation of the research
markdowns, rather than using the raw markdowns directly inside operational code.
