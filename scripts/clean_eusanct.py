#!/usr/bin/env python3
"""
Clean EUSANCT sanctions panel into SENTINEL-ready country-year outputs.

Inputs:
  data/raw/EUSANCT_CLEAN.dta

Outputs:
  data/cleaned/eusanct.json
  data/cleaned/eusanct.csv
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "EUSANCT_CLEAN.dta"
OUT_JSON = ROOT / "data" / "cleaned" / "eusanct.json"
OUT_CSV = ROOT / "data" / "cleaned" / "eusanct.csv"

COUNTRIES = {
    "Argentina", "Belize", "Bolivia", "Brazil", "Chile", "Colombia",
    "Costa Rica", "Cuba", "Dominican Republic", "Ecuador", "El Salvador",
    "Guatemala", "Guyana", "Haiti", "Honduras", "Jamaica", "Mexico",
    "Nicaragua", "Panama", "Paraguay", "Peru", "Suriname",
    "Trinidad and Tobago", "Uruguay", "Venezuela",
}


def main() -> None:
    df = pd.read_stata(RAW)
    df = df[df["country"].isin(COUNTRIES)].copy()
    df["year"] = df["year"].astype(int)
    numeric_cols = [
        "EU", "US", "UN", "multilateral",
        "econ_eu_sanc", "non_econ_eu_sanc",
        "econ_us_sanc", "non_econ_us_sanc",
        "econ_un_sanc", "non_econ_un_sanc",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    rows = []
    for _, row in df.sort_values(["country", "year"]).iterrows():
        rows.append({
            "country": row["country"],
            "year": int(row["year"]),
            "eu_sanctions_any": int(row["EU"] > 0),
            "us_sanctions_any": int(row["US"] > 0),
            "un_sanctions_any": int(row["UN"] > 0),
            "multilateral_sanctions_any": int(row["multilateral"] > 0),
            "eu_economic_sanctions": int(row["econ_eu_sanc"] > 0),
            "us_economic_sanctions": int(row["econ_us_sanc"] > 0),
            "un_economic_sanctions": int(row["econ_un_sanc"] > 0),
            "sanctions_intensity_score": float(
                row["econ_eu_sanc"] * 22
                + row["non_econ_eu_sanc"] * 10
                + row["econ_us_sanc"] * 28
                + row["non_econ_us_sanc"] * 12
                + row["econ_un_sanc"] * 20
                + row["non_econ_un_sanc"] * 8
            ),
        })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(RAW.relative_to(ROOT)),
        "count": len(rows),
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_JSON}")


if __name__ == "__main__":
    main()
