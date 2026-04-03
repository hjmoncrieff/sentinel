# Console UI To-Do

## Immediate

- Do a live browser pass on the analyst console after the latest three-column refactor.
- Check desktop behavior for:
  - left tape density
  - middle-column readability
  - right-column action spacing
  - independent column scrolling
- Check mobile and smaller laptop breakpoints for the console.

## Console

- Tighten the top navigator further:
  - reduce visual weight of username/role pills
  - consider a lighter `Command` toggle treatment
- Refine the command tray:
  - simplify quick views further
  - decide whether grouping should remain exposed
- Continue aligning the left tape with the public dashboard event feed:
  - reduce residual internal-review noise
  - refine selected-state emphasis
  - improve empty and low-information states
- Improve the middle column tabs:
  - `Briefing`
  - `AI Analysis`
  - `Actors`
  - make low-data tabs more compact
- Improve the right column tabs:
  - `Action`
  - `Release`
  - `Audit`
  - reduce form heaviness and explanatory text
- Revisit quick-action hierarchy after live use:
  - primary actions
  - caution actions
  - destructive actions
  - disabled states

## Data / Workflow

- Improve actor extraction so the console and dashboard do not show weak actor states too often.
- Audit geolocation quality for events where country and point placement diverge.
- Review multi-country event handling across:
  - tape
  - dashboard event feed
  - map highlighting
  - profile linking
- Consider a clearer publication-state vocabulary across the console:
  - `Published`
  - `Withheld`
  - `Removed`
  - `Draft`

## Documentation

- Keep [event-taxonomy-reference.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/event-taxonomy-reference.md) updated whenever taxonomy changes.
- Add a short analyst-console workflow note for:
  - tape review
  - action/release flow
  - actor review flow
  - audit usage

