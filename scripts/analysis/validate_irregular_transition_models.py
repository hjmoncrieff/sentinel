#!/usr/bin/env python3
"""
Run a first private model-validation comparison for irregular-transition risk.

This stage compares:
- the current score-threshold baseline
- a leave-one-out logistic regression baseline

against the reviewed fit-ready sample built from:
- positives: gold irregular-transition labels
- negatives: reviewed-watch adjudications and explicit weak review rows
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
ADJUDICATED = ROOT / "data" / "modeling" / "adjudicated_irregular_transition_labels.json"
GOLD = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
REVIEW = ROOT / "data" / "review" / "irregular_transition_target_review.json"
LOCAL_NEGATIVE_DECISIONS = ROOT / "data" / "review" / "reviewed_negative_decisions.local.json"
BENCHMARK_TIERS = ROOT / "data" / "modeling" / "irregular_transition_benchmark_tiers.json"
OUT = ROOT / "data" / "review" / "irregular_transition_model_validation.json"

FEATURES = [
    "event_type_coup_count",
    "high_severity_episode_count",
    "episode_construct_regime_vulnerability_count",
    "escalating_episode_count",
    "episode_start_count",
    "deed_type_destabilizing_count",
    "event_shock_flag",
    "high_salience_event_count",
    "event_type_conflict_count",
    "event_type_protest_count",
    "state_capacity_composite",
    "external_pressure_sanctions_active",
    "economic_fragility_fx_stress",
    "time_since_last_coup",
    "coup_count_5y",
    "regime_shift_flag",
    "polyarchy_delta_1y",
    "trade_openness_delta_3y",
    "oda_received_delta_3y",
    "transition_rupture_precursor_score",
    "transition_contestation_load_score",
    "transition_specificity_gap",
]


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
    accuracy = (tp + tn) / len(y_true) if y_true else 0.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision_pct": round(precision * 100.0, 3),
        "recall_pct": round(recall * 100.0, 3),
        "specificity_pct": round(specificity * 100.0, 3),
        "f1_pct": round(f1 * 100.0, 3),
        "accuracy_pct": round(accuracy * 100.0, 3),
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


def build_fit_sample() -> list[dict]:
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

    sample = []
    for key in sorted(gold_keys):
        row = panel_lookup.get(key)
        if not row:
            continue
        sample.append({
            "country": key[0],
            "panel_date": key[1],
            "y_true": 1,
            "label_group": "gold_positive",
            "benchmark_tier": benchmark_tier_lookup.get(key, "gold_positive"),
            **{feature: row.get(feature) for feature in FEATURES},
            "signal_score_1m": int(row.get("irregular_transition_fit_score_next_1m") or 0),
            "signal_label_1m": str(row.get("irregular_transition_fit_label_next_1m") or ""),
            "operational_label_1m": int(row.get("irregular_transition_next_1m") or 0),
        })

    for key in sorted((reviewed_watch_keys | weak_keys | local_negative_keys) - gold_keys):
        row = panel_lookup.get(key)
        if not row:
            continue
        sample.append({
            "country": key[0],
            "panel_date": key[1],
            "y_true": 0,
            "label_group": (
                "local_reviewed_negative"
                if key in local_negative_keys
                else ("reviewed_watch_negative" if key in reviewed_watch_keys else "weak_review_negative")
            ),
            "benchmark_tier": benchmark_tier_lookup.get(key, "unclassified_negative"),
            **{feature: row.get(feature) for feature in FEATURES},
            "signal_score_1m": int(row.get("irregular_transition_fit_score_next_1m") or 0),
            "signal_label_1m": str(row.get("irregular_transition_fit_label_next_1m") or ""),
            "operational_label_1m": int(row.get("irregular_transition_next_1m") or 0),
        })

    sample.sort(key=lambda item: (item["country"], item["panel_date"], item["y_true"]))
    return sample


def value_or_zero(value: object) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def main() -> None:
    sample = build_fit_sample()
    y_true = [int(row["y_true"]) for row in sample]

    baseline_pred = [int(row["signal_score_1m"] >= 4) for row in sample]
    operational_pred = [int(row["operational_label_1m"]) for row in sample]
    for idx, pred in enumerate(baseline_pred):
        sample[idx]["baseline_pred"] = pred
    for idx, pred in enumerate(operational_pred):
        sample[idx]["operational_pred"] = pred

    X = np.array([[value_or_zero(row.get(feature)) for feature in FEATURES] for row in sample], dtype=float)
    y = np.array(y_true, dtype=int)

    loo = LeaveOneOut()
    logistic_proba: list[float] = []
    logistic_pred: list[int] = []

    for train_idx, test_idx in loo.split(X):
        model = Pipeline([
            ("scale", StandardScaler()),
            ("logit", LogisticRegression(class_weight="balanced", solver="liblinear", max_iter=1000)),
        ])
        model.fit(X[train_idx], y[train_idx])
        proba = float(model.predict_proba(X[test_idx])[0][1])
        pred = int(proba >= 0.5)
        logistic_proba.append(round(proba, 6))
        logistic_pred.append(pred)
    for idx, pred in enumerate(logistic_pred):
        sample[idx]["logistic_loo_pred"] = pred
        sample[idx]["logistic_loo_proba"] = logistic_proba[idx]

    final_model = Pipeline([
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(class_weight="balanced", solver="liblinear", max_iter=1000)),
    ])
    final_model.fit(X, y)
    coef = final_model.named_steps["logit"].coef_[0]
    intercept = float(final_model.named_steps["logit"].intercept_[0])

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_model_validation",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "gold_file": str(GOLD.relative_to(ROOT)),
        "validation_sample": {
            "rows": len(sample),
            "gold_positive_rows": sum(1 for row in sample if row["label_group"] == "gold_positive"),
            "reviewed_watch_negative_rows": sum(1 for row in sample if row["label_group"] == "reviewed_watch_negative"),
            "weak_review_negative_rows": sum(1 for row in sample if row["label_group"] == "weak_review_negative"),
            "local_reviewed_negative_rows": sum(1 for row in sample if row["label_group"] == "local_reviewed_negative"),
        },
        "feature_set": FEATURES,
        "baseline_score_threshold_result": metrics(y_true, baseline_pred),
        "baseline_score_threshold_tier_results": tier_metrics(sample, "baseline_pred"),
        "operational_label_result": metrics(y_true, operational_pred),
        "operational_label_tier_results": tier_metrics(sample, "operational_pred"),
        "logistic_loo_result": metrics(y_true, logistic_pred),
        "logistic_loo_tier_results": tier_metrics(sample, "logistic_loo_pred"),
        "logistic_configuration": {
            "validation": "leave_one_out",
            "class_weight": "balanced",
            "solver": "liblinear",
            "probability_threshold": 0.5,
        },
        "full_sample_logistic_coefficients": {
            "intercept": round(intercept, 6),
            "features": [
                {"feature": feature, "coefficient": round(float(weight), 6)}
                for feature, weight in sorted(zip(FEATURES, coef), key=lambda item: abs(item[1]), reverse=True)
            ],
        },
        "rows": [
            row
            for row in sample
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote model validation report to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
