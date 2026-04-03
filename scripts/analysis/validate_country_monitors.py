#!/usr/bin/env python3
"""
Validate SENTINEL country monitor outputs against benchmark target ranges.

Inputs:
  config/risk_model_benchmarks.json
  data/published/country_monitors.json

Output:
  data/review/country_monitor_validation.json
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BENCHMARKS = ROOT / "config" / "risk_model_benchmarks.json"
COUNTRY_MONITORS = ROOT / "data" / "published" / "country_monitors.json"
OUT = ROOT / "data" / "review" / "country_monitor_validation.json"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def score_for_country(row: dict, metric: str) -> float | None:
    if metric == "overall_risk":
        return row.get("predictive_summary", {}).get("overall_risk_score")
    for construct in row.get("risk_constructs", []):
        if construct.get("code") == metric:
            return construct.get("score")
    return None


def distance_to_range(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 0.0
    if value < low:
        return round(low - value, 2)
    return round(value - high, 2)


def midpoint(low: float, high: float) -> float:
    return (low + high) / 2.0


def validate(benchmarks_path: Path, monitors_path: Path) -> dict:
    benchmarks = load_json(benchmarks_path)
    monitor_payload = load_json(monitors_path)
    monitor_rows = {row["country"]: row for row in monitor_payload.get("countries", [])}

    results = []
    metric_summary: dict[str, dict] = {}

    for benchmark in benchmarks.get("benchmarks", []):
        country = benchmark["country"]
        row = monitor_rows.get(country)
        if not row:
            results.append({
                "country": country,
                "status": "missing_country",
                "reason": benchmark.get("reason"),
            })
            continue

        metric_results = []
        for metric, target in benchmark.get("targets", {}).items():
            actual = score_for_country(row, metric)
            low = float(target["min"])
            high = float(target["max"])
            mid = midpoint(low, high)
            if actual is None:
                metric_results.append({
                    "metric": metric,
                    "status": "missing_metric",
                    "target_min": low,
                    "target_max": high,
                    "actual": None,
                })
                continue
            actual = float(actual)
            within = low <= actual <= high
            error = distance_to_range(actual, low, high)
            metric_results.append({
                "metric": metric,
                "status": "within_range" if within else "out_of_range",
                "target_min": low,
                "target_max": high,
                "target_midpoint": round(mid, 2),
                "actual": round(actual, 2),
                "distance_to_range": error,
                "distance_to_midpoint": round(abs(actual - mid), 2),
            })

            summary = metric_summary.setdefault(metric, {
                "count": 0,
                "within_range": 0,
                "mean_abs_distance_to_midpoint": 0.0,
                "mean_distance_outside_range": 0.0,
            })
            summary["count"] += 1
            summary["within_range"] += 1 if within else 0
            summary["mean_abs_distance_to_midpoint"] += abs(actual - mid)
            summary["mean_distance_outside_range"] += error

        overall_ok = all(item["status"] == "within_range" for item in metric_results if item["status"] != "missing_metric")
        results.append({
            "country": country,
            "reason": benchmark.get("reason"),
            "status": "passes" if overall_ok else "needs_review",
            "metrics": metric_results,
        })

    for metric, summary in metric_summary.items():
        count = max(summary["count"], 1)
        summary["within_range_rate"] = round(summary["within_range"] / count, 3)
        summary["mean_abs_distance_to_midpoint"] = round(summary["mean_abs_distance_to_midpoint"] / count, 2)
        summary["mean_distance_outside_range"] = round(summary["mean_distance_outside_range"] / count, 2)

    failing = [
        item for item in results
        if item.get("status") == "needs_review"
    ]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "benchmark_file": str(benchmarks_path.relative_to(ROOT)),
        "monitor_file": str(monitors_path.relative_to(ROOT)),
        "benchmark_count": len(benchmarks.get("benchmarks", [])),
        "country_result_count": len(results),
        "failing_country_count": len(failing),
        "metric_summary": metric_summary,
        "countries": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate country monitor outputs against benchmark ranges")
    parser.add_argument("--benchmarks", type=Path, default=BENCHMARKS)
    parser.add_argument("--monitors", type=Path, default=COUNTRY_MONITORS)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()

    payload = validate(args.benchmarks, args.monitors)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote validation report to {args.output}")
    print(f"Benchmarks evaluated: {payload['benchmark_count']}")
    print(f"Countries needing review: {payload['failing_country_count']}")


if __name__ == "__main__":
    main()
