#!/usr/bin/env python3
"""
Fit first-pass static latent scores for SENTINEL annual constructs.

This is a transparent v0 extractor, not the final measurement model.
It uses:
  1. eligibility-gated country-year rows from latent_design_matrix.json
  2. median imputation within the eligible sample
  3. standardized inputs
  4. one-factor extraction via sklearn FactorAnalysis
  5. sign orientation against anchor variables

Outputs:
  data/modeling/static_latent_scores_v0.json
  data/modeling/static_latent_scores_v0.csv
  data/review/static_latent_scores_v0_diagnostics.json
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sklearn.decomposition import FactorAnalysis

ROOT = Path(__file__).resolve().parent.parent.parent
DESIGN_IN = ROOT / "data" / "modeling" / "latent_design_matrix.json"
COUNTRY_YEAR_IN = ROOT / "data" / "cleaned" / "country_year.json"
OUT_JSON = ROOT / "data" / "modeling" / "static_latent_scores_v0.json"
OUT_CSV = ROOT / "data" / "modeling" / "static_latent_scores_v0.csv"
OUT_REVIEW = ROOT / "data" / "review" / "static_latent_scores_v0_diagnostics.json"

CC_NAME = "civilian_control_latent_v0"
MIL_NAME = "militarization_latent_v0"


@dataclass(frozen=True)
class Spec:
    name: str
    variables: list[str]
    eligible_field: str
    positive_anchors: list[str]
    negative_anchors: list[str]


CC_SPEC = Spec(
    name=CC_NAME,
    variables=[
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
    ],
    eligible_field="cc_v0_eligible",
    positive_anchors=[
        "mil_constrain",
        "judicial_constraints",
        "legislative_constraints",
        "rule_of_law_vdem",
    ],
    negative_anchors=[
        "mil_exec",
        "coup_event",
        "coup_attempts",
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
    ],
)

MIL_SPEC = Spec(
    name=MIL_NAME,
    variables=[
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
    ],
    eligible_field="mil_v0_eligible",
    positive_anchors=[
        "mil_exec",
        "cs_repress",
        "political_violence",
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
        "sentinel_domestic_military_role_count_y",
        "sentinel_military_policing_role_count_y",
        "sentinel_exception_rule_militarization_count_y",
    ],
    negative_anchors=[
        "mil_constrain",
        "polyarchy",
    ],
)


def load_rows() -> tuple[dict, list[dict]]:
    payload = json.loads(DESIGN_IN.read_text(encoding="utf-8"))
    return payload, payload["rows"]


def load_country_year_index() -> dict[tuple[str, int], dict]:
    payload = json.loads(COUNTRY_YEAR_IN.read_text(encoding="utf-8"))
    return {(row["country"], int(row["year"])): row for row in payload["rows"]}


def finite_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(out) or np.isinf(out):
        return None
    return out


def build_matrix(
    rows: list[dict],
    variables: list[str],
) -> tuple[np.ndarray, list[str], list[str], dict[str, float], dict[str, float]]:
    medians: dict[str, float] = {}
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    columns: list[np.ndarray] = []
    used_variables: list[str] = []
    dropped_variables: list[str] = []

    for variable in variables:
        values = np.array(
            [
                value
                for row in rows
                if (value := finite_or_none(row.get(variable))) is not None
            ],
            dtype=float,
        )
        if values.size == 0:
            dropped_variables.append(variable)
            continue
        median = float(np.median(values))
        filled = np.array(
            [
                value if (value := finite_or_none(row.get(variable))) is not None else median
                for row in rows
            ],
            dtype=float,
        )
        mean = float(filled.mean())
        std = float(filled.std())
        if std == 0:
            std = 1.0
        standardized = (filled - mean) / std
        medians[variable] = median
        means[variable] = mean
        stds[variable] = std
        columns.append(standardized)
        used_variables.append(variable)

    matrix = np.column_stack(columns)
    return (
        matrix,
        used_variables,
        dropped_variables,
        medians,
        {k: means[k] for k in used_variables} | {f"{k}__std": stds[k] for k in used_variables},
    )


def corr(a: np.ndarray, b: np.ndarray) -> float | None:
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def orient_scores(
    scores: np.ndarray,
    rows: list[dict],
    spec: Spec,
) -> tuple[np.ndarray, int, dict[str, float | None]]:
    anchor_map: dict[str, float | None] = {}
    orientation_vote = 0.0

    for variable in spec.positive_anchors:
        values = np.array(
            [
                value if (value := finite_or_none(row.get(variable))) is not None else np.nan
                for row in rows
            ],
            dtype=float,
        )
        mask = ~np.isnan(values)
        value = corr(scores[mask], values[mask]) if mask.sum() >= 3 else None
        anchor_map[variable] = value
        if value is not None:
            orientation_vote += value

    for variable in spec.negative_anchors:
        values = np.array(
            [
                value if (value := finite_or_none(row.get(variable))) is not None else np.nan
                for row in rows
            ],
            dtype=float,
        )
        mask = ~np.isnan(values)
        value = corr(scores[mask], values[mask]) if mask.sum() >= 3 else None
        anchor_map[variable] = value
        if value is not None:
            orientation_vote -= value

    sign = 1 if orientation_vote >= 0 else -1
    return scores * sign, sign, anchor_map


def fit_construct(rows: list[dict], spec: Spec) -> tuple[dict[tuple[str, int], dict], dict]:
    eligible_rows = [row for row in rows if int(row.get(spec.eligible_field, 0)) == 1]
    matrix, used_variables, dropped_variables, medians, standardization = build_matrix(
        eligible_rows, spec.variables
    )

    model = FactorAnalysis(n_components=1, random_state=42)
    raw_scores = model.fit_transform(matrix).ravel()
    oriented_scores, sign, anchor_corrs = orient_scores(raw_scores, eligible_rows, spec)

    mean = float(oriented_scores.mean())
    std = float(oriented_scores.std())
    if std == 0:
        std = 1.0
    z_scores = (oriented_scores - mean) / std
    score_0100 = np.clip(50 + 15 * z_scores, 0, 100)

    row_scores: dict[tuple[str, int], dict] = {}
    for idx, row in enumerate(eligible_rows):
        row_scores[(row["country"], int(row["year"]))] = {
            f"{spec.name}_raw": round(float(oriented_scores[idx]), 6),
            f"{spec.name}_z": round(float(z_scores[idx]), 6),
            f"{spec.name}_score": round(float(score_0100[idx]), 3),
        }

    loadings = {}
    for idx, variable in enumerate(used_variables):
        loadings[variable] = round(float(model.components_[0][idx] * sign), 6)

    diagnostics = {
        "eligible_row_count": len(eligible_rows),
        "eligible_country_count": len({row["country"] for row in eligible_rows}),
        "eligible_year_range": [
            min((int(row["year"]) for row in eligible_rows), default=None),
            max((int(row["year"]) for row in eligible_rows), default=None),
        ],
        "orientation_sign": sign,
        "requested_variables": spec.variables,
        "used_variables": used_variables,
        "dropped_variables": dropped_variables,
        "anchor_correlations": anchor_corrs,
        "loadings": dict(sorted(loadings.items(), key=lambda item: abs(item[1]), reverse=True)),
        "medians": medians,
        "standardization": standardization,
        "score_summary": {
            "raw_min": round(float(oriented_scores.min()), 6),
            "raw_max": round(float(oriented_scores.max()), 6),
            "score_min": round(float(score_0100.min()), 3),
            "score_max": round(float(score_0100.max()), 3),
            "score_mean": round(float(score_0100.mean()), 3),
            "score_std": round(float(score_0100.std()), 3),
        },
        "top_years": {
            "highest_mean_score_years": top_group_means(eligible_rows, score_0100, "year", descending=True),
            "lowest_mean_score_years": top_group_means(eligible_rows, score_0100, "year", descending=False),
        },
        "top_countries": {
            "highest_mean_score_countries": top_group_means(eligible_rows, score_0100, "country", descending=True),
            "lowest_mean_score_countries": top_group_means(eligible_rows, score_0100, "country", descending=False),
        },
    }
    return row_scores, diagnostics


def top_group_means(rows: list[dict], scores: np.ndarray, field: str, descending: bool) -> list[dict]:
    buckets: dict[str, list[float]] = {}
    for idx, row in enumerate(rows):
        buckets.setdefault(str(row[field]), []).append(float(scores[idx]))
    ranked = sorted(
        (
            {
                field: key,
                "mean_score": round(sum(vals) / len(vals), 3),
                "n": len(vals),
            }
            for key, vals in buckets.items()
        ),
        key=lambda item: item["mean_score"],
        reverse=descending,
    )
    return ranked[:10]


def merge_outputs(source_rows: list[dict], cc_scores: dict, mil_scores: dict) -> list[dict]:
    merged: list[dict] = []
    for row in source_rows:
        key = (row["country"], int(row["year"]))
        out = {
            "country": row["country"],
            "iso3": row["iso3"],
            "year": int(row["year"]),
            "cc_v0_eligible": int(row.get("cc_v0_eligible", 0)),
            "mil_v0_eligible": int(row.get("mil_v0_eligible", 0)),
            f"{CC_NAME}_score": None,
            f"{CC_NAME}_z": None,
            f"{CC_NAME}_raw": None,
            f"{MIL_NAME}_score": None,
            f"{MIL_NAME}_z": None,
            f"{MIL_NAME}_raw": None,
        }
        out.update({k: v for k, v in cc_scores.get(key, {}).items()})
        out.update({k: v for k, v in mil_scores.get(key, {}).items()})
        merged.append(out)
    return merged


def compare_with_live_indices(rows: list[dict], latent_field: str, live_field: str) -> float | None:
    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        latent_value = finite_or_none(row.get(latent_field))
        live_value = finite_or_none(row.get(live_field))
        if latent_value is None or live_value is None:
            continue
        xs.append(latent_value)
        ys.append(live_value)
    if len(xs) < 3:
        return None
    return corr(np.array(xs, dtype=float), np.array(ys, dtype=float))


def main() -> None:
    payload, source_rows = load_rows()
    country_year_index = load_country_year_index()
    cc_scores, cc_diag = fit_construct(source_rows, CC_SPEC)
    mil_scores, mil_diag = fit_construct(source_rows, MIL_SPEC)
    merged = merge_outputs(source_rows, cc_scores, mil_scores)

    merged_with_live = []
    for row in merged:
        joined = dict(row)
        base = country_year_index[(row["country"], int(row["year"]))]
        joined["regime_vulnerability"] = base.get("regime_vulnerability")
        joined["militarization"] = base.get("militarization")
        merged_with_live.append(joined)

    cc_live_corr = compare_with_live_indices(merged_with_live, f"{CC_NAME}_score", "regime_vulnerability")
    mil_live_corr = compare_with_live_indices(
        merged_with_live, f"{MIL_NAME}_score", "militarization"
    )

    diagnostics = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(DESIGN_IN.relative_to(ROOT)),
        "method": {
            "family": "static_one_factor_v0",
            "extractor": "sklearn FactorAnalysis(n_components=1)",
            "preprocessing": [
                "eligibility gate from latent design matrix",
                "median imputation within eligible sample",
                "standardization per variable",
                "post-fit sign orientation against anchor variables",
                "score rescaling to 0-100 via 50 + 15*z",
            ],
        },
        "coverage": {
            "row_count": len(source_rows),
            "cc_eligible_count": cc_diag["eligible_row_count"],
            "mil_eligible_count": mil_diag["eligible_row_count"],
            "cc_year_range": cc_diag["eligible_year_range"],
            "mil_year_range": mil_diag["eligible_year_range"],
        },
        "constructs": {
            CC_NAME: cc_diag,
            MIL_NAME: mil_diag,
        },
        "live_index_comparison": {
            "civilian_control_vs_regime_vulnerability_corr": cc_live_corr,
            "militarization_latent_vs_live_militarization_corr": mil_live_corr,
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_REVIEW.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(
        json.dumps(
            {
                "generated_at": diagnostics["generated_at"],
                "source_file": diagnostics["source_file"],
                "method": diagnostics["method"],
                "rows": merged,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(merged[0].keys()))
        writer.writeheader()
        writer.writerows(merged)

    OUT_REVIEW.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote static latent JSON to {OUT_JSON}")
    print(f"Wrote static latent CSV to {OUT_CSV}")
    print(f"Wrote static latent diagnostics to {OUT_REVIEW}")
    print(f"CC eligible rows: {cc_diag['eligible_row_count']}")
    print(f"Militarization eligible rows: {mil_diag['eligible_row_count']}")


if __name__ == "__main__":
    main()
