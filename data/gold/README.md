# data/gold/

This is the gold layer: human-reviewed records that clear the quality thresholds in
`config/gold_policy.json`. It is **private**. Only this README is tracked; everything
else here is gitignored and must never be published or synced to the public repo.

## Purpose

The gold layer is the step between analyst review and any learning. It gathers the
judgments humans have already made, so that they can:

1. become evaluation sets (for example, measuring classifier agreement against
   `corrections.jsonl`);
2. serve as retrieval examples for prompts and rules;
3. later, once volume and quality justify it, train task-specific models.

## Build

```bash
python3 scripts/review/apply_analyst_edits.py   # refresh post-review events first
python3 scripts/review/build_gold_layer.py
```

## Files

| File | Contents |
|---|---|
| `events.jsonl` | Accepted events tiered as `coordinator_approved` (3), `analyst_reviewed` (2), or `human_validated` (1) |
| `negatives.jsonl` | Events humans rejected, with the machine coding kept for contrast |
| `corrections.jsonl` | The latest human value per (event, field) where it differs from the machine value. Only edits from analyst role or above count |
| `duplicate_decisions.jsonl` | Final `merged` and `distinct` decisions. Drafts and undone decisions are excluded |
| `qa_decisions.jsonl` | Resolved QA flags |
| `labels.jsonl` | Adjudicated country-month target labels from `data/review/*decisions.local.json` |
| `summary.json` | Counts, tiers, exclusions, and SHA-256 fingerprints of every input |

## Thresholds

The thresholds are defined in `config/gold_policy.json` (`gold_v1`):

- Events qualify only by review status (`analyst_reviewed`, `coordinator_approved`) or by
  an explicit `human_validated` flag.
- Events whose edit history produced permission or field warnings are excluded.
- Events that were merged away are excluded.
- Corrections from RA-role edits are excluded, because RAs can only annotate.

Changing a threshold changes what counts as ground truth, so log every change in
`CHANGELOG.md`.
