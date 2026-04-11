#!/usr/bin/env python3
"""
Build the first private annual latent-design matrix for SENTINEL.

Outputs:
  data/modeling/latent_design_matrix.json
  data/modeling/latent_design_matrix.csv
  data/review/latent_design_matrix_coverage.json
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COUNTRY_YEAR_IN = ROOT / "data" / "cleaned" / "country_year.json"
OUT_JSON = ROOT / "data" / "modeling" / "latent_design_matrix.json"
OUT_CSV = ROOT / "data" / "modeling" / "latent_design_matrix.csv"
OUT_REVIEW = ROOT / "data" / "review" / "latent_design_matrix_coverage.json"

CC_VARS = [
    "mil_constrain",
    "mil_exec",
    "coup_event",
    "coup_attempts",
    "judicial_constraints",
    "legislative_constraints",
    "rule_of_law_vdem",
    "cs_repress",
    "election_repression",
    "m3_mil_origin",
    "m3_mil_leader",
    "m3_mil_mod",
    "m3_mil_veto",
    "m3_mil_impunity",
    "m3_mil_repress",
    "m3_mil_crime_police",
    "m3_mil_law_enforcement",
    "m3_mil_peace_order",
    "m3_mil_police_overlap",
    "sentinel_coup_family_count_y",
    "sentinel_purge_family_count_y",
    "sentinel_domestic_military_role_count_y",
]

MIL_VARS = [
    "mil_exec",
    "mil_constrain",
    "cs_repress",
    "political_violence",
    "regime_type",
    "polyarchy",
    "m3_conscription",
    "m3_conscription_dur_max",
    "m3_mil_crime_police",
    "m3_mil_law_enforcement",
    "m3_mil_peace_order",
    "m3_mil_police_overlap",
    "m3_mil_repress",
    "m3_mil_impunity",
    "m3_mil_eco",
    "m3_milex_gdp",
    "m3_pers_to_pop",
    "m3_reserve_pop",
    "m3_hwi",
    "sentinel_domestic_military_role_count_y",
    "sentinel_military_policing_role_count_y",
    "sentinel_exception_rule_militarization_count_y",
]

MIN_ELIGIBLE_SHARE = 0.75
FIRST_M3_YEAR = 1990


def non_null_count(row: dict, fields: list[str]) -> int:
    return sum(1 for field in fields if row.get(field) is not None)


def build_row(row: dict) -> dict:
    cc_count = non_null_count(row, CC_VARS)
    mil_count = non_null_count(row, MIL_VARS)
    cc_share = round(cc_count / len(CC_VARS), 3)
    mil_share = round(mil_count / len(MIL_VARS), 3)
    year = int(row["year"])
    cc_eligible = int(year >= FIRST_M3_YEAR and cc_share >= MIN_ELIGIBLE_SHARE)
    mil_eligible = int(year >= FIRST_M3_YEAR and mil_share >= MIN_ELIGIBLE_SHARE)

    out = {
        "country": row["country"],
        "iso3": row["iso3"],
        "year": year,
        "m3_source_year": row.get("m3_source_year"),
        "m3_observed_year": row.get("m3_observed_year"),
        "cc_non_null_count": cc_count,
        "cc_non_null_share": cc_share,
        "cc_v0_eligible": cc_eligible,
        "mil_non_null_count": mil_count,
        "mil_non_null_share": mil_share,
        "mil_v0_eligible": mil_eligible,
    }
    for field in sorted(set(CC_VARS + MIL_VARS)):
        out[field] = row.get(field)
    return out


def summarize(rows: list[dict]) -> dict:
    cc_eligible = [row for row in rows if row["cc_v0_eligible"]]
    mil_eligible = [row for row in rows if row["mil_v0_eligible"]]

    def by_country(target_rows: list[dict], field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in target_rows:
            counts[row["country"]] = counts.get(row["country"], 0) + int(row[field])
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(COUNTRY_YEAR_IN.relative_to(ROOT)),
        "cc_variables": CC_VARS,
        "mil_variables": MIL_VARS,
        "min_eligible_share": MIN_ELIGIBLE_SHARE,
        "first_m3_year": FIRST_M3_YEAR,
        "row_count": len(rows),
        "country_count": len({row["country"] for row in rows}),
        "cc_v0_eligible_count": len(cc_eligible),
        "mil_v0_eligible_count": len(mil_eligible),
        "cc_v0_eligible_by_country": by_country(rows, "cc_v0_eligible"),
        "mil_v0_eligible_by_country": by_country(rows, "mil_v0_eligible"),
        "cc_v0_year_range": [
            min((row["year"] for row in cc_eligible), default=None),
            max((row["year"] for row in cc_eligible), default=None),
        ],
        "mil_v0_year_range": [
            min((row["year"] for row in mil_eligible), default=None),
            max((row["year"] for row in mil_eligible), default=None),
        ],
    }


def main() -> None:
    payload = json.loads(COUNTRY_YEAR_IN.read_text(encoding="utf-8"))
    source_rows = payload["rows"]
    rows = [build_row(row) for row in source_rows]
    summary = summarize(rows)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_REVIEW.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(
        json.dumps(
            {
                "generated_at": summary["generated_at"],
                "source_file": summary["source_file"],
                "cc_variables": CC_VARS,
                "mil_variables": MIL_VARS,
                "min_eligible_share": MIN_ELIGIBLE_SHARE,
                "first_m3_year": FIRST_M3_YEAR,
                "row_count": len(rows),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    OUT_REVIEW.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote latent design JSON to {OUT_JSON}")
    print(f"Wrote latent design CSV to {OUT_CSV}")
    print(f"Wrote coverage summary to {OUT_REVIEW}")
    print(f"Rows: {len(rows)}")
    print(f"CC v0 eligible rows: {summary['cc_v0_eligible_count']}")
    print(f"Militarization v0 eligible rows: {summary['mil_v0_eligible_count']}")


if __name__ == "__main__":
    main()
