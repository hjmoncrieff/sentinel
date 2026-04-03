#!/usr/bin/env python3
"""
Clean financial crises workbook into SENTINEL-ready country-year outputs.

Inputs:
  data/raw/FinancialCrises_A new comprehensive database of financial crises Identification, frequency, and duration.xlsx

Outputs:
  data/cleaned/financial_crises.json
  data/cleaned/financial_crises.csv
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "FinancialCrises_A new comprehensive database of financial crises Identification, frequency, and duration.xlsx"
OUT_JSON = ROOT / "data" / "cleaned" / "financial_crises.json"
OUT_CSV = ROOT / "data" / "cleaned" / "financial_crises.csv"

COUNTRIES = {
    "Argentina", "Belize", "Bolivia", "Brazil", "Chile", "Colombia",
    "Costa Rica", "Cuba", "Dominican Republic", "Ecuador", "El Salvador",
    "Guatemala", "Guyana", "Haiti", "Honduras", "Jamaica", "Mexico",
    "Nicaragua", "Panama", "Paraguay", "Peru", "Suriname", "Venezuela, RB",
    "Trinidad and Tobago", "Uruguay",
}

NAME_MAP = {
    "Venezuela, RB": "Venezuela",
}


def main() -> None:
    df = pd.read_excel(RAW, sheet_name="Crisis")
    df = df[df["Country"].isin(COUNTRIES)].copy()
    df["Year"] = df["Year"].astype(int)

    cols = [
        "Banking Crises", "Currency Crises", "Debt Crises",
        "Twin Crises", "Triple Crises", "Twin and Triple crises", "All Crises",
    ]
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    rows = []
    for _, row in df.sort_values(["Country", "Year"]).iterrows():
        country = NAME_MAP.get(row["Country"], row["Country"])
        rows.append({
            "country": country,
            "year": int(row["Year"]),
            "banking_crisis": int(row["Banking Crises"] > 0),
            "currency_crisis": int(row["Currency Crises"] > 0),
            "debt_crisis": int(row["Debt Crises"] > 0),
            "twin_crisis": int(row["Twin Crises"] > 0),
            "triple_crisis": int(row["Triple Crises"] > 0),
            "all_crises": int(row["All Crises"] > 0),
            "crisis_intensity_score": float(
                row["Banking Crises"] * 24
                + row["Currency Crises"] * 28
                + row["Debt Crises"] * 28
                + row["Twin Crises"] * 16
                + row["Triple Crises"] * 24
                + row["Twin and Triple crises"] * 8
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
