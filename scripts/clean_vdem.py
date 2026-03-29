"""
clean_vdem.py
Cleans the V-Dem Country-Year Core CSV and writes SENTINEL-ready outputs to
data/cleaned/vdem.json and data/cleaned/vdem.csv.

Usage:
    python scripts/clean_vdem.py
    # Reads data/raw/vdem.csv relative to the repo root (one level above scripts/).
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths (resolved relative to this script file so it works from any cwd)
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.join(SCRIPT_DIR, "..")
RAW_CSV     = os.path.join(REPO_ROOT, "data", "raw", "vdem.csv")
OUT_DIR     = os.path.join(REPO_ROOT, "data", "cleaned")
OUT_JSON    = os.path.join(OUT_DIR, "vdem.json")
OUT_CSV     = os.path.join(OUT_DIR, "vdem.csv")

# ---------------------------------------------------------------------------
# SENTINEL canonical country list  →  V-Dem country_name spelling
# (Both happen to match exactly, but the map makes future divergence easy.)
# ---------------------------------------------------------------------------
VDEM_NAME_MAP: dict[str, str] = {
    "Argentina":           "Argentina",
    "Belize":              "Belize",
    "Bolivia":             "Bolivia",
    "Brazil":              "Brazil",
    "Chile":               "Chile",
    "Colombia":            "Colombia",
    "Costa Rica":          "Costa Rica",
    "Cuba":                "Cuba",
    "Dominican Republic":  "Dominican Republic",
    "Ecuador":             "Ecuador",
    "El Salvador":         "El Salvador",
    "Guatemala":           "Guatemala",
    "Guyana":              "Guyana",
    "Haiti":               "Haiti",
    "Honduras":            "Honduras",
    "Jamaica":             "Jamaica",
    "Mexico":              "Mexico",
    "Nicaragua":           "Nicaragua",
    "Panama":              "Panama",
    "Paraguay":            "Paraguay",
    "Peru":                "Peru",
    "Suriname":            "Suriname",
    "Trinidad and Tobago": "Trinidad and Tobago",
    "Uruguay":             "Uruguay",
    "Venezuela":           "Venezuela",
}

# V-Dem name  →  SENTINEL canonical name (reverse lookup)
VDEM_TO_SENTINEL: dict[str, str] = {v: k for k, v in VDEM_NAME_MAP.items()}
VDEM_NAMES: set[str] = set(VDEM_NAME_MAP.values())

YEAR_MIN = 1990
YEAR_MAX = 2023

# ---------------------------------------------------------------------------
# Column mapping:  output key  →  (vdem_csv_column, human label)
# ---------------------------------------------------------------------------
COL_MAP: dict[str, tuple[str, str]] = {
    "polyarchy":        ("v2x_polyarchy",   "Electoral democracy index (0-1)"),
    "regime_type":      ("v2x_regime",      "Regime type: 0=closed autocracy, 1=electoral autocracy, 2=electoral democracy, 3=liberal democracy"),
    "physinteg":        ("v2x_clphy",       "Physical integrity index (0-1)"),
    "mil_constrain":    ("v2stcritapparm",  "Military constraints on executive (ordinal, higher=more civilian control)"),
    "mil_exec":         ("v2x_ex_military", "Executive is military officer (0-1)"),
    "coup_event":       ("e_pt_coup",       "Coup event occurred (0/1)"),
    "coup_attempts":    ("e_pt_coup_attempts", "Number of coup attempts"),
    "polity2":          ("e_polity2",       "Polity2 score (-10 to +10)"),
    "cs_repress":       ("v2csreprss",      "Civil society repression"),
    "political_violence": ("v2caviol",      "Political violence"),
}

# Keys whose values should be stored as int (0/1 flags, integer counts, ordinal)
INT_KEYS = {"coup_event", "coup_attempts", "polity2"}

# Series keys included in the per-country time-series block
SERIES_KEYS = [
    "polyarchy", "regime_type", "polity2", "physinteg",
    "coup_event", "coup_attempts", "mil_exec", "mil_constrain",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_float(val: str) -> float | None:
    """Return float, or None for blanks / non-numeric strings."""
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in ("na", "nan", "none", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def coerce_value(key: str, val: str):
    """Return appropriately typed value for an output key."""
    f = safe_float(val)
    if f is None:
        return None
    if key in INT_KEYS:
        return int(round(f))
    return round(f, 6)   # keep full precision; JSON encoder trims trailing zeros


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(RAW_CSV):
        print(f"ERROR: raw CSV not found: {RAW_CSV}")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Reading {RAW_CSV} …")

    # country_vdem_name  →  year (int)  →  {out_key: value}
    raw: dict[str, dict[int, dict]] = {}

    with open(RAW_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])

        missing_cols = [v for v, _ in COL_MAP.values() if v not in headers]
        if missing_cols:
            print(f"  WARNING: these V-Dem columns were not found in the CSV: {missing_cols}")

        row_count = 0
        kept_count = 0
        for row in reader:
            row_count += 1
            country = row.get("country_name", "").strip()
            if country not in VDEM_NAMES:
                continue
            try:
                year = int(float(row.get("year") or 0))
            except (ValueError, TypeError):
                continue
            if not (YEAR_MIN <= year <= YEAR_MAX):
                continue

            kept_count += 1
            if country not in raw:
                raw[country] = {}
            raw[country][year] = {
                out_key: coerce_value(out_key, row.get(vdem_col, ""))
                for out_key, (vdem_col, _) in COL_MAP.items()
                if vdem_col in headers
            }

    print(f"  Scanned {row_count:,} rows; kept {kept_count:,} (LatAm 1990–2023)")

    all_years = list(range(YEAR_MIN, YEAR_MAX + 1))

    # ---------------------------------------------------------------------------
    # Build per-country objects
    # ---------------------------------------------------------------------------
    countries_out = []
    csv_rows = []

    for sentinel_name in sorted(VDEM_NAME_MAP.keys()):
        vdem_name = VDEM_NAME_MAP[sentinel_name]
        year_data = raw.get(vdem_name, {})
        if not year_data:
            print(f"  WARNING: no data for {sentinel_name}")
            continue

        # Latest non-null snapshot for each indicator individually
        def latest_value(key):
            for yr in sorted(year_data.keys(), reverse=True):
                v = year_data[yr].get(key)
                if v is not None:
                    return yr, v
            return None, None

        # Overall latest year (max year with ANY data)
        latest_year = max(year_data.keys())

        snapshot = {}
        for key in COL_MAP:
            _, v = latest_value(key)
            snapshot[key] = v

        # Build series arrays (all_years, None where missing)
        series = {}
        for key in SERIES_KEYS:
            series[key] = [
                {"year": yr, "value": year_data[yr].get(key) if yr in year_data else None}
                for yr in all_years
            ]

        country_obj = {
            "country":    sentinel_name,
            "latest_year": latest_year,
            **snapshot,
            "series": series,
        }
        countries_out.append(country_obj)

        # CSV rows: one per year (only years with data)
        for yr in sorted(year_data.keys()):
            row_out = {"country": sentinel_name, "year": yr}
            row_out.update(year_data[yr])
            csv_rows.append(row_out)

        print(f"  {sentinel_name}: {min(year_data.keys())}–{latest_year} ({len(year_data)} years)")

    # ---------------------------------------------------------------------------
    # Write JSON
    # ---------------------------------------------------------------------------
    payload = {
        "updated":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":   "V-Dem Country-Year Core v16",
        "years":    all_years,
        "columns":  {out_key: label for out_key, (_, label) in COL_MAP.items()},
        "countries": countries_out,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n  → {OUT_JSON}  ({len(countries_out)} countries)")

    # ---------------------------------------------------------------------------
    # Write CSV
    # ---------------------------------------------------------------------------
    csv_fieldnames = ["country", "year"] + list(COL_MAP.keys())
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"  → {OUT_CSV}  ({len(csv_rows)} rows)")
    print("\nDone.")


if __name__ == "__main__":
    main()
