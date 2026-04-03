#!/usr/bin/env python3
"""
Validate the current irregular-transition signal layer against a reviewed
fit-ready sample.

The sample is built from:
- positives: gold irregular-transition labels
- negatives: reviewed-watch adjudicated rows plus any explicit weak review rows

This is a private/internal baseline validation stage before model fitting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
ADJUDICATED = ROOT / "data" / "modeling" / "adjudicated_irregular_transition_labels.json"
GOLD = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
REVIEW = ROOT / "data" / "review" / "irregular_transition_target_review.json"
LOCAL_NEGATIVE_DECISIONS = ROOT / "data" / "review" / "reviewed_negative_decisions.local.json"
BENCHMARK_TIERS = ROOT / "data" / "modeling" / "irregular_transition_benchmark_tiers.json"
OUT = ROOT / "data" / "review" / "irregular_transition_baseline_validation.json"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 3)


def metrics(y_true: list[int], y_pred: list[int]) -> dict:
    tp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 1)
    tn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 0)
    fp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 1)
    fn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision_pct": round(precision * 100.0, 3),
        "recall_pct": round(recall * 100.0, 3),
        "specificity_pct": round(specificity * 100.0, 3),
        "f1_pct": round(f1 * 100.0, 3),
    }


def tier_metrics(rows: list[dict], pred_key: str) -> dict:
    out: dict[str, dict] = {}
    tiers = sorted({str(row.get("benchmark_tier") or "unclassified") for row in rows})
    for tier in tiers:
        subset = [row for row in rows if str(row.get("benchmark_tier") or "unclassified") == tier]
        y_true = [int(row["y_true"]) for row in subset]
        y_pred = [int(row[pred_key]) for row in subset]
        out[tier] = {"rows": len(subset), **metrics(y_true, y_pred)}
    return out


def main() -> None:
    panel_payload = load_json(PANEL)
    panel_rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else []
    panel_lookup = {
        (str(row.get("country") or ""), str(row.get("panel_date") or "")): row
        for row in panel_rows
    }

    gold_payload = load_json(GOLD)
    gold_rows = gold_payload.get("rows", []) if isinstance(gold_payload, dict) else []
    gold_keys = {
        (str(row.get("country") or ""), str(row.get("panel_date") or ""))
        for row in gold_rows
    }
    benchmark_tier_lookup: dict[tuple[str, str], str] = {}
    if BENCHMARK_TIERS.exists():
        benchmark_payload = load_json(BENCHMARK_TIERS)
        benchmark_rows = benchmark_payload.get("rows", []) if isinstance(benchmark_payload, dict) else benchmark_payload
        benchmark_tier_lookup = {
            (str(row.get("country") or ""), str(row.get("panel_date") or "")): str(row.get("tier") or "")
            for row in benchmark_rows
        }

    adjudicated_payload = load_json(ADJUDICATED)
    adjudicated_rows = adjudicated_payload.get("rows", []) if isinstance(adjudicated_payload, dict) else []
    reviewed_watch_keys = {
        (str(row.get("country") or ""), str(row.get("panel_date") or ""))
        for row in adjudicated_rows
        if str(row.get("rating") or "").strip().lower() == "reviewed_watch"
    }

    review_payload = load_json(REVIEW)
    review_countries = review_payload.get("countries", []) if isinstance(review_payload, dict) else []
    weak_keys = set()
    for country_row in review_countries:
        country = str(country_row.get("country") or "")
        for case in country_row.get("cases", []):
            if str(case.get("rating") or "").strip().lower() == "weak":
                weak_keys.add((country, str(case.get("trigger_month") or "")))

    local_negative_keys = set()
    if LOCAL_NEGATIVE_DECISIONS.exists():
        local_payload = load_json(LOCAL_NEGATIVE_DECISIONS)
        local_rows = local_payload.get("rows", []) if isinstance(local_payload, dict) else []
        for row in local_rows:
            if int(row.get("label") or 0) != 0:
                continue
            if str(row.get("target_name") or "irregular_transition_next_1m") != "irregular_transition_next_1m":
                continue
            local_negative_keys.add((str(row.get("country") or ""), str(row.get("panel_date") or "")))

    labeled_rows = []
    labeled_keys = set()

    for key in sorted(gold_keys):
        row = panel_lookup.get(key)
        if not row:
            continue
        labeled_keys.add(key)
        labeled_rows.append({
            "country": key[0],
            "panel_date": key[1],
            "y_true": 1,
            "label_group": "gold_positive",
            "benchmark_tier": benchmark_tier_lookup.get(key, "gold_positive"),
            "signal_score_1m": int(row.get("irregular_transition_fit_score_next_1m") or 0),
            "signal_label_1m": str(row.get("irregular_transition_fit_label_next_1m") or ""),
            "operational_label_1m": int(row.get("irregular_transition_next_1m") or 0),
            "label_source": str(row.get("irregular_transition_label_source") or ""),
        })

    negative_keys = sorted((reviewed_watch_keys | weak_keys | local_negative_keys) - gold_keys)
    for key in negative_keys:
        row = panel_lookup.get(key)
        if not row:
            continue
        if key in labeled_keys:
            continue
        if key in local_negative_keys:
            label_group = "local_reviewed_negative"
        elif key in reviewed_watch_keys:
            label_group = "reviewed_watch_negative"
        else:
            label_group = "weak_review_negative"
        labeled_rows.append({
            "country": key[0],
            "panel_date": key[1],
            "y_true": 0,
            "label_group": label_group,
            "benchmark_tier": benchmark_tier_lookup.get(key, "unclassified_negative"),
            "signal_score_1m": int(row.get("irregular_transition_fit_score_next_1m") or 0),
            "signal_label_1m": str(row.get("irregular_transition_fit_label_next_1m") or ""),
            "operational_label_1m": int(row.get("irregular_transition_next_1m") or 0),
            "label_source": str(row.get("irregular_transition_label_source") or ""),
        })

    labeled_rows.sort(key=lambda item: (item["country"], item["panel_date"], item["y_true"]))
    y_true = [row["y_true"] for row in labeled_rows]

    threshold_results = []
    for threshold in range(2, 7):
        y_pred = [int(row["signal_score_1m"] >= threshold) for row in labeled_rows]
        for idx, pred in enumerate(y_pred):
            labeled_rows[idx][f"threshold_{threshold}_pred"] = pred
        result = {
            "threshold": threshold,
            **metrics(y_true, y_pred),
            "tier_results": tier_metrics(labeled_rows, f"threshold_{threshold}_pred"),
        }
        threshold_results.append(result)

    operational_pred = [row["operational_label_1m"] for row in labeled_rows]
    operational_result = metrics(y_true, operational_pred)
    for idx, pred in enumerate(operational_pred):
        labeled_rows[idx]["operational_pred"] = pred

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_baseline_validation",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "gold_file": str(GOLD.relative_to(ROOT)),
        "adjudicated_file": str(ADJUDICATED.relative_to(ROOT)),
        "review_file": str(REVIEW.relative_to(ROOT)),
        "local_negative_file": str(LOCAL_NEGATIVE_DECISIONS.relative_to(ROOT)) if LOCAL_NEGATIVE_DECISIONS.exists() else None,
        "validation_sample": {
            "rows": len(labeled_rows),
            "gold_positive_rows": sum(1 for row in labeled_rows if row["label_group"] == "gold_positive"),
            "reviewed_watch_negative_rows": sum(1 for row in labeled_rows if row["label_group"] == "reviewed_watch_negative"),
            "weak_review_negative_rows": sum(1 for row in labeled_rows if row["label_group"] == "weak_review_negative"),
            "local_reviewed_negative_rows": sum(1 for row in labeled_rows if row["label_group"] == "local_reviewed_negative"),
        },
        "operational_label_result": operational_result,
        "operational_label_tier_results": tier_metrics(labeled_rows, "operational_pred"),
        "signal_score_threshold_results": threshold_results,
        "recommended_threshold": max(threshold_results, key=lambda item: (item["f1_pct"], item["precision_pct"])),
        "rows": labeled_rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote baseline validation report to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
