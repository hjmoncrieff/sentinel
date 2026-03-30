#!/usr/bin/env python3
"""
SENTINEL — Country-Year Join Table
Joins V-Dem, World Bank, and M3 data into a single country × year flat table.

Outputs:
  data/cleaned/country_year.json
  data/cleaned/country_year.csv

Usage:
  python3 scripts/build_country_year.py
  python3 scripts/build_country_year.py --output-dir data/cleaned
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

ROOT    = Path(__file__).parent.parent
VDEM_IN = ROOT / "data" / "cleaned" / "vdem.json"
WB_IN   = ROOT / "data" / "cleaned" / "worldbank.json"
OUT_DIR = ROOT / "data" / "cleaned"

# M3 indicators — static (2020 snapshot); applied to all years as structural flags
COUNTRY_M3 = {
    "Brazil":             {"conscription":1,"mil_veto":0,"mil_impunity":1,"mil_crime_police":0,"mil_eco":0,"hwi":1.3},
    "Colombia":           {"conscription":1,"mil_veto":0,"mil_impunity":0,"mil_crime_police":None,"mil_eco":1,"hwi":0.8},
    "Mexico":             {"conscription":1,"mil_veto":0,"mil_impunity":1,"mil_crime_police":1,"mil_eco":1,"hwi":1.0},
    "Venezuela":          {"conscription":1,"mil_veto":1,"mil_impunity":1,"mil_crime_police":0,"mil_eco":1,"hwi":3.6},
    "Argentina":          {"conscription":0,"mil_veto":0,"mil_impunity":0,"mil_crime_police":0,"mil_eco":0,"hwi":2.9},
    "Peru":               {"conscription":0,"mil_veto":0,"mil_impunity":1,"mil_crime_police":0,"mil_eco":1,"hwi":3.8},
    "Chile":              {"conscription":1,"mil_veto":0,"mil_impunity":0,"mil_crime_police":0,"mil_eco":1,"hwi":7.8},
    "Ecuador":            {"conscription":0,"mil_veto":0,"mil_impunity":0,"mil_crime_police":1,"mil_eco":1,"hwi":2.0},
    "Bolivia":            {"conscription":0,"mil_veto":0,"mil_impunity":1,"mil_crime_police":1,"mil_eco":1,"hwi":2.6},
    "Cuba":               {"conscription":1,"mil_veto":1,"mil_impunity":0,"mil_crime_police":0,"mil_eco":1,"hwi":19.6},
    "Honduras":           {"conscription":0,"mil_veto":0,"mil_impunity":1,"mil_crime_police":1,"mil_eco":1,"hwi":0.6},
    "Guatemala":          {"conscription":1,"mil_veto":0,"mil_impunity":1,"mil_crime_police":1,"mil_eco":1,"hwi":0.8},
    "El Salvador":        {"conscription":1,"mil_veto":0,"mil_impunity":1,"mil_crime_police":1,"mil_eco":1,"hwi":2.0},
    "Nicaragua":          {"conscription":0,"mil_veto":0,"mil_impunity":1,"mil_crime_police":1,"mil_eco":1,"hwi":8.0},
    "Paraguay":           {"conscription":1,"mil_veto":0,"mil_impunity":1,"mil_crime_police":None,"mil_eco":0,"hwi":0.5},
    "Uruguay":            {"conscription":0,"mil_veto":0,"mil_impunity":0,"mil_crime_police":1,"mil_eco":0,"hwi":15.0},
    "Haiti":              {"conscription":0,"mil_veto":None,"mil_impunity":None,"mil_crime_police":0,"mil_eco":0,"hwi":None},
    "Dominican Republic": {"conscription":0,"mil_veto":0,"mil_impunity":1,"mil_crime_police":None,"mil_eco":0,"hwi":0.3},
    "Jamaica":            {"conscription":0,"mil_veto":0,"mil_impunity":0,"mil_crime_police":1,"mil_eco":0,"hwi":0.4},
    "Trinidad and Tobago":{"conscription":0,"mil_veto":0,"mil_impunity":1,"mil_crime_police":0,"mil_eco":0,"hwi":None},
}

# ISO3 lookup
ISO3 = {
    "Brazil":"BRA","Colombia":"COL","Mexico":"MEX","Venezuela":"VEN","Argentina":"ARG",
    "Peru":"PER","Chile":"CHL","Ecuador":"ECU","Bolivia":"BOL","Cuba":"CUB",
    "Honduras":"HND","Guatemala":"GTM","El Salvador":"SLV","Nicaragua":"NIC",
    "Paraguay":"PRY","Uruguay":"URY","Haiti":"HTI","Dominican Republic":"DOM",
    "Panama":"PAN","Costa Rica":"CRI","Jamaica":"JAM","Trinidad and Tobago":"TTO",
    "Guyana":"GUY","Suriname":"SUR","Belize":"BLZ","Regional":"REG",
}

# WB series fields to include (field_name → output column name)
WB_SERIES = {
    "military_expenditure_pct_gdp_series":      "mil_exp_pct_gdp",
    "military_expenditure_current_usd_series":  "mil_exp_usd",
    "military_personnel_total_series":          "mil_personnel",
    "wgi_rule_of_law_series":                   "wgi_rule_of_law",
    "wgi_govt_effectiveness_series":            "wgi_govt_effectiveness",
    "wgi_control_of_corruption_series":         "wgi_control_corruption",
    "wgi_political_stability_series":           "wgi_political_stability",
    "gdp_constant_2015_usd_series":             "gdp_const_2015_usd",
    "gdp_per_capita_constant_2015_usd_series":  "gdp_per_capita_const_usd",
    "population_total_series":                  "population",
}

# V-Dem series fields to include
VDEM_SERIES = [
    "polyarchy", "regime_type", "physinteg", "mil_constrain",
    "mil_exec", "coup_event", "coup_attempts", "polity2",
    "cs_repress", "political_violence",
]


def main(out_dir: Path = OUT_DIR) -> None:
    print(f"Loading V-Dem from {VDEM_IN}")
    vdem_raw = json.loads(VDEM_IN.read_text(encoding="utf-8"))
    vdem_countries = {c["country"]: c for c in vdem_raw["countries"]}

    print(f"Loading World Bank from {WB_IN}")
    wb_raw = json.loads(WB_IN.read_text(encoding="utf-8"))
    wb_countries = {c["country"]: c for c in wb_raw["countries"]}

    # Build union of years (1990–2023 from V-Dem; WB goes to ~2024)
    years = list(range(1990, 2025))

    rows: list[dict] = []

    all_countries = sorted(set(list(vdem_countries.keys()) + list(wb_countries.keys())))

    for country in all_countries:
        iso3 = ISO3.get(country, "")
        m3 = COUNTRY_M3.get(country, {})
        vdem = vdem_countries.get(country)
        wb   = wb_countries.get(country)

        # Build V-Dem year → value lookup
        vdem_series: dict[str, dict[int, float | None]] = {}
        if vdem and "series" in vdem:
            for field in VDEM_SERIES:
                if field in vdem["series"]:
                    vdem_series[field] = {pt["year"]: pt["value"] for pt in vdem["series"][field]}

        # Build WB year → value lookup
        wb_series: dict[str, dict[int, float | None]] = {}
        if wb:
            for wb_field, col_name in WB_SERIES.items():
                if wb_field in wb:
                    wb_series[col_name] = {int(pt["year"]): pt["value"] for pt in wb[wb_field]}

        for year in years:
            row: dict = {
                "country":    country,
                "iso3":       iso3,
                "year":       year,
                # V-Dem indicators
                **{f: vdem_series.get(f, {}).get(year) for f in VDEM_SERIES},
                # WB indicators
                **{col: wb_series.get(col, {}).get(year) for col in WB_SERIES.values()},
                # M3 structural (static 2020 snapshot)
                "m3_conscription":       m3.get("conscription"),
                "m3_mil_veto":           m3.get("mil_veto"),
                "m3_mil_impunity":       m3.get("mil_impunity"),
                "m3_mil_crime_police":   m3.get("mil_crime_police"),
                "m3_mil_eco":            m3.get("mil_eco"),
                "m3_hwi":                m3.get("hwi"),
            }
            rows.append(row)

    rows.sort(key=lambda r: (r["country"], r["year"]))
    print(f"  {len(rows)} country-year rows built ({len(all_countries)} countries × {len(years)} years)")

    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Write JSON ─────────────────────────────────────────────
    json_path = out_dir / "country_year.json"
    json_path.write_text(
        json.dumps({
            "generated": datetime.utcnow().isoformat() + "Z",
            "schema_version": "1.0",
            "count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"JSON written: {json_path}")

    # ── Write CSV ──────────────────────────────────────────────
    csv_path = out_dir / "country_year.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV written: {csv_path}")

    # ── Coverage summary ───────────────────────────────────────
    from collections import Counter
    non_null = Counter()
    for r in rows:
        for k, v in r.items():
            if v is not None and k not in ("country", "iso3", "year"):
                non_null[k] += 1
    print("\nField coverage (non-null rows):")
    for field, n in sorted(non_null.items(), key=lambda x: -x[1]):
        pct = n / len(rows) * 100
        print(f"  {field:40s} {n:4d} / {len(rows)} ({pct:.0f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build SENTINEL country-year join table")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    main(args.output_dir)
