#!/usr/bin/env python3
"""
Build a first private adjudicated acute political-risk label layer.

This stage promotes a narrow set of reviewed benchmark positives into tracked
labels so the country-month panel can move beyond pure proxy logic for the
broader acute political-risk target.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW = ROOT / "data" / "review" / "acute_political_risk_target_review.json"
OUT = ROOT / "data" / "modeling" / "adjudicated_acute_political_risk_labels.json"
LOCAL_DECISIONS = ROOT / "data" / "review" / "adjudicated_acute_political_risk_decisions.local.json"

APPROVED_COUNTRIES = {"Bolivia", "Chile", "El Salvador", "Haiti", "Peru"}
ALLOWED_RATINGS = {"strong", "plausible"}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_local_decisions() -> list[dict]:
    if not LOCAL_DECISIONS.exists():
        return []
    payload = load_json(LOCAL_DECISIONS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return rows if isinstance(rows, list) else []


def build() -> dict:
    payload = load_json(REVIEW)
    countries = payload.get("countries", []) if isinstance(payload, dict) else []
    rows = []
    for country_row in countries:
        country = str(country_row.get("country") or "")
        if country not in APPROVED_COUNTRIES:
            continue
        for case in country_row.get("cases", []):
            rating = str(case.get("rating") or "")
            if rating not in ALLOWED_RATINGS:
                continue
            rows.append({
                "country": country,
                "panel_date": str(case.get("trigger_month") or ""),
                "target_name": "acute_political_risk_next_1m",
                "label": 1,
                "label_source": "adjudicated_benchmark_review",
                "rating": rating,
                "note": case.get("note"),
                "next_month": case.get("next_month"),
                "proxy_score_1m": case.get("score_1m"),
            })
    for row in load_local_decisions():
        country = str(row.get("country") or "")
        panel_date = str(row.get("panel_date") or "")
        target_name = str(row.get("target_name") or "acute_political_risk_next_1m")
        if not country or not panel_date or target_name != "acute_political_risk_next_1m":
            continue
        rows.append({
            "country": country,
            "panel_date": panel_date,
            "target_name": target_name,
            "label": int(row.get("label", 0)),
            "label_source": str(row.get("label_source") or "local_adjudication"),
            "rating": str(row.get("rating") or "reviewed"),
            "note": row.get("note"),
            "next_month": row.get("next_month"),
            "proxy_score_1m": row.get("proxy_score_1m"),
        })
    deduped: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        deduped[(row["country"], row["panel_date"], row["target_name"])] = row
    rows = [deduped[key] for key in sorted(deduped)]
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_adjudicated_acute_political_risk_label_artifact",
        "source_file": str(REVIEW.relative_to(ROOT)),
        "local_decision_file": str(LOCAL_DECISIONS.relative_to(ROOT)) if LOCAL_DECISIONS.exists() else None,
        "target_name": "acute_political_risk_next_1m",
        "description": (
            "First selective adjudicated acute political-risk label layer built "
            "from private benchmark review. This should remain narrower than "
            "the broader proxy layer."
        ),
        "approved_countries": sorted(APPROVED_COUNTRIES),
        "allowed_ratings": sorted(ALLOWED_RATINGS),
        "count": len(rows),
        "rows": rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote adjudicated acute political-risk labels to {OUT.relative_to(ROOT)}")
    print(f"Labels written: {payload['count']}")


if __name__ == "__main__":
    main()
