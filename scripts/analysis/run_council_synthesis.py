#!/usr/bin/env python3
"""
Upgrade council synthesis to Claude Sonnet for high- and medium-salience events.

Reads  data/review/council_analyses.json (heuristic output from run_council.py)
Writes back to the same file with two new fields per qualifying event:
  analyses.synthesis.public_analysis  → replaced with LLM text (consumed by publish_dashboard_data.py)
  analyses.llm_synthesis              → full tracking block (model, tokens, cache stats, raw output)

Design:
  - Events are grouped by country before calling the API.
  - Each country's system prompt is marked cache_control="ephemeral" so Anthropic
    can reuse it across all events in that country batch within the same 5-minute window.
  - Low-salience events are skipped entirely (no API call).
  - Already-synthesised events (analyses.llm_synthesis present) are skipped on
    incremental runs unless --force is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COUNCIL_PATH = ROOT / "data" / "review" / "council_analyses.json"
COUNTRY_YEAR_PATH = ROOT / "data" / "cleaned" / "country_year.csv"
ANALYST_KNOWLEDGE_PATH = ROOT / "config" / "agents" / "analyst_knowledge.json"

SYNTHESIS_MODEL = "claude-sonnet-4-6"
SYNTHESIS_SALIENCE = {"high", "medium"}
MAX_TOKENS = 600   # one paragraph ~200 tokens; two paragraphs ~400 tokens; JSON overhead ~50
RETRY_SLEEP = 5.0       # seconds between retries on rate-limit
INTER_CALL_SLEEP = 0.3  # polite pause between API calls

# CMR status per country — authoritative text for the system prompt.
# Update after major political changes (see CLAUDE.md maintenance notes).
CMR_STATUS: dict[str, str] = {
    "Argentina": "Strained — civilian control holds but Milei's friction with judiciary creates institutional uncertainty",
    "Belize": "Stable — small professional defence force, civilian control robust",
    "Bolivia": "Strained — post-2019 coup legacy; security sector politically fragmented",
    "Brazil": "Strained — Lula navigating Bolsonaro-era military loyalty risks; 8-Jan accountability ongoing",
    "Chile": "Stable — one of the strongest civilian control records in the region",
    "Colombia": "Strained — peace process tensions; FARC dissident resurgence stresses CMR",
    "Costa Rica": "Stable — no standing military; police under firm civilian control",
    "Cuba": "Authoritarian — civil-military fusion; armed forces integral to regime survival",
    "Dominican Republic": "Stable — civilian control improving; recent professionalization reforms",
    "Ecuador": "Crisis — internal armed conflict framework; military deployed in domestic security",
    "El Salvador": "Crisis — Régimen de Excepción; Bukele model eroding civilian oversight norms",
    "Guatemala": "Strained — military retains significant institutional prerogatives",
    "Guyana": "Stable — civilian control generally robust; oil boom adding resource-security dimension",
    "Haiti": "Crisis — institutional collapse; MSS/gang fragmentation; MNS mission underway",
    "Honduras": "Strained — post-2009 coup legacy; military remains politically influential",
    "Jamaica": "Stable — civilian control solid; episodic states of emergency for OC zones",
    "Mexico": "Strained — SEDENA militarization of civilian functions; López Obrador legacy entrenching military in governance under Sheinbaum",
    "Nicaragua": "Authoritarian — Ortega-Murillo political-military fusion; opposition suppressed",
    "Panama": "Stable — no standing military post-1990; security forces under civilian control",
    "Paraguay": "Strained — military historically influential; EPP guerrilla operations ongoing",
    "Peru": "Strained — rotating executive instability; military navigating constitutional crises",
    "Suriname": "Stable — improving; Bouterse conviction resolved historic civil-military tension",
    "Trinidad and Tobago": "Stable — civilian control solid; OC/gang violence dominant security challenge",
    "Uruguay": "Stable — strongest civilian control record in Southern Cone",
    "Venezuela": "Authoritarian — FANB as regime pillar; military business empire; Chavismo survival mechanism",
}


# ── Country structural context ────────────────────────────────────────────────

def load_country_profiles() -> dict[str, dict]:
    """Load most-recent-year structural indicators from country_year.csv per country."""
    if not COUNTRY_YEAR_PATH.exists():
        return {}
    import csv
    rows_by_country: dict[str, list[dict]] = defaultdict(list)
    with COUNTRY_YEAR_PATH.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            country = row.get("country", "").strip()
            if country:
                rows_by_country[country].append(row)
    profiles: dict[str, dict] = {}
    for country, rows in rows_by_country.items():
        # Take the most recent year that has polyarchy data
        valid = [r for r in rows if r.get("polyarchy") not in (None, "", "nan")]
        if not valid:
            valid = rows
        latest = max(valid, key=lambda r: int(r.get("year") or 0))
        def _f(key: str) -> str:
            v = latest.get(key, "")
            try:
                return f"{float(v):.3f}" if v not in ("", None, "nan") else "n/a"
            except (ValueError, TypeError):
                return str(v) if v else "n/a"
        profiles[country] = {
            "year": latest.get("year", ""),
            "polyarchy": _f("polyarchy"),
            "regime_type": _f("regime_type"),
            "mil_constrain": _f("mil_constrain"),
            "mil_exec": _f("mil_exec"),
            "cs_repress": _f("cs_repress"),
            "political_violence": _f("political_violence"),
            "rule_of_law_vdem": _f("rule_of_law_vdem"),
            "coup_5y": latest.get("coup_attempt_count_5y") or "0",
            "coup_10y": latest.get("coup_attempt_count_10y") or "0",
        }
    return profiles


def load_analyst_knowledge() -> dict:
    if not ANALYST_KNOWLEDGE_PATH.exists():
        return {}
    return json.loads(ANALYST_KNOWLEDGE_PATH.read_text(encoding="utf-8"))


# ── Prompt builders ────────────────────────────────────────────────────────────

_FRAMEWORK_BLOCK = """\
## SENTINEL Analytical Framework

SENTINEL tracks six core civil-military relations (CMR) concepts:
1. Civilian Control — subordination of military to elected civilian authority
2. Coup-Proofing — mechanisms leaders use to prevent coups (counterbalancing units, loyalty promotions, economic integration)
3. Institutional Autonomy — degree to which the officer corps retains policy/budgetary independence from civilian oversight
4. SSR (Security Sector Reform) — external/internal efforts to restructure security forces for democratic accountability
5. Democratic Backsliding — erosion of civilian control norms via executive encroachment (the Bukele model) or entrenched military prerogatives
6. Transnational Security — cartel/OC interactions with state security forces; proxy and collusion relationships

## CMR Status Classifications
- Stable: robust civilian control, no acute tensions
- Strained: friction between civilian and military actors, but within institutional bounds
- Crisis: active breach of civilian control norms (Ecuador internal conflict framework, El Salvador régimen)
- Authoritarian: civil-military fusion; military as pillar of authoritarian regime (Venezuela, Cuba, Nicaragua)

## Relationship Type Glossary
- REL_SUBORDINATE: military complies with civilian direction without visible bargaining
- REL_BARGAINING: civilian leaders and military negotiate informal boundaries
- REL_TUTELARY_VETO: military acts as guardian or veto player without openly seizing power
- REL_PARTISAN_PILLAR: military aligns with a leader or faction as a political pillar
- REL_FRACTURED: military internally divided through mutiny, rival commands, or factionalism
- REL_PRAETORIAN: military has seized or is actively contesting political power
- REL_CORRUPTION_CAPTURE: criminal or predatory capture of security institutions

## Role Domain Glossary
- external_defense: military activity aimed at external threats or sovereign defense
- public_security: military or militarized force used for internal coercion, policing, or domestic enforcement
- governance_tasks: military assigned to administrative, economic, social, or state-capacity functions
- political_influence: military behavior shaping executive survival, leadership outcomes, or regime direction

## OC–State Interaction Type Glossary
- INT_CONFRONTATION: state or military confrontation with criminal or hybrid armed actors
- INT_DEPLOYMENT: domestic deployment of military/security actors for crime control, emergency policing, or border control
- INT_JOINT_OPERATION: coordinated operation involving multiple state agencies (military, police, prosecutors)
- INT_GOVERNANCE_ROLE: military or security actors performing governance or administrative functions
- INT_NEGOTIATION_OR_TRUCE: negotiation, tacit pact, truce, or accommodation between state and criminal actors
- INT_COLLUSION: protection, facilitation, shared rents, or operational coordination between state and criminal actors
- INT_CORRUPTION_CASE: arrest, indictment, sanction, or documented corruption involving security actors linked to crime
- INT_REFUSAL_OR_DEFECTION: refusal, neutrality, mutiny, or defection by military actors in a crisis

## Evidence Tiers
- documented: official legal action, court ruling, sanction, indictment, authoritative audit, or direct state document
- credible: multiple independent reputable outlets or high-quality NGO/academic reporting with sourcing
- alleged: single-source claim, partisan statement, or insufficiently corroborated report

## Interpretive Rules
- Separate role coding from relationship coding: roles describe what the military does; relationships describe how it relates to civilian authority
- Keep public-security roles distinct from governance roles
- Treat hybrid actors and state-linked auxiliaries as analytically distinct from regular armed forces
- Use collusion and corruption-capture labels cautiously; prefer documented evidence
- Preserve uncertainty rather than flattening weak claims into definitive judgements\
"""


def build_country_system_prompt(country: str, profile: dict, knowledge: dict) -> str:
    """Build the cached system prompt for a country batch."""
    cmr_status = CMR_STATUS.get(country, "Unknown — insufficient data")
    p = profile or {}

    structural_block = f"""\
## Country Profile: {country}

CMR Status (SENTINEL assessment): {cmr_status}

Structural indicators (most recent available year: {p.get("year", "n/a")}):
- Polyarchy score (V-Dem, 0–1, higher = more democratic): {p.get("polyarchy", "n/a")}
- Regime type (V-Dem, 0=closed autocracy → 3=liberal democracy): {p.get("regime_type", "n/a")}
- Military constraints on executive (V-Dem mil_constrain, 0–1): {p.get("mil_constrain", "n/a")}
- Military executive index (V-Dem mil_exec, higher = more military in exec): {p.get("mil_exec", "n/a")}
- Civil-society repression (V-Dem cs_repress, higher = more repression): {p.get("cs_repress", "n/a")}
- Political violence index (V-Dem, higher = more violence): {p.get("political_violence", "n/a")}
- Rule of law (V-Dem, 0–1): {p.get("rule_of_law_vdem", "n/a")}
- Coup attempts in past 5 years: {p.get("coup_5y", "0")}
- Coup attempts in past 10 years: {p.get("coup_10y", "0")}\
"""

    role_text = """\
## Your Role

You are the SENTINEL Synthesis Analyst. You receive structured lens assessments (CMR, Political Risk, Security, International, Economic) produced by specialist analysts. Your synthesis should:

1. Integrate the most important signals across all active lenses into a coherent analytical narrative
2. State the core mechanism clearly — what is happening, why it matters, what it could change
3. Be grounded in the specific event: name actors, institutions, and concrete actions where possible
4. Conclude with one specific, actionable watchpoint (what to monitor next)
5. Use direct, plain language suitable for an intelligence brief — no hedges like "it should be noted", no generic theory language
6. Length: determined by salience (specified in the event message)

Respond ONLY with a JSON object in this exact format (no markdown code fences):
{"synthesis": "<paragraph(s)>", "risk_level": "<high|medium|low>", "watchpoint": "<one sentence>"}\
"""

    return "\n\n".join([_FRAMEWORK_BLOCK, structural_block, role_text])


def build_event_user_message(council_entry: dict) -> str:
    """Build the (uncached) per-event user message from the heuristic council record."""
    event_id   = council_entry.get("event_id", "")
    country    = council_entry.get("country", "")
    event_type = council_entry.get("event_type", "")
    salience   = str(council_entry.get("salience") or "medium").lower()
    event_date = council_entry.get("event_date", "")
    length_instruction = (
        "Write 1–2 paragraphs (high-salience event — use two only if the lenses surface genuinely distinct mechanisms)."
        if salience == "high"
        else "Write exactly 1 paragraph."
    )

    ctx = council_entry.get("event_context") or {}
    headline   = ctx.get("primary_headline", "")
    summary    = ctx.get("primary_context", "")
    supporting = ctx.get("supporting_headlines", "")

    analyses   = council_entry.get("analyses") or {}

    # Build lens text block from heuristic analyses (skip synthesis)
    lens_parts: list[str] = []
    LENS_LABELS = {
        "cmr": "Civil-Military Relations Analyst",
        "political_risk": "Political Risk Analyst",
        "regional_security": "Security Analyst",
        "international": "International Analyst",
        "economist": "Economist Analyst",
    }
    for lens_key, label in LENS_LABELS.items():
        lens = analyses.get(lens_key)
        if not lens:
            continue
        assessment = (lens.get("assessment") or "").strip()
        risk       = lens.get("risk_level", "")
        if assessment:
            lens_parts.append(f"**{label}** (risk: {risk})\n{assessment}")

    lens_block = "\n\n".join(lens_parts) if lens_parts else "(no specialist lens analyses available)"

    event_subtype = council_entry.get("event_subcategory") or ""
    deed_type     = (analyses.get("synthesis") or {}).get("deed_type") or ""
    deed_clause   = f" | Deed type: {deed_type}" if deed_type else ""
    sub_clause    = f" | Subtype: {event_subtype}" if event_subtype else ""

    article_block = ""
    if headline:
        article_block += f"Headline: {headline}\n"
    if summary:
        article_block += f"Context: {summary}\n"
    if supporting:
        article_block += f"Additional coverage: {supporting}\n"

    return f"""\
## Event
ID: {event_id}
Country: {country} | Date: {event_date}
Type: {event_type}{sub_clause}{deed_clause}
Salience: {salience}

{article_block.strip()}

## Lens Analyses

{lens_block}

## Task
{length_instruction} Write the synthesis for this event.\
"""


# ── API call ───────────────────────────────────────────────────────────────────

def call_sonnet(
    client: "anthropic.Anthropic",
    system_prompt: str,
    user_message: str,
    country: str,
) -> dict:
    """
    Call Claude Sonnet with the cached country system prompt.
    Returns a dict with synthesis text, risk_level, watchpoint, and token metadata.
    """
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=SYNTHESIS_MODEL,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text = response.content[0].text.strip()

            # Strip accidental markdown code fences
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
            raw_text = re.sub(r"\s*```$", "", raw_text)

            parsed = json.loads(raw_text)
            synthesis_text  = str(parsed.get("synthesis") or "").strip()
            risk_level      = str(parsed.get("risk_level") or "medium").lower()
            watchpoint      = str(parsed.get("watchpoint") or "").strip()
            if risk_level not in {"high", "medium", "low"}:
                risk_level = "medium"

            usage = response.usage
            cache_read    = getattr(usage, "cache_read_input_tokens", 0) or 0
            cache_written = getattr(usage, "cache_creation_input_tokens", 0) or 0

            return {
                "ok": True,
                "synthesis": synthesis_text,
                "risk_level": risk_level,
                "watchpoint": watchpoint,
                "model": SYNTHESIS_MODEL,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_tokens": cache_read,
                "cache_written_tokens": cache_written,
                "cache_hit": cache_read > 0,
                "generated_at": datetime.now(UTC).isoformat(),
            }

        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "error": f"JSON parse error: {exc}",
                "raw": raw_text if "raw_text" in dir() else "",
                "model": SYNTHESIS_MODEL,
                "generated_at": datetime.now(UTC).isoformat(),
            }
        except Exception as exc:
            err_str = str(exc)
            if "rate_limit" in err_str.lower() or "529" in err_str or "overloaded" in err_str.lower():
                wait = RETRY_SLEEP * (attempt + 1)
                print(f"  Rate-limit / overload on attempt {attempt + 1}, waiting {wait}s …")
                time.sleep(wait)
                continue
            return {
                "ok": False,
                "error": err_str,
                "model": SYNTHESIS_MODEL,
                "generated_at": datetime.now(UTC).isoformat(),
            }
    return {
        "ok": False,
        "error": "max retries exceeded",
        "model": SYNTHESIS_MODEL,
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade council synthesis with Claude Sonnet.")
    parser.add_argument("--force", action="store_true", help="Re-generate even if llm_synthesis already present")
    parser.add_argument("--dry-run", action="store_true", help="Print stats but do not call the API or write files")
    parser.add_argument("--country", metavar="NAME", help="Restrict to a single country (for testing)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        raise SystemExit(1)

    if not COUNCIL_PATH.exists():
        print(f"Council analyses not found at {COUNCIL_PATH}. Run run_council.py first.")
        raise SystemExit(1)

    print("Loading council analyses …")
    payload  = json.loads(COUNCIL_PATH.read_text(encoding="utf-8"))
    entries  = payload.get("events", [])
    profiles = load_country_profiles()
    knowledge = load_analyst_knowledge()

    def _needs_synthesis(e: dict) -> bool:
        if args.force:
            return True
        llm = (e.get("analyses") or {}).get("llm_synthesis")
        if not llm:
            return True  # never run
        if not llm.get("ok", True):
            return True  # previous attempt failed — retry automatically
        return False

    # Filter to qualifying events
    candidates = [
        e for e in entries
        if str(e.get("salience") or "").lower() in SYNTHESIS_SALIENCE
        and _needs_synthesis(e)
        and (not args.country or e.get("country") == args.country)
    ]

    total       = len(entries)
    qualifying  = len(candidates)
    skipped_low = sum(1 for e in entries if str(e.get("salience") or "").lower() == "low")
    already_done = sum(
        1 for e in entries
        if str(e.get("salience") or "").lower() in SYNTHESIS_SALIENCE
        and (e.get("analyses") or {}).get("llm_synthesis")
        and not args.force
    )

    print(f"Events total: {total}")
    print(f"  Low-salience (skipped): {skipped_low}")
    print(f"  Already synthesised (skipping unless --force): {already_done}")
    print(f"  Qualifying for Sonnet synthesis: {qualifying}")

    if args.dry_run:
        print("Dry run — exiting without API calls.")
        return

    if not qualifying:
        print("Nothing to synthesise. Exiting.")
        return

    # Group by country to maximise cache hits
    by_country: dict[str, list[dict]] = defaultdict(list)
    for entry in candidates:
        by_country[entry.get("country", "Unknown")].append(entry)

    # Build entry lookup for in-place update
    entry_by_id = {e.get("event_id"): e for e in entries if e.get("event_id")}

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    total_input   = 0
    total_output  = 0
    total_cached  = 0
    total_written = 0
    errors        = 0

    for country, country_entries in sorted(by_country.items()):
        profile       = profiles.get(country, {})
        system_prompt = build_country_system_prompt(country, profile, knowledge)
        print(f"\n{country} ({len(country_entries)} events) …")

        for i, entry in enumerate(country_entries):
            event_id = entry.get("event_id", "?")
            salience = entry.get("salience", "")
            event_date = entry.get("event_date", "")
            print(f"  [{i+1}/{len(country_entries)}] {event_id} ({salience}, {event_date})", end=" ", flush=True)

            user_msg = build_event_user_message(entry)
            result   = call_sonnet(client, system_prompt, user_msg, country)

            if result["ok"]:
                total_input   += result.get("input_tokens", 0)
                total_output  += result.get("output_tokens", 0)
                total_cached  += result.get("cache_read_tokens", 0)
                total_written += result.get("cache_written_tokens", 0)

                cache_flag = "↩cached" if result["cache_hit"] else "↑miss"
                print(f"✓ risk={result['risk_level']} {cache_flag} "
                      f"in={result['input_tokens']} out={result['output_tokens']}")

                # Update the live entry in-place
                live = entry_by_id.get(event_id, entry)
                analyses = live.setdefault("analyses", {})

                # Store full tracking block
                analyses["llm_synthesis"] = {
                    "model": result["model"],
                    "synthesis": result["synthesis"],
                    "risk_level": result["risk_level"],
                    "watchpoint": result["watchpoint"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "cache_read_tokens": result["cache_read_tokens"],
                    "cache_written_tokens": result["cache_written_tokens"],
                    "cache_hit": result["cache_hit"],
                    "generated_at": result["generated_at"],
                }

                # Upgrade synthesis.public_analysis with LLM text
                # (this is what publish_dashboard_data.py reads)
                synthesis_block = analyses.setdefault("synthesis", {})
                if result["synthesis"]:
                    watchpoint_suffix = (
                        f"\n\n**Watch:** {result['watchpoint']}"
                        if result["watchpoint"]
                        else ""
                    )
                    synthesis_block["public_analysis"] = result["synthesis"] + watchpoint_suffix
                    synthesis_block["risk_level"] = result["risk_level"]
                    synthesis_block["llm_upgraded"] = True
                    synthesis_block["llm_model"] = result["model"]

            else:
                errors += 1
                print(f"✗ {result.get('error', 'unknown error')}")
                # Store error block so we can track failures
                live = entry_by_id.get(event_id, entry)
                (live.setdefault("analyses", {}))["llm_synthesis"] = {
                    "model": result["model"],
                    "ok": False,
                    "error": result.get("error"),
                    "generated_at": result["generated_at"],
                }

            if INTER_CALL_SLEEP > 0:
                time.sleep(INTER_CALL_SLEEP)

    # Write augmented file
    payload["llm_synthesis_run"] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": SYNTHESIS_MODEL,
        "events_processed": qualifying,
        "errors": errors,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_read_tokens": total_cached,
        "total_cache_written_tokens": total_written,
    }
    COUNCIL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Wrote {COUNCIL_PATH}")
    print(f"  Processed: {qualifying}  Errors: {errors}")
    print(f"  Tokens — input: {total_input}  output: {total_output}  "
          f"cache_read: {total_cached}  cache_written: {total_written}")


if __name__ == "__main__":
    main()
