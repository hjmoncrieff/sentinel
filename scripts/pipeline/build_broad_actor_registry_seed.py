#!/usr/bin/env python3
"""
Build a broader actor-registry seed for non-NSVA actor coverage.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = ROOT / "config" / "actors" / "broad_actor_registry_seed.json"

COUNTRIES = [
    "Argentina", "Belize", "Bolivia", "Brazil", "Chile", "Colombia",
    "Costa Rica", "Cuba", "Dominican Republic", "Ecuador", "El Salvador",
    "Guatemala", "Guyana", "Haiti", "Honduras", "Jamaica", "Mexico",
    "Nicaragua", "Panama", "Paraguay", "Peru", "Suriname",
    "Trinidad and Tobago", "Uruguay", "Venezuela",
]

INTERNATIONAL_ACTORS = [
    ("Organization of American States", "Regional", "non_state_actor", "international_org", "international_org", "multilateral_org", ["OAS"]),
    ("United Nations", "Regional", "non_state_actor", "international_org", "international_org", "multilateral_org", ["UN", "U.N."]),
    ("International Monetary Fund", "Regional", "non_state_actor", "international_org", "international_org", "international_financial_institution", ["IMF"]),
    ("World Bank", "Regional", "non_state_actor", "international_org", "international_org", "international_financial_institution", []),
    ("Inter-American Development Bank", "Regional", "non_state_actor", "international_org", "international_org", "international_financial_institution", ["IDB", "IADB"]),
    ("Inter-American Commission on Human Rights", "Regional", "non_state_actor", "international_org", "international_org", "human_rights_body", ["IACHR"]),
    ("European Union", "Regional", "non_state_actor", "international_org", "international_org", "regional_org", ["EU"]),
    ("CARICOM", "Regional", "non_state_actor", "international_org", "international_org", "regional_org", ["Caribbean Community"]),
    ("MERCOSUR", "Regional", "non_state_actor", "international_org", "international_org", "regional_org", ["Mercosur"]),
    ("CELAC", "Regional", "non_state_actor", "international_org", "international_org", "regional_org", ["Community of Latin American and Caribbean States"]),
    ("United States", "United States", "state_actor", "foreign_government", "foreign_government", "state", ["U.S.", "US", "United States government", "U.S. government"]),
    ("U.S. Southern Command", "United States", "state_actor", "military", "state_security_force", "foreign_military_command", ["SOUTHCOM", "US Southern Command"]),
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "unknown"


def build_actor(country: str, name: str, category: str, group: str, actor_type: str, subtype: str, aliases: list[str], confidence: str = "medium") -> dict:
    return {
        "actor_id": f"broad_{slugify(country)}_{slugify(group)}_{slugify(name)}",
        "canonical_name": name,
        "country": country,
        "actor_category": category,
        "actor_group": group,
        "actor_type": actor_type,
        "subtype": subtype,
        "aliases": aliases,
        "primary_activities": [],
        "source_confidence": confidence,
        "registry_status": "active",
    }


def state_templates(country: str) -> list[dict]:
    return [
        build_actor(country, f"Presidency of {country}", "state_actor", "executive", "state_institution", "executive_office", [f"Government of {country}", f"Executive branch of {country}"], "high"),
        build_actor(country, f"Armed Forces of {country}", "state_actor", "military", "state_security_force", "armed_forces", [f"{country} armed forces", f"{country} military"], "high"),
        build_actor(country, f"National Police of {country}", "state_actor", "police", "state_security_force", "police_force", [f"{country} national police", f"Police of {country}"], "high"),
        build_actor(country, f"Ministry of Defense of {country}", "state_actor", "policy", "state_institution", "defense_ministry", [f"{country} defense ministry", f"{country} ministry of defense"], "high"),
        build_actor(country, f"Ministry of Interior and Public Security of {country}", "state_actor", "policy", "state_institution", "interior_security_ministry", [f"{country} interior ministry", f"{country} public security ministry"]),
        build_actor(country, f"Legislature of {country}", "state_actor", "legislature", "state_institution", "legislature", [f"Congress of {country}", f"National Assembly of {country}", f"Legislative Assembly of {country}"]),
        build_actor(country, f"Judiciary of {country}", "state_actor", "judiciary", "state_institution", "high_court_system", [f"Supreme Court of {country}", f"Constitutional Court of {country}"]),
        build_actor(country, f"Electoral Authority of {country}", "state_actor", "policy", "state_institution", "electoral_authority", [f"Electoral tribunal of {country}", f"National electoral council of {country}"]),
        build_actor(country, f"Public Prosecutor's Office of {country}", "state_actor", "judiciary", "state_institution", "public_prosecutor", [f"Attorney General of {country}", f"Public ministry of {country}", f"Prosecutor General of {country}"]),
    ]


def non_state_templates(country: str) -> list[dict]:
    return [
        build_actor(country, f"Civil Society Organizations of {country}", "non_state_actor", "civil_society", "civic_actor", "civil_society_coalition", [f"{country} civil society organizations", f"{country} civil society"]),
        build_actor(country, f"Business Associations of {country}", "non_state_actor", "economic_group", "economic_actor", "business_association", [f"{country} business associations", f"{country} private sector"]),
        build_actor(country, f"Labor Unions of {country}", "non_state_actor", "civil_society", "civic_actor", "labor_union_movement", [f"{country} labor unions", f"{country} trade unions"]),
        build_actor(country, f"Student Movements of {country}", "non_state_actor", "civil_society", "civic_actor", "student_movement", [f"{country} student movements", f"{country} student organizations"]),
        build_actor(country, f"Independent Media of {country}", "non_state_actor", "media", "media_actor", "independent_media", [f"{country} independent media", f"{country} press"]),
        build_actor(country, f"Protest Movements of {country}", "non_state_actor", "protesters", "civilian_group", "protest_movement", [f"{country} protest movements", f"{country} protesters"]),
    ]


def main() -> None:
    actors = []
    for country in COUNTRIES:
        actors.extend(state_templates(country))
        actors.extend(non_state_templates(country))
    for name, country, category, group, actor_type, subtype, aliases in INTERNATIONAL_ACTORS:
        actors.append(build_actor(country, name, category, group, actor_type, subtype, aliases, "high"))
    actors = sorted(actors, key=lambda item: (item["country"], item["actor_group"], item["canonical_name"]))
    payload = {
        "version": "0.1",
        "updated": datetime.now(UTC).date().isoformat(),
        "status": "seed",
        "source_note": "Broader non-NSVA actor seed for SENTINEL. This layer provides reusable state, civil-society, economic, media, protest, and international actors that complement the NSVA seed.",
        "actors": actors,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"Seed actors: {len(actors)}")


if __name__ == "__main__":
    main()
