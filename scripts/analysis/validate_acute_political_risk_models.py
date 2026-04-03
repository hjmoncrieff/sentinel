#!/usr/bin/env python3
"""
Run a first private model-validation comparison for acute political-risk.

This stage compares:
- the current score-threshold baseline
- a leave-one-out logistic regression baseline

against the reviewed fit-ready acute-risk sample built from:
- positives: gold acute-risk labels
- negatives: hard and easy acute-risk benchmark negatives
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
FIT_DATASET = ROOT / "data" / "modeling" / "acute_political_risk_fit_dataset.json"
OUT = ROOT / "data" / "review" / "acute_political_risk_model_validation.json"


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


def value_or_zero(value: object) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def main() -> None:
    payload = load_json(FIT_DATASET)
    sample = payload.get("rows", []) if isinstance(payload, dict) else payload
    features = payload.get("fit_features", []) if isinstance(payload, dict) else []
    y_true = [int(row["y_true"]) for row in sample]

    baseline_pred = [int(int(row.get("signal_score_1m") or 0) >= 4) for row in sample]
    for idx, pred in enumerate(baseline_pred):
        sample[idx]["baseline_pred"] = pred

    X = np.array([[value_or_zero(row.get(feature)) for feature in features] for row in sample], dtype=float)
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
        "status": "private_internal_acute_political_risk_model_validation",
        "fit_dataset_file": str(FIT_DATASET.relative_to(ROOT)),
        "validation_sample": payload.get("summary", {}) if isinstance(payload, dict) else {"rows": len(sample)},
        "feature_set": features,
        "baseline_score_threshold_result": metrics(y_true, baseline_pred),
        "baseline_score_threshold_tier_results": tier_metrics(sample, "baseline_pred"),
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
                for feature, weight in sorted(zip(features, coef), key=lambda item: abs(item[1]), reverse=True)
            ],
        },
        "rows": sample,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote acute-risk model validation report to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
