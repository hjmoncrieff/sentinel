# SENTINEL Analyst Console Redesign — Design Spec
**Date:** 2026-06-05  
**Status:** Draft for written review  
**Scope:** `apps/analyst-console/` — UI architecture, interaction model, component system, and validation workflow for a redesign of the private analyst console

---

## Overview

Redesign the SENTINEL analyst console as a focused operations application rather than a large single-page interface. The console should feel closer to VS Code or Supabase than to the public dashboard: a dark operations desk with a narrow global rail, a quiet mixed top bar, and a stable three-column review workspace.

The redesign should optimize for **progressive review**:
- quick decisions are visible immediately
- deeper evidence and audit context are one expansion away
- actions remain beside context instead of replacing it

This redesign applies only to the private analyst console. The public dashboard remains static, lighter in tone, and architecturally separate.

---

## Goals

1. Make the analyst console feel like a serious review desk, not an oversized HTML page.
2. Improve navigation, scanability, and workflow clarity for repeated analyst use.
3. Replace ad hoc page structure with a reusable component system.
4. Support both fast event triage and deeper analytical review without layout thrash.
5. Establish a frontend workflow that supports responsive QA, accessibility checks, and visual regression testing.

---

## Non-Goals

- Redesigning the public dashboard UI
- Changing publication policy logic or backend review semantics
- Reworking Supabase data model or auth flows
- Rebuilding the analyst console into a different product surface outside `apps/analyst-console/`
- Introducing paid design or browser tools

---

## Product Direction

### Chosen operating mode
`Balanced console`

The analyst console should prioritize operational clarity over maximal information density or presentation polish. It should feel efficient and professional without becoming visually harsh or unreadable.

### Chosen navigation model
`Hybrid navigation`

The interface should combine:
- a narrow global left rail for major work modes
- workspace-specific organization within the main canvas

This keeps the shell compact and workstation-like while avoiding the ambiguity of a pure icon-only experience everywhere.

### Chosen workspace model
`Multi-panel review desk`

The console should not behave like a sequence of pages. The shell remains fixed while the center and right work surfaces reconfigure by mode and selection.

### Chosen top-bar model
`Mixed operations bar`

The top bar should combine:
- navigation context
- global search / command access
- sync / environment / session state

It should remain visually restrained and avoid becoming a second dense toolbar.

### Chosen visual tone
`Dark operations desk`

The analyst console should use a dark technical surface treatment distinct from the lighter, more editorial public dashboard.

### Chosen workflow behavior
`Progressive review`

The first layer of the interface should support fast decisions, but every key surface must expand into deeper evidence, actor, QA, and audit context without forcing a full context switch.

---

## Information Architecture

The redesigned console is organized around three levels:

1. **Global shell**
   - global left rail
   - mixed top bar
   - stable workspace frame

2. **Workspace layer**
   - queue / review tape
   - event brief and analytical context
   - actions and audit controls

3. **Deep review layer**
   - drawers, tabs, and inline expansions for evidence, actors, QA, duplicates, registry changes, and history

The key design rule is that analysts should rarely lose their current event context while moving deeper into review.

---

## Shell Layout

### Overall frame

The base shell consists of:
- **Far-left global rail**: narrow, icon-led, persistent
- **Top bar**: mixed operations bar spanning the workspace
- **Three-column review desk**:
  - left: queue / tape
  - center: event brief and context
  - right: actions, release, and audit

### Left global rail

The rail should be narrow and visually similar to workstation tools like VS Code. It is not a full labeled sidebar by default.

Primary rail sections:
- Inbox / Review
- Release
- Audit
- Registry
- Country / Entity views

Utility rail items:
- settings
- environment / backend mode
- session / account

Behavior:
- active state uses strong selection contrast
- icon count stays small and stable
- labels appear through tooltip, context headers, or expanded subviews, not full persistent text in the rail

### Top bar

The top bar is quiet and dense enough to be useful without feeling busy.

It should contain:
- current workspace / mode label
- global search or command affordance
- sync / freshness status
- publish or review-state summary
- session / environment controls

It should not become a second navigation band. Section switching belongs primarily to the left rail.

---

## Workspace Layout

### Base model
The default review desk uses a **balanced triad**:

- **Left column**: queue and filters
- **Center column**: event brief and analytical context
- **Right column**: actions, release controls, and audit access

This layout should remain stable across the major review workflows so analysts do not feel the application reshaping itself on every click.

### Left column: queue

Purpose:
- scan incoming items
- sort by priority
- shift between inbox/review queues
- preserve movement speed

Contains:
- queue mode chips or segmented controls
- filter and search controls scoped to the queue
- compact queue cards
- empty and low-information states

Queue cards should emphasize:
- headline
- country / scope
- review priority
- status badges
- concise trigger context

### Center column: event brief

Purpose:
- hold the selected event as the stable center of gravity
- support both skim and deeper reading

Contains:
- event header
- summary / reporting synthesis
- AI analysis and classification
- country context
- source / evidence views
- actor and network views

The center column is the anchor surface. The user should not lose this context while performing actions.

### Right column: actions and audit

Purpose:
- support quick operational decisions
- make deeper review operations available without crowding the main brief

Contains:
- primary review actions
- release state controls
- QA actions
- duplicate handling
- audit trail access

The right column should support both fast action and expandable depth. It should avoid the current “form wall” feeling.

---

## Workflow Model

### Canonical review states

The redesign should normalize visible workflow states across the interface:

- `Inbox`
- `In review`
- `Needs follow-up`
- `Ready for release`
- `Published`
- `Withheld`
- `Escalated`

These states should be represented consistently in:
- queue cards
- badges
- action panels
- audit views
- filters

### Progressive review behavior

Default event selection should show:
- summary
- key status badges
- fast decision controls

Expanded views should reveal:
- full evidence set
- actor extraction and registry context
- QA flags and duplicate candidates
- edit history and audit trail

The default mode is action-capable but not shallow. Deep review is additive, not disruptive.

---

## Component System

The redesign should be built from a small, explicit component inventory.

### Shell components
- `AppShell`
- `GlobalRail`
- `TopOperationsBar`
- `WorkspaceFrame`
- `PanelHeader`

### Navigation and status components
- `RailItem`
- `CommandButton`
- `ModeChip`
- `StateBadge`
- `StatusPill`
- `ContextBreadcrumb`

### Review components
- `QueueCard`
- `QueueFilterBar`
- `BriefPanel`
- `EvidencePanel`
- `ActorPanel`
- `CountryContextPanel`

### Action and audit components
- `ActionPanel`
- `ReleasePanel`
- `AuditPanel`
- `QaResolutionCard`
- `DuplicateResolutionCard`
- `RegistryEditCard`

### Interaction components
- `Tabs`
- `SegmentedControl`
- `InlineDrawer`
- `DetailDrawer`
- `EmptyState`
- `NoticeBanner`

### Component rules

1. Shared state surfaces must use a common badge and pill language.
2. Panels should use common header, spacing, and action-row patterns.
3. Deep-review experiences should prefer drawers and inline expansions over full replacements of the workspace.
4. Controls should be compact, predictable, and biased toward repeated analyst use.

---

## Visual System

### Tone

The console should feel:
- dark
- low-glare
- operational
- technical but not neon

### Styling rules

- restrained contrast with strong focus states
- minimal decorative treatment
- stable panel geometry
- dense but readable spacing
- strong hover / selected / active differentiation
- no card-within-card stacking for page sections

### Relationship to public dashboard

The analyst console should intentionally diverge from the public dashboard:
- console = darker, tighter, operational
- public dashboard = lighter, editorial, public-facing

This distinction is productively honest. The analyst console is a work surface, not a publication surface.

---

## Frontend Architecture

The redesign should not remain as a single giant undifferentiated page structure.

Target structure:
- shell module
- queue module
- brief module
- actions module
- audit module
- shared primitives / tokens

The exact file split can follow the current project constraints, but responsibilities must separate cleanly enough that each surface can be reasoned about independently.

The first extraction should be **design tokens**, followed by **UI primitives**, then **composed panels**, then **full workspace behavior**.

---

## Migration Strategy

This should be an incremental refactor, not a big-bang rewrite.

### Recommended order

1. **Token extraction**
   - colors
   - spacing
   - typography
   - borders
   - status colors

2. **Primitive extraction**
   - buttons
   - tabs
   - pills
   - badges
   - panel frames
   - drawer patterns

3. **Shell rebuild**
   - left rail
   - top bar
   - workspace frame

4. **Queue rebuild**
   - queue cards
   - queue controls
   - empty states

5. **Center brief rebuild**
   - event summary
   - AI analysis
   - evidence and actor expansions

6. **Right-side rebuild**
   - actions
   - release
   - audit
   - QA / duplicate / registry surfaces

7. **Cleanup**
   - remove dead styles
   - remove obsolete branches
   - consolidate duplicated logic and presentation rules

### Stability requirement

The public dashboard remains untouched during this refactor. The analyst console is the only redesign surface in scope.

---

## Free / Open-Source Tooling

The redesign workflow should use only free or open-source tools.

### Install / adopt

- **Storybook**
  - component workshop
  - state inspection
  - isolated UI development

- **Storybook accessibility addon**
  - baseline accessibility review on core components

- **Storybook visual tests / component tests**
  - state-level UI validation

- **Responsively App**
  - side-by-side responsive checks during active development

- **Playwright**
  - workflow smoke tests
  - visual screenshot checks for key console states

- **Tailwind + open-code component approach**
  - if adopted, use Tailwind with open-code components rather than opaque UI packages

- **Radix UI primitives**
  - default accessible behavioral primitive layer for interactive controls

### Recommended default stack

If the redesign becomes a componentized app, the recommended free stack is:
- Tailwind CSS
- shadcn/ui-style open-code components
- Radix UI primitives
- Storybook
- Playwright
- Responsively App

---

## Validation Strategy

Validation should happen at four levels.

### 1. Component validation
- component states rendered in Storybook
- badges, controls, tabs, drawers, cards, empty states, and panels checked independently

### 2. Accessibility validation
- keyboard navigation
- focus visibility
- screen-reader-relevant labeling
- automated a11y checks on core components and workflows

### 3. Layout validation
- desktop
- smaller laptop
- reduced-width desktop / tablet-like breakpoints

The redesign must preserve readable density and avoid overlap or collapsing controls.

### 4. Workflow validation

Playwright smoke coverage should include at minimum:
- app loads
- queue renders
- event selection updates center and right panels
- major tabs or drawers open
- primary actions remain reachable

Visual checks should cover:
- inbox state
- selected event state
- release state
- audit state
- empty / low-data state

---

## Risks And Constraints

1. The current analyst console is large and style-heavy, so extraction order matters.
2. A redesign that changes shell and workflow simultaneously can sprawl unless tokens and primitives are stabilized early.
3. A dark operations desk can become visually muddy if status colors and focus states are not disciplined.
4. Over-expanding the left rail or top bar would weaken the chosen workstation direction.

These risks are controlled by:
- keeping the shell compact
- stabilizing the balanced triad early
- using progressive review instead of page replacement
- validating repeatedly in browser and component states

---

## Acceptance Criteria

The redesign is successful when:

1. The analyst console clearly reads as a dark operational app distinct from the public dashboard.
2. The left rail, top bar, and three-column desk feel coherent and stable.
3. Analysts can make quick review decisions without losing access to deeper context.
4. Event context remains visible while action and audit work happens.
5. Core interface surfaces are componentized enough to support Storybook and repeatable UI QA.
6. Responsive and accessibility checks pass for the major review workflows.

---

## Immediate Next Step

After written approval of this spec, create an implementation plan that:
- defines file/module boundaries
- uses Tailwind CSS + open-code components + Radix UI primitives as the baseline UI stack
- sequences shell extraction, queue rebuild, and panel rebuild
- defines the first Playwright and Storybook checkpoints
