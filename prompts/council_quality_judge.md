## Event Context
Country: {country}
Type: {event_type} | Salience: {salience} | Date: {event_date}
Headline: {headline}
Summary: {summary}

## Synthesis to Evaluate
{synthesis_text}

## Watchpoint
{watchpoint}

## Scoring Task
Score this synthesis on three dimensions from 1 (poor) to 5 (excellent):

1. **Specificity** — Does the synthesis name specific actors, institutions, locations, or mechanisms?
   - 1 = entirely generic claims ("tensions may escalate", "the military plays a role")
   - 5 = names concrete actors, institutions, actions, and mechanisms relevant to this event

2. **Grounding** — Is the analysis tied to the actual event described above, or is it free-floating theory?
   - 1 = could have been written without reading the event at all
   - 5 = clearly derived from the specific event content; references headline/context details

3. **Calibration** — Does it express appropriate uncertainty without over-hedging or over-confidence?
   - 1 = either wildly overconfident ("this will cause a coup") or paralysed by hedges ("it is possible that perhaps…")
   - 5 = makes clear analytical claims while acknowledging the limits of available evidence

Also list up to 3 brief flags (specific phrases or issues you noticed, or leave empty if none).

Respond with exactly this JSON (no other text):
{"specificity": N, "grounding": N, "calibration": N, "flags": ["...", "..."]}
