#!/usr/bin/env python3
"""
Build a refinement queue for the acute political-risk benchmark.

This stage is private/internal. It does not invent new features or labels.
Instead it identifies which benchmark rows deserve closer review before the
acute-risk benchmark is treated as stable enough for further modeling work.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
BENCHMARK = ROOT / "data" / "modeling" / "acute_political_risk_benchmark_tiers.json"
OUT = ROOT / "data" / "review" / "acute_political_risk_benchmark_refinement_queue.json"
LOCAL_DECISIONS = ROOT / "data" / "review" / "acute_political_risk_benchmark_refinement_decisions.local.json"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_local_decisions() -> list[dict]:
    if not LOCAL_DECISIONS.exists():
        return []
    payload = load_json(LOCAL_DECISIONS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return rows if isinstance(rows, list) else []


def f(row: dict, key: str) -> float:
    value = row.get(key)
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def build_reason(row: dict, tier: str) -> tuple[str, str]:
    score = int(row.get("acute_political_risk_signal_score_next_1m") or 0)
    specificity_gap = f(row, "transition_specificity_gap")
    protest_specificity = f(row, "protest_escalation_specificity_score")
    protest_bg = f(row, "protest_background_load_score")
    high_severity = int(row.get("high_severity_episode_count") or 0)
    fragmenting = int(row.get("fragmenting_episode_count") or 0)
    shock = int(row.get("event_shock_flag") or 0)

    if tier == "hard_negative":
        if protest_specificity > 0:
            return (
                "protest_near_miss",
                "hard-negative benchmark month with nonzero protest-escalation specificity that should be reviewed against the protest-positive reference pattern",
            )
        if high_severity > 0 and specificity_gap >= 0:
            return (
                "high_severity_near_miss",
                "hard-negative benchmark month with high severity and non-negative specificity gap that may be close to the acute-positive boundary",
            )
        if fragmenting > 0 and score >= 3:
            return (
                "fragmentation_boundary",
                "hard-negative benchmark month with fragmenting structure and watch-level score that should be confirmed as a true near miss",
            )
        return (
            "confirm_hard_negative",
            "hard-negative benchmark month that should be confirmed and preserved as a benchmark stress-test case",
        )

    if tier == "easy_negative":
        if score > 0 or protest_bg > 0 or shock > 0:
            return (
                "easy_negative_sanity_check",
                "easy-negative benchmark month carries nonzero stress residue and should be sanity-checked before the benchmark is treated as stable",
            )
        return (
            "stable_easy_negative",
            "easy-negative benchmark month looks stable and can remain in the benchmark with low review priority",
        )

    return (
        "gold_positive_checkpoint",
        "gold-positive benchmark month retained for reference",
    )


def priority(row: dict, tier: str) -> int:
    if tier == "hard_negative":
        return int(
            20
            + (f(row, "protest_escalation_specificity_score") > 0) * 8
            + (int(row.get("high_severity_episode_count") or 0) > 0) * 5
            + (int(row.get("fragmenting_episode_count") or 0) > 0) * 4
            + (f(row, "transition_specificity_gap") >= 0) * 3
            + int(row.get("acute_political_risk_signal_score_next_1m") or 0)
        )
    if tier == "easy_negative":
        return int(
            (int(row.get("acute_political_risk_signal_score_next_1m") or 0) > 0) * 8
            + (f(row, "protest_background_load_score") > 0) * 3
            + (int(row.get("event_shock_flag") or 0) > 0) * 3
        )
    return 0


def main() -> None:
    panel_payload = load_json(PANEL)
    panel_rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else panel_payload
    panel_lookup = {
        (str(row.get("country") or ""), str(row.get("panel_date") or "")): row
        for row in panel_rows
    }

    benchmark_payload = load_json(BENCHMARK)
    benchmark_rows = benchmark_payload.get("rows", []) if isinstance(benchmark_payload, dict) else benchmark_payload
    resolved_keys = {
        (
            str(row.get("country") or ""),
            str(row.get("panel_date") or ""),
            str(row.get("tier") or ""),
        )
        for row in load_local_decisions()
    }

    queue_rows: list[dict] = []
    for item in benchmark_rows:
        tier = str(item.get("tier") or "")
        if tier not in {"hard_negative", "easy_negative"}:
            continue
        key = (str(item.get("country") or ""), str(item.get("panel_date") or ""))
        if (key[0], key[1], tier) in resolved_keys:
            continue
        row = panel_lookup.get(key)
        if not row:
            continue
        category, note = build_reason(row, tier)
        if category == "stable_easy_negative":
            continue
        queue_rows.append({
            "country": key[0],
            "panel_date": key[1],
            "tier": tier,
            "refinement_category": category,
            "review_priority": priority(row, tier),
            "acute_political_risk_signal_score_next_1m": row.get("acute_political_risk_signal_score_next_1m"),
            "acute_political_risk_signal_label_next_1m": row.get("acute_political_risk_signal_label_next_1m"),
            "high_severity_episode_count": row.get("high_severity_episode_count"),
            "fragmenting_episode_count": row.get("fragmenting_episode_count"),
            "event_shock_flag": row.get("event_shock_flag"),
            "event_type_conflict_count": row.get("event_type_conflict_count"),
            "event_type_protest_count": row.get("event_type_protest_count"),
            "protest_acute_signal_score": row.get("protest_acute_signal_score"),
            "protest_background_load_score": row.get("protest_background_load_score"),
            "protest_escalation_specificity_score": row.get("protest_escalation_specificity_score"),
            "transition_contestation_load_score": row.get("transition_contestation_load_score"),
            "transition_specificity_gap": row.get("transition_specificity_gap"),
            "note": note,
        })

    queue_rows.sort(
        key=lambda row: (
            -int(row["review_priority"]),
            row["tier"],
            row["country"],
            row["panel_date"],
        )
    )

    summary = {
        "rows": len(queue_rows),
        "hard_negative_rows": sum(1 for row in queue_rows if row["tier"] == "hard_negative"),
        "easy_negative_rows": sum(1 for row in queue_rows if row["tier"] == "easy_negative"),
        "protest_near_miss_rows": sum(1 for row in queue_rows if row["refinement_category"] == "protest_near_miss"),
        "high_severity_near_miss_rows": sum(1 for row in queue_rows if row["refinement_category"] == "high_severity_near_miss"),
        "fragmentation_boundary_rows": sum(1 for row in queue_rows if row["refinement_category"] == "fragmentation_boundary"),
        "easy_negative_sanity_check_rows": sum(1 for row in queue_rows if row["refinement_category"] == "easy_negative_sanity_check"),
        "countries": sorted({row["country"] for row in queue_rows}),
    }

    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_acute_political_risk_benchmark_refinement_queue",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "benchmark_file": str(BENCHMARK.relative_to(ROOT)),
        "local_decision_file": str(LOCAL_DECISIONS.relative_to(ROOT)) if LOCAL_DECISIONS.exists() else None,
        "summary": summary,
        "current_goal": [
            "Refine the acute-risk benchmark before inventing more features or models.",
            "Review hard negatives first, especially protest-linked and high-severity near misses.",
            "Treat easy negatives mainly as sanity-check rows, not the main analytical bottleneck.",
        ],
        "rows": queue_rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote acute-risk benchmark refinement queue to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
