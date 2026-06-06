# SENTINEL Editorial System Redesign — Design Spec
**Date:** 2026-06-06  
**Status:** Draft for written review  
**Scope:** Public visual system, palette, surface rules, and cross-tab editorial coherence for `Overview`, `Countries`, `OC`, `US-LATAM`, `Events`, and `About`

---

### Overview

SENTINEL already has the bones of an editorial publication, but the visual language is drifting across tabs. The home page retains the strongest identity, while `Countries`, `OC`, `US-LATAM`, and `About` feel less intentionally related, and `Events` has recently become more fragmented through one-off styling decisions.

This redesign defines a shared editorial system for the public site. The goal is not to make every tab look the same. The goal is to make the whole product feel like one publication with distinct section behaviors.

The approved direction for this work is:

- **Palette:** `C2 — Editorial Oxide`
- **Sitewide model:** `B — Editorial System`
- **Reference surface:** homepage editorial feeling
- **Operational exception:** `Events` remains the most utilitarian tab

---

## Goals

1. Extend the editorial feeling of the homepage across the public site without flattening every tab into the same template.
2. Replace the current disliked color direction with an off-white, dark olive, and oxide-led palette that feels calmer, sharper, and more coherent.
3. Make `Countries`, `OC`, and `US-LATAM` feel like parts of the same publication family.
4. Keep `Events` operational and fast to scan while still bringing it into the shared system.
5. Remove decorative treatments that feel soft, inconsistent, or overly digital, especially broad gradients and over-treated cards.
6. Update `About` so it explains both the project and the publication logic behind SENTINEL.

---

## Non-Goals

- Redesigning the private analyst console in this spec
- Changing event taxonomy, risk methodology, or backend data contracts
- Replacing the homepage's editorial identity with a completely different aesthetic
- Turning `Events` into a magazine-style reading experience at the expense of operational usability
- Defining implementation sequencing at the ticket or file-edit level

---

## Core Direction

### Chosen visual stance

`Editorial Oxide`

SENTINEL should feel like a contemporary political-risk dossier: restrained, literate, and slightly severe rather than glossy, techy, or pastel. The tone should suggest paper, ink, institutional analysis, and marked-up briefing documents rather than dashboards built from generic SaaS defaults.

### Chosen system model

`Editorial System`

The site should use one shared visual grammar with section-specific behavior. This is preferred over either:

- a loose tab-by-tab redesign, which would keep the current drift alive
- a highly theatrical magazine treatment, which would undermine analytical trust and slow repeated use

### Master reference

The homepage remains the strongest expression of SENTINEL's editorial identity. Other tabs should borrow its sense of hierarchy, paper-like structure, framing, and pacing, then adapt that language to their own information needs.

---

## Palette System

The approved palette is `C2 — Editorial Oxide`.

### Primary roles

- **Paper:** off-white base for the full site background and most reading surfaces
- **Ink:** near-black softened through olive/charcoal undertones for headings and body text
- **Anchor olive:** dark olive green for structural emphasis, navigation anchors, buttons, and key framing elements
- **Editorial oxide:** warm rust-oxide accent for active states, ranked emphasis, directional change, and selected highlights
- **Muted field greens:** desaturated olive-gray support tones for secondary borders, dividers, inactive chips, filters, and map/chart support

### Color behavior

- Off-white should dominate the page so the site reads like a publication rather than a dashboard on colored slabs.
- Dark olive should feel architectural, not decorative.
- Oxide should be selective and meaningful. It should not wash entire cards or large surfaces.
- Neutrals should lean toward ink, stone, and dried-paper tones rather than pink-beige warmth.

### Explicit removals

- broad warm glow treatments
- diffuse gradient overlays on cards
- overuse of amber/orange as a default highlight
- tab-specific accent drift that makes sections feel unrelated

---

## Typography And Tone

### Hierarchy

- Serif display headlines remain the emotional anchor.
- Monospace labels continue to handle taxonomy, metadata, timestamps, and system cues.
- Sans-serif body copy stays readable and understated.

### Tone target

The site should read like an analytical publication:

- authoritative but not militarized
- editorial but not theatrical
- contemporary but not trendy

Typography should do more of the hierarchy work so color and decoration can do less.

---

## Surface And Component Rules

### Surface model

Panels should feel like dossier sheets and clipped briefing components, not floating app cards.

Shared rules:

- flatter surfaces
- visible borders
- restrained corner radii
- lighter shadow dependence
- stronger spacing rhythm

### Borders and framing

Borders should become a major organizing device. Section frames, card edges, dividers, and rails should do more work than gradients.

### Active and selected states

Selected items should rely on a clear combination of:

- oxide or olive accent
- border change
- typographic emphasis

They should not rely primarily on glow, blur, or animated lift.

### Data visualizations

Charts, sparklines, and comparative graphics should inherit the same palette family:

- olive and muted green for stable structural context
- oxide for direction, pressure, or emphasis
- darker ink/navy-charcoal supports where contrast is needed

Data graphics should stay analytical first. The site palette should guide them without reducing legibility or turning all series into one tonal family.

---

## Tab-by-Tab Application

## Overview

The homepage remains the master editorial stage. It should keep the strongest publication feeling, with clearer framing and fewer accidental style leaks into other tabs. Its role is to establish the grammar that the rest of the site speaks.

### Countries

`Countries` should become the clearest dossier expression on the site.

The country profile should feel like a national monitor brief:

- strong opening analytical brief
- disciplined hierarchy
- structural and predictive evidence that supports the brief instead of repeating it
- document-like panels rather than decorative dashboard blocks

The current country navigator should stay flatter and more archival in tone, without broad gradients or over-heavy motion.

### OC

`OC` should feel like a thematic field guide within the same publication family. It can be slightly denser and more network-oriented than `Countries`, but it should use the same paper, border, type, and accent logic.

### US-LATAM

`US-LATAM` should feel more archival and strategic: a policy desk or relationship dossier rather than a generic chart tab. It should sit comfortably beside `Countries` and `OC`, with stronger section framing and more deliberate comparative layouts.

### Events

`Events` should remain the most operational tab on the site.

That means:

- tighter spacing
- faster scanning
- less decorative treatment
- stronger list discipline

But it should still belong to the same publication. The palette, typography, borders, and selected-state logic should align with the rest of the site. The recent move toward a single-column expanding brief list is consistent with this direction and should remain the baseline interaction pattern.

### About

`About` should be rewritten or reorganized so it explains:

- what SENTINEL monitors
- how the analytical framework works
- why the publication is structured the way it is
- how editorial, structural, and event layers relate

It should feel like an editorial methods note, not a miscellaneous reference page.

---

## Content And Interaction Principles

1. Avoid repeated summaries that restate the same risk story in multiple adjacent boxes.
2. Let the monitor brief lead, then let structural and event evidence support it.
3. Use hover states as enhancement, not as the only way to access critical information.
4. Prefer expandable reading flows over split-pane clutter when the task is narrative interpretation.
5. Keep lists legible and disciplined; metadata should support the story, not crowd it out.

---

## Rollout Order

Implementation should follow four phases:

1. **Shared visual tokens and component rules**
   - establish palette tokens, surface rules, borders, active states, and section framing

2. **Core editorial tabs**
   - apply the system to `Countries`, `OC`, and `US-LATAM`

3. **Operational harmonization**
   - bring `Events` into the shared system without sacrificing speed or density

4. **Institutional framing**
   - update `About` so the publication identity and methodology are communicated clearly

The homepage should be treated as the reference grammar, not the first surface to reinvent.

---

## Risks

### Over-editorializing `Events`

If `Events` becomes too magazine-like, it will lose the fast reading and triage quality that makes it useful.

### Overusing oxide

If oxide becomes a blanket accent rather than a selective signal, the whole site will feel louder and less trustworthy.

### Surface inconsistency

If some tabs keep soft gradients, rounded floating cards, or different accent logic, the redesign will read as partial and unresolved.

### Style without hierarchy

If the redesign changes color and texture without improving structure, it will feel cosmetic rather than editorial.

---

## Validation Criteria

The redesign is successful if:

1. A user can move from `Overview` to `Countries`, `OC`, `US-LATAM`, `Events`, and `About` and feel they are still inside one publication.
2. The palette reads as off-white, dark olive, and oxide-led rather than beige, amber, or gradient-heavy.
3. `Countries` feels like a national dossier rather than a collection of dashboard boxes.
4. `Events` still reads as the most operational surface on the site.
5. Active, selected, and ranked states are legible without relying on glow-heavy treatments.
6. Desktop and mobile views preserve hierarchy, contrast, and coherence.

---

## Deliverable Boundary

This spec defines the approved design direction and system rules for the public site. It does not yet define the implementation task breakdown. The next step after written approval is to translate this spec into an explicit implementation plan.
