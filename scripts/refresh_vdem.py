#!/usr/bin/env python3
"""
Refresh SENTINEL's cleaned V-Dem layer using a Python entry point.

This runner uses the locally installed R `vdemdata` package as a data source,
but the orchestration, normalization, and output generation all happen through
this Python script so it can fit naturally into the existing pipeline.

Outputs:
  data/cleaned/vdem.json
  data/cleaned/vdem.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "cleaned"
OUT_JSON = OUT_DIR / "vdem.json"
OUT_CSV = OUT_DIR / "vdem.csv"

YEAR_MIN = 1960

COUNTRY_MAP: dict[str, str] = {
    "Argentina": "Argentina",
    "Belize": "Belize",
    "Bolivia": "Bolivia",
    "Brazil": "Brazil",
    "Chile": "Chile",
    "Colombia": "Colombia",
    "Costa Rica": "Costa Rica",
    "Cuba": "Cuba",
    "Dominican Republic": "Dominican Republic",
    "Ecuador": "Ecuador",
    "El Salvador": "El Salvador",
    "Guatemala": "Guatemala",
    "Guyana": "Guyana",
    "Haiti": "Haiti",
    "Honduras": "Honduras",
    "Jamaica": "Jamaica",
    "Mexico": "Mexico",
    "Nicaragua": "Nicaragua",
    "Panama": "Panama",
    "Paraguay": "Paraguay",
    "Peru": "Peru",
    "Suriname": "Suriname",
    "Trinidad and Tobago": "Trinidad and Tobago",
    "Uruguay": "Uruguay",
    "Venezuela": "Venezuela",
}

SOURCE_COLUMNS: dict[str, tuple[str, str]] = {
    "polyarchy": ("v2x_polyarchy", "Electoral democracy index"),
    "liberal_democracy": ("v2x_libdem", "Liberal democracy index"),
    "participatory_democracy": ("v2x_partipdem", "Participatory democracy index"),
    "deliberative_democracy": ("v2x_delibdem", "Deliberative democracy index"),
    "egalitarian_democracy": ("v2x_egaldem", "Egalitarian democracy index"),
    "regime_type": ("v2x_regime", "Regime type"),
    "physinteg": ("v2x_clphy", "Physical integrity index"),
    "mil_constrain": ("v2stcritapparm", "Military constraints on the executive"),
    "mil_exec": ("v2x_ex_military", "Executive military profile"),
    "exec_confidence": ("v2x_ex_confidence", "Executive confidence"),
    "judicial_constraints": ("v2x_jucon", "Judicial constraints on the executive"),
    "legislative_constraints": ("v2xlg_legcon", "Legislative constraints on the executive"),
    "rule_of_law_vdem": ("v2x_rule", "Rule of law index"),
    "public_sector_corruption": ("v2x_pubcorr", "Public-sector corruption index"),
    "executive_corruption": ("v2x_execorr", "Executive corruption index"),
    "corruption_index": ("v2x_corr", "Overall corruption index"),
    "clientelism": ("v2xnp_client", "Clientelism/programmatic politics"),
    "civil_society_participation": ("v2xcs_ccsi", "Civil society participation"),
    "party_institutionalization": ("v2xps_party", "Party institutionalization"),
    "state_authority": ("v2castate", "State authority over territory"),
    "coup_total_events": ("e_coups", "Total coup events"),
    "coup_event": ("e_pt_coup", "Coup event"),
    "coup_attempts": ("e_pt_coup_attempts", "Coup attempts"),
    "executive_direct_election": ("v2x_ex_direlect", "Chief executive directly elected"),
    "election_repression": ("v3eldirepr", "Election-related repression"),
    "voter_turnout": ("v3ttlvote", "Voter turnout"),
    "democracy_breakdown": ("e_democracy_breakdowns", "Democracy breakdown event"),
    "democracy_transition": ("e_democracy_trans", "Democracy transition event"),
    "polity2": ("e_polity2", "Polity2"),
    "cs_repress": ("v2csreprss", "Civil society repression"),
    "political_violence": ("v2caviol", "Political violence"),
}

SERIES_KEYS = list(SOURCE_COLUMNS.keys())
INT_KEYS = {
    "coup_total_events",
    "coup_event",
    "coup_attempts",
    "democracy_breakdown",
    "democracy_transition",
    "polity2",
}


@dataclass
class VDemRecord:
    country: str
    year: int
    values: dict[str, int | float | None]


def safe_number(raw: str | None, key: str) -> int | float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"na", "nan", "null", "none"}:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if key in INT_KEYS:
        return int(round(value))
    return round(value, 6)


def extract_vdem_rows() -> list[VDemRecord]:
    keep_cols = ["country_name", "year"] + [source for source, _label in SOURCE_COLUMNS.values()]
    keep_r = ", ".join(f'"{column}"' for column in keep_cols)
    countries_r = ", ".join(f'"{country}"' for country in COUNTRY_MAP.values())
    code = f"""
suppressPackageStartupMessages(library(vdemdata))
keep <- c({keep_r})
present <- intersect(keep, names(vdem))
d <- vdem[, present, drop = FALSE]
d <- d[d$country_name %in% c({countries_r}) & d$year >= {YEAR_MIN}, , drop = FALSE]
write.csv(d, stdout(), row.names = FALSE, na = "")
"""
    result = subprocess.run(
        ["Rscript", "-e", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    rows: list[VDemRecord] = []
    reverse = {source: output for output, (source, _label) in SOURCE_COLUMNS.items()}
    for row in reader:
        country = str(row.get("country_name") or "").strip()
        if country not in COUNTRY_MAP.values():
            continue
        try:
            year = int(float(row.get("year") or 0))
        except (TypeError, ValueError):
            continue
        values = {
            reverse[source]: safe_number(row.get(source), reverse[source])
            for source in reverse
            if source in row
        }
        rows.append(VDemRecord(country=country, year=year, values=values))
    return rows


def build_country_payload(rows: list[VDemRecord]) -> dict:
    per_country: dict[str, dict[int, dict[str, int | float | None]]] = {}
    for record in rows:
        per_country.setdefault(record.country, {})[record.year] = record.values

    years = sorted({record.year for record in rows})
    countries_out = []
    flat_rows = []

    for sentinel_name, vdem_name in sorted(COUNTRY_MAP.items()):
        country_rows = per_country.get(vdem_name, {})
        if not country_rows:
            continue
        latest_year = max(country_rows)
        snapshot: dict[str, int | float | None] = {}
        for key in SOURCE_COLUMNS:
            latest_value = None
            for year in sorted(country_rows.keys(), reverse=True):
                candidate = country_rows[year].get(key)
                if candidate is not None:
                    latest_value = candidate
                    break
            snapshot[key] = latest_value

        series = {
            key: [
                {"year": year, "value": country_rows.get(year, {}).get(key)}
                for year in years
            ]
            for key in SERIES_KEYS
        }

        countries_out.append({
            "country": sentinel_name,
            "latest_year": latest_year,
            **snapshot,
            "series": series,
        })

        for year in sorted(country_rows):
            flat_rows.append({
                "country": sentinel_name,
                "year": year,
                **country_rows[year],
            })

    return {
        "updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "V-Dem Country-Year data via local R vdemdata package",
        "years": years,
        "columns": {output: label for output, (_source, label) in SOURCE_COLUMNS.items()},
        "countries": countries_out,
        "rows": flat_rows,
    }


def write_outputs(payload: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    flat_rows = payload.get("rows", [])
    if flat_rows:
        with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0].keys()))
            writer.writeheader()
            writer.writerows(flat_rows)


def main(output_dir: Path = OUT_DIR) -> None:
    rows = extract_vdem_rows()
    if not rows:
        raise RuntimeError("No V-Dem rows were extracted.")
    payload = build_country_payload(rows)
    write_outputs(payload, output_dir)
    print(f"Wrote cleaned V-Dem JSON to {OUT_JSON}")
    print(f"Wrote cleaned V-Dem CSV to {OUT_CSV}")
    print(f"Countries written: {len(payload.get('countries', []))}")
    print(f"Year rows written: {len(payload.get('rows', []))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh the cleaned V-Dem layer through a Python runner")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    main(args.output_dir)
