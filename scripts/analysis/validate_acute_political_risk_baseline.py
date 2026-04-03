#!/usr/bin/env python3
"""
Validate the current acute political-risk signal layer against the reviewed
acute-risk fit-ready sample.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FIT_DATASET = ROOT / "data" / "modeling" / "acute_political_risk_fit_dataset.json"
OUT = ROOT / "data" / "review" / "acute_political_risk_baseline_validation.json"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


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
    payload = load_json(FIT_DATASET)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    y_true = [int(row["y_true"]) for row in rows]

    threshold_results = []
    for threshold in range(2, 7):
        y_pred = [int(int(row.get("signal_score_1m") or 0) >= threshold) for row in rows]
        for idx, pred in enumerate(y_pred):
            rows[idx][f"threshold_{threshold}_pred"] = pred
        threshold_results.append({
            "threshold": threshold,
            **metrics(y_true, y_pred),
            "tier_results": tier_metrics(rows, f"threshold_{threshold}_pred"),
        })

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_acute_political_risk_baseline_validation",
        "fit_dataset_file": str(FIT_DATASET.relative_to(ROOT)),
        "validation_sample": payload.get("summary", {}),
        "signal_score_threshold_results": threshold_results,
        "recommended_threshold": max(threshold_results, key=lambda item: (item["f1_pct"], item["precision_pct"])),
        "rows": rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote acute-risk baseline validation report to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
