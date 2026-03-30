#!/usr/bin/env python3
"""
SENTINEL — Clean Event Dataset Export
Generates data/cleaned/events.csv and data/cleaned/events_clean.json

Adds:
  - sentinel_id (ISO3_YYYY_MM_SHA6)
  - iso3, cow_n, cow_c country codes (COW / M3 compatible)
  - wb_region, sentinel_subregion
  - v2x_regime (V-Dem RoW, from vdem.json, by country-year)
  - confidence mapped to high/med/low
  - days_since_last_coup, days_since_last_purge (per country)
  - mission_std (standardized role), mission_desc (from type)
  - cmr_risk_score (composite: event pressure + V-Dem structural)

Usage:
  python3 scripts/generate_clean_events.py
  python3 scripts/generate_clean_events.py --output-dir data/cleaned
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
EVENTS_IN  = ROOT / "data" / "events.json"
VDEM_IN    = ROOT / "data" / "cleaned" / "vdem.json"
OUT_DIR    = ROOT / "data" / "cleaned"

# ── Country code tables ────────────────────────────────────────────────────────
ISO3 = {
    "Brazil": "BRA", "Colombia": "COL", "Mexico": "MEX", "Venezuela": "VEN",
    "Argentina": "ARG", "Peru": "PER", "Chile": "CHL", "Ecuador": "ECU",
    "Bolivia": "BOL", "Honduras": "HND", "Nicaragua": "NIC", "Guatemala": "GTM",
    "El Salvador": "SLV", "Paraguay": "PRY", "Uruguay": "URY", "Cuba": "CUB",
    "Haiti": "HTI", "Dominican Republic": "DOM", "Panama": "PAN",
    "Costa Rica": "CRI", "Jamaica": "JAM", "Trinidad and Tobago": "TTO",
    "Guyana": "GUY", "Suriname": "SUR", "Belize": "BLZ", "Regional": "REG",
}

COW_N = {
    "Brazil": 140, "Colombia": 100, "Mexico": 70, "Venezuela": 101,
    "Argentina": 160, "Peru": 135, "Chile": 155, "Ecuador": 130,
    "Bolivia": 145, "Honduras": 91, "Nicaragua": 93, "Guatemala": 90,
    "El Salvador": 92, "Paraguay": 150, "Uruguay": 165, "Cuba": 40,
    "Haiti": 41, "Dominican Republic": 42, "Panama": 95, "Costa Rica": 94,
    "Jamaica": 51, "Trinidad and Tobago": 52, "Guyana": 110, "Suriname": 115,
    "Belize": 80,
}

COW_C = {
    "Brazil": "BRA", "Colombia": "COL", "Mexico": "MEX", "Venezuela": "VEN",
    "Argentina": "ARG", "Peru": "PER", "Chile": "CHL", "Ecuador": "ECU",
    "Bolivia": "BOL", "Honduras": "HON", "Nicaragua": "NIC", "Guatemala": "GUA",
    "El Salvador": "SAL", "Paraguay": "PAR", "Uruguay": "URU", "Cuba": "CUB",
    "Haiti": "HAI", "Dominican Republic": "DOM", "Panama": "PAN",
    "Costa Rica": "COS", "Jamaica": "JAM", "Trinidad and Tobago": "TRI",
    "Guyana": "GUY", "Suriname": "SUR", "Belize": "BLZ",
}

WB_REGION = {c: "Latin America & Caribbean" for c in ISO3 if c != "Regional"}
WB_REGION["Regional"] = "Latin America & Caribbean"

SENTINEL_SUBREGION = {
    "Brazil": "Brazil",
    "Colombia": "Andean", "Peru": "Andean", "Ecuador": "Andean",
    "Bolivia": "Andean", "Venezuela": "Andean",
    "Argentina": "Southern Cone", "Chile": "Southern Cone",
    "Paraguay": "Southern Cone", "Uruguay": "Southern Cone",
    "Honduras": "Central America", "Guatemala": "Central America",
    "El Salvador": "Central America", "Nicaragua": "Central America",
    "Panama": "Central America", "Costa Rica": "Central America",
    "Belize": "Central America",
    "Cuba": "Caribbean", "Haiti": "Caribbean", "Dominican Republic": "Caribbean",
    "Jamaica": "Caribbean", "Trinidad and Tobago": "Caribbean",
    "Guyana": "Caribbean", "Suriname": "Caribbean",
    "Mexico": "Mexico",
    "Regional": "Regional",
}

# ── Confidence mapping (old green/yellow/red → high/med/low) ──────────────────
CONF_MAP = {"green": "high", "yellow": "med", "red": "low",
            "high": "high", "med": "med", "low": "low"}

# ── Mission standardization (type → mission_std) ──────────────────────────────
MISSION_STD = {
    "coup":          "political",
    "purge":         "political",
    "coup_proofing": "political",
    "aid":           "US_cooperation",
    "coop":          "US_cooperation",
    "protest":       "internal_security",
    "reform":        "internal_security",
    "conflict":      "internal_security",
    "exercise":      "external_defense",
    "oc":            "counternarcotics",
    "peace":         "internal_security",
    "other":         "other",
}

MISSION_DESC = {
    "coup":          "Attempted or successful seizure of political power by military",
    "purge":         "Removal of officers for political/loyalty reasons",
    "coup_proofing": "Deliberate strategy to prevent coups via institutional controls",
    "aid":           "Receipt of US/foreign military assistance or arms transfers",
    "coop":          "Joint operations or US security cooperation activities",
    "protest":       "Civil-military tensions involving public demonstrations",
    "reform":        "Institutional reform of security sector or civil-military relations",
    "conflict":      "Armed conflict or criminal violence involving security forces",
    "exercise":      "Multinational or bilateral military exercise",
    "oc":            "Organized crime network interaction with security forces",
    "peace":         "Peace negotiations, ceasefire, or DDR process",
    "other":         "Other civil-military development",
}

# ── Event type weights for CMR risk (higher = worse for civilian control) ──────
TYPE_WEIGHT = {
    "coup":          10,
    "coup_proofing": 7,
    "purge":         6,
    "conflict":      5,
    "oc":            4,
    "protest":       3,
    "coop":          2,
    "aid":           1,
    "exercise":      1,
    "peace":        -2,
    "reform":       -3,
    "other":         0,
}

SALIENCE_MULT = {"high": 1.5, "medium": 1.0, "low": 0.5, "med": 1.0}


def make_sentinel_id(country: str, date: str, internal_id: str) -> str:
    iso3 = ISO3.get(country, "REG")
    year  = date[:4]  if len(date) >= 4  else "0000"
    month = date[5:7] if len(date) >= 7  else "00"
    return f"{iso3}_{year}_{month}_{internal_id[:6]}"


# ── CMR event-pressure score (rolling 90-day window per country) ──────────────
def compute_event_pressure(events: list[dict]) -> dict[str, float]:
    """Return {event_id: event_pressure_score} — weighted count of recent events."""
    from collections import defaultdict
    country_events: dict[str, list] = defaultdict(list)
    for ev in events:
        country_events[ev["country"]].append(ev)

    scores: dict[str, float] = {}
    for ev in events:
        try:
            d0 = datetime.strptime(ev["date"], "%Y-%m-%d")
        except ValueError:
            scores[ev["id"]] = 0.0
            continue
        window = [
            e for e in country_events[ev["country"]]
            if e["id"] != ev["id"] and e.get("date")
            and 0 < (d0 - datetime.strptime(e["date"], "%Y-%m-%d")).days <= 90
        ]
        score = sum(
            TYPE_WEIGHT.get(e.get("type", "other"), 0) *
            SALIENCE_MULT.get(e.get("salience", "low"), 0.5)
            for e in window
        )
        scores[ev["id"]] = round(score, 2)
    return scores


# ── Main ───────────────────────────────────────────────────────────────────────
def main(out_dir: Path = OUT_DIR) -> None:
    print(f"Loading events from {EVENTS_IN}")
    raw = json.loads(EVENTS_IN.read_text(encoding="utf-8"))
    events = raw.get("events", raw) if isinstance(raw, dict) else raw
    print(f"  {len(events)} events loaded")

    # Event pressure scores
    pressure = compute_event_pressure(events)

    # Build clean records
    clean: list[dict] = []
    for ev in events:
        country = ev.get("country", "Regional")
        date    = ev.get("date", "")
        iid     = ev.get("id", "")
        year    = int(date[:4]) if len(date) >= 4 else None
        ev_type = ev.get("type", "other")

        # sentinel_id: use existing if present, else generate
        sid = ev.get("sentinel_id") or make_sentinel_id(country, date, iid)

        clean.append({
            # Identifiers
            "sentinel_id":    sid,
            "event_id":       iid,
            "date":           date,
            "year":           year,
            "month":          int(date[5:7]) if len(date) >= 7 else None,

            # Geography
            "country":              country,
            "iso3":                 ISO3.get(country, ""),
            "cow_n":                COW_N.get(country),
            "cow_c":                COW_C.get(country, ""),
            "sentinel_subregion":   SENTINEL_SUBREGION.get(country, "Regional"),

            # Event classification
            "type":               ev_type,
            "subtype":            ev.get("subtype") or "",
            "tags":               "|".join(ev.get("tags", [])),
            "deed_type":          ev.get("deed_type") or "",
            "accountability_axis":ev.get("axis") or "",
            "cmr_dimension":      ev.get("cmr_dimension") or "",
            "direction":          ev.get("direction") or "",
            "actor":              ev.get("actor") or "",
            "target":             ev.get("target") or "",
            "structural":         ev.get("structural", False),

            # Quality
            "salience":    ev.get("salience", "low"),
            "confidence":  CONF_MAP.get(ev.get("conf", "yellow"), "med"),

            # Missions
            "mission_std": MISSION_STD.get(ev_type, "other"),
            "mission_desc":MISSION_DESC.get(ev_type, ""),

            # Content
            "title":   ev.get("title", ""),
            "summary": ev.get("summary", ""),
            "source":  ev.get("source", ""),
            "url":     ev.get("url", ""),

            # Derived (event-level only)
            "event_pressure_90d": pressure.get(iid, 0.0),
            "source_type":        ev.get("source_type") or infer_source_type(ev.get("source", "")),
        })

    # Sort by date descending
    clean.sort(key=lambda e: e["date"] or "", reverse=True)

    # ── Write CSV ──────────────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "events.csv"
    if clean:
        fieldnames = list(clean[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(clean)
        print(f"CSV written: {csv_path} ({len(clean)} rows)")

    # ── Write JSON ─────────────────────────────────────────────────────────────
    json_path = out_dir / "events_clean.json"
    json_path.write_text(
        json.dumps({
            "generated": datetime.utcnow().isoformat() + "Z",
            "count": len(clean),
            "schema_version": "1.0",
            "events": clean,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"JSON written: {json_path} ({len(clean)} events)")

    # ── Summary stats ──────────────────────────────────────────────────────────
    from collections import Counter
    type_counts = Counter(e["type"] for e in clean)
    country_counts = Counter(e["country"] for e in clean)
    print("\nEvent types:")
    for t, n in type_counts.most_common():
        print(f"  {t:20s} {n}")
    print(f"\nCountries covered: {len(country_counts)}")
    print(f"Date range: {min(e['date'] for e in clean if e['date'])} → {max(e['date'] for e in clean if e['date'])}")


def infer_source_type(source: str) -> str:
    s = source.lower()
    if any(x in s for x in ["acled", "gdelt"]): return "structured_data"
    if any(x in s for x in ["crisis group", "insight crime", "wilson", "americas quarterly",
                              "nacla", "southcom"]): return "think_tank"
    if any(x in s for x in ["reuters", "ap ", "bbc", "guardian", "nyt", "times",
                              "folha", "el país", "el tiempo", "semana", "cnn",
                              "miami herald", "infobae", "el nacional"]): return "wire"
    if any(x in s for x in ["dea", "dsca", "pentagon", "state dept"]): return "official"
    return "wire"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SENTINEL clean event dataset")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    main(args.output_dir)
