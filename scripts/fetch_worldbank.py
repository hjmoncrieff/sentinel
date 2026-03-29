"""
fetch_worldbank.py
Pulls World Bank WDI + WGI indicators for 25 SENTINEL countries.
Fetches the full 1990-2025 range.
Saves raw JSON per indicator to data/raw/ and merged CSV + JSON to data/cleaned/.

Run manually or add to GitHub Actions (no API key needed).
"""

import json
import os
import time
import csv
import requests
from datetime import datetime

# ── Country mapping ───────────────────────────────────────────────────────────
# ISO2 → SENTINEL canonical name
COUNTRIES = {
    "BR": "Brazil",        "CO": "Colombia",      "MX": "Mexico",
    "VE": "Venezuela",     "AR": "Argentina",     "PE": "Peru",
    "CL": "Chile",         "EC": "Ecuador",       "BO": "Bolivia",
    "CU": "Cuba",          "HN": "Honduras",      "GT": "Guatemala",
    "SV": "El Salvador",   "NI": "Nicaragua",     "PY": "Paraguay",
    "UY": "Uruguay",       "HT": "Haiti",         "DO": "Dominican Republic",
    "PA": "Panama",        "CR": "Costa Rica",    "JM": "Jamaica",
    "TT": "Trinidad and Tobago", "GY": "Guyana",  "SR": "Suriname",
    "BZ": "Belize",
}

ISO2_LIST = ";".join(COUNTRIES.keys())

# ── Indicators to fetch ───────────────────────────────────────────────────────
INDICATORS = {
    "SP.POP.TOTL":        "population_total",
    "NY.GDP.MKTP.KD":     "gdp_constant_2015_usd",
    "NY.GDP.PCAP.KD":     "gdp_per_capita_constant_2015_usd",
    "RL.EST":             "wgi_rule_of_law",
    "GE.EST":             "wgi_govt_effectiveness",
    "CC.EST":             "wgi_control_of_corruption",
    "PV.EST":             "wgi_political_stability",
    "MS.MIL.XPND.GD.ZS": "military_expenditure_pct_gdp",
    "MS.MIL.XPND.CD":    "military_expenditure_current_usd",
    "MS.MIL.TOTL.P1":    "military_personnel_total",
}

BASE_URL = "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"
PARAMS   = {"format": "json", "date": "1990:2025", "per_page": 1000}

RAW_DIR     = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CLEANED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CLEANED_DIR, exist_ok=True)


def fetch_indicator(code: str) -> list[dict]:
    """Fetch all pages for one indicator across all SENTINEL countries."""
    url    = BASE_URL.format(countries=ISO2_LIST, indicator=code)
    page   = 1
    pages  = 1
    rows   = []
    while page <= pages:
        r = None
        for attempt in range(5):
            try:
                r = requests.get(url, params={**PARAMS, "page": page}, timeout=90)
                r.raise_for_status()
                break
            except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as exc:
                status = getattr(exc.response, "status_code", None) if hasattr(exc, "response") else None
                if attempt == 4:
                    print(f"    WARNING: failed after 5 attempts for {code} page {page} ({exc}), skipping")
                    return rows
                wait = 5 * (attempt + 1)
                print(f"    retry {attempt+1}/5 for {code} page {page} (status={status}), waiting {wait}s…")
                time.sleep(wait)
        meta, data = r.json()
        pages = meta["pages"]
        rows.extend(data or [])
        page += 1
    return rows


def most_recent_value(rows: list[dict], iso2: str) -> tuple[str | None, float | None]:
    """Return (year, value) for the most recent non-null observation for a country."""
    country_rows = [
        r for r in rows
        if r["country"]["id"].upper() == iso2.upper() and r["value"] is not None
    ]
    if not country_rows:
        return None, None
    best = sorted(country_rows, key=lambda r: r["date"], reverse=True)[0]
    return best["date"], best["value"]


def all_values_for_country(rows: list[dict], iso2: str) -> list[dict]:
    """
    Return a list of {"year": str, "value": float_or_None} for all years in the
    fetched range, sorted ascending by year (1990 first).
    Years present in the API response but with null values are included as None.
    Years absent from the response entirely are omitted (no invented placeholders).
    """
    country_rows = [
        r for r in rows
        if r["country"]["id"].upper() == iso2.upper()
    ]
    # Build year → value mapping; keep None values to represent known-missing years
    year_map: dict[str, float | None] = {}
    for r in country_rows:
        year_map[r["date"]] = r["value"]  # value may be None
    return [{"year": y, "value": year_map[y]} for y in sorted(year_map)]


def main():
    print(f"[{datetime.utcnow().isoformat()}] Fetching World Bank indicators (1990-2025)…")

    # keyed as merged[iso2][col] = value
    merged: dict[str, dict] = {iso2: {"country": name, "iso2": iso2}
                                for iso2, name in COUNTRIES.items()}

    for wb_code, col_name in INDICATORS.items():
        print(f"  Fetching {wb_code} → {col_name} …", end=" ", flush=True)
        rows = fetch_indicator(wb_code)
        non_null = sum(1 for r in rows if r["value"] is not None)
        print(f"{len(rows)} rows ({non_null} non-null)")

        # save raw JSON (full 1990-2025 range)
        raw_path = os.path.join(RAW_DIR, f"wb_{col_name}.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        # merge most-recent value + full series into table
        for iso2 in COUNTRIES:
            year, value = most_recent_value(rows, iso2)
            series = all_values_for_country(rows, iso2)
            merged[iso2][col_name]                   = value
            merged[iso2][f"{col_name}_year"]         = year
            merged[iso2][f"{col_name}_series"]       = series

        time.sleep(0.4)   # be polite to the API

    # ── Write cleaned CSV (latest value per indicator only — no series) ────────
    col_order = (
        ["country", "iso2"]
        + [col for col in [v for v in INDICATORS.values()]
           + [f"{v}_year" for v in INDICATORS.values()]]
    )

    cleaned_path = os.path.join(CLEANED_DIR, "worldbank.csv")
    with open(cleaned_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=col_order, extrasaction="ignore")
        writer.writeheader()
        for iso2 in sorted(COUNTRIES, key=lambda x: COUNTRIES[x]):
            writer.writerow(merged[iso2])

    print(f"  → data/cleaned/worldbank.csv  ({len(COUNTRIES)} countries, latest values only)")

    # ── Write cleaned JSON (includes full series per indicator per country) ────
    cleaned_json_path = os.path.join(CLEANED_DIR, "worldbank.json")
    payload = {
        "updated":    datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date_range": "1990-2025",
        "indicators": list(INDICATORS.values()),
        "countries":  list(merged.values()),
    }
    with open(cleaned_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  → data/cleaned/worldbank.json (includes full series)")
    print(f"  → data/raw/wb_*.json          ({len(INDICATORS)} files, full 1990-2025 range)")
    print("Done.")


if __name__ == "__main__":
    main()
