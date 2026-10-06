#!/usr/bin/env python3
"""
fetch_us_assistance.py
Pulls US foreign assistance obligations by funding account from ForeignAssistance.gov
and writes data/cleaned/us_assistance.json for the 25 SENTINEL countries.

The Greenbook file (data/cleaned/greenbook.json) ends at fiscal 2019. This series runs
from fiscal 2001 to the current year and is the one to show as current.

Each obligation is put in one of three groups by its funding account:

  military          Foreign Military Financing, IMET, Peacekeeping Operations, Excess
                    Defense Articles, and every Defense Department account (including
                    Defense counter-drug activities).
  counternarcotics  State Department narcotics control and law enforcement (INCLE), the
                    Andean Counterdrug Programs, and anti-terrorism/demining (NADR).
  other             Everything else: economic, development, health, humanitarian.

This is SENTINEL's grouping, not the Greenbook's: the Greenbook counts INCLE as
economic assistance. Amounts are constant US dollars. The newest fiscal years are
incomplete when the file is published; `partial_years` lists them.

The 22 MB source file is downloaded to a temporary file and not kept. No API key.

Usage:
  python3 scripts/structural/fetch_us_assistance.py [--from-file funding.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "cleaned" / "us_assistance.json"
SOURCE_URL = "https://s3.amazonaws.com/files.explorer.devtechlab.com/us_foreign_aid_funding.csv"
FIRST_YEAR = 2001
DEFENSE_AGENCIES = {"DOD", "ARMY", "NAVY", "AF"}
MILITARY_ACCOUNTS = ("foreign military financing", "international military education", "peace keeping operations",
                     "peacekeeping operations", "excess defense articles")
COUNTERNARCOTICS_ACCOUNTS = ("international narcotics control", "andean counterdrug", "nonproliferation, anti-terrorism")
GROUPS = ("military", "counternarcotics", "other")


def group_of(agency: str, account: str) -> str:
    name = (account or "").lower()
    if agency in DEFENSE_AGENCIES or any(key in name for key in MILITARY_ACCOUNTS):
        return "military"
    if any(key in name for key in COUNTERNARCOTICS_ACCOUNTS):
        return "counternarcotics"
    return "other"


def build(rows, countries: list[str], now: datetime) -> dict:
    wanted = set(countries)
    totals: dict[str, dict[int, dict[str, float]]] = {c: {} for c in countries}
    accounts: dict[str, dict[str, float]] = {c: {} for c in countries}
    for row in rows:
        country = row.get("Country Name")
        if country not in wanted or row.get("Transaction Type Name") != "Obligations":
            continue
        try:
            year, amount = int(row["Fiscal Year"]), float(row["constant_amount"] or 0)
        except (TypeError, ValueError):
            continue
        if year < FIRST_YEAR:
            continue
        group = group_of(row.get("Funding Agency Acronym", ""), row.get("Funding Account Name", ""))
        bucket = totals[country].setdefault(year, dict.fromkeys(GROUPS, 0.0))
        bucket[group] += amount
        if group != "other":
            accounts[country][row["Funding Account Name"]] = accounts[country].get(row["Funding Account Name"], 0.0) + amount
    last_year = max((y for years in totals.values() for y in years), default=FIRST_YEAR)
    # The US fiscal year ends on 30 September and reporting lags by months, so the
    # current and the previous fiscal year are incomplete.
    current_fy = now.year + (1 if now.month >= 10 else 0)
    partial = [y for y in range(current_fy - 1, last_year + 1)]
    out = []
    for country in countries:
        series = [{"year": y, **{g: round(totals[country].get(y, {}).get(g, 0.0)) for g in GROUPS}}
                  for y in range(FIRST_YEAR, last_year + 1)]
        for point in series:
            point["total"] = sum(point[g] for g in GROUPS)
        top = sorted(accounts[country].items(), key=lambda kv: -kv[1])[:5]
        out.append({"country": country, "series": series,
                    "top_security_accounts": [{"account": name, "total": round(total)} for name, total in top]})
    return {
        "updated": now.isoformat(timespec="seconds"),
        "source": "ForeignAssistance.gov, obligations by funding account",
        "source_url": SOURCE_URL,
        "note": "Constant US dollars. Grouping by funding account is SENTINEL's (see scripts/structural/fetch_us_assistance.py); "
                "the Greenbook counts narcotics-control funding as economic assistance.",
        "groups": {"military": "Military assistance", "counternarcotics": "Counternarcotics and law enforcement", "other": "Economic and humanitarian"},
        "first_year": FIRST_YEAR,
        "last_year": last_year,
        "partial_years": partial,
        "countries": out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--from-file", type=Path, help="Use a downloaded us_foreign_aid_funding.csv instead of fetching it")
    args = parser.parse_args()
    centroids = json.loads((ROOT / "config" / "taxonomy" / "country_centroids.json").read_text(encoding="utf-8"))["centroids"]
    countries = [c for c in centroids if c != "Regional"]
    with tempfile.TemporaryDirectory() as tmp:
        path = args.from_file
        if path is None:
            path = Path(tmp) / "funding.csv"
            with requests.get(SOURCE_URL, stream=True, timeout=300, headers={"User-Agent": "SENTINEL research monitor"}) as response:
                response.raise_for_status()
                with path.open("wb") as handle:
                    for chunk in response.iter_content(1 << 20):
                        handle.write(chunk)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            payload = build(csv.DictReader(handle), countries, datetime.now(timezone.utc))
    missing = [c["country"] for c in payload["countries"] if not any(p["total"] for p in c["series"])]
    if len(missing) > 5:
        raise SystemExit(f"Too many countries without data ({missing}); the source format may have changed. Nothing written.")
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"countries": len(payload["countries"]), "last_year": payload["last_year"],
                      "partial_years": payload["partial_years"], "without_data": missing}))


if __name__ == "__main__":
    main()
