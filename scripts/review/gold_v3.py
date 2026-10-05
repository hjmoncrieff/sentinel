#!/usr/bin/env python3
"""
Codebook v3 gold set and model head-to-head.

  code     Code the gold candidates with each coder (Batch API) → codes_<coder>.jsonl
  compare  Field-level agreement across coders → agreement.json and adjudication.json
           (every disagreement, plus a seeded 10% spot check of full agreements)
  import   Merge the owner's decisions (exported from the review page's db) → gold.jsonl
  score    Score each coder against gold.jsonl → scores.json

Coders: Haiku 4.5 and Sonnet 5.5 are the candidates; Opus 5.5 is a third,
reference coder that helps surface disagreements. Where all three agree, the
value is accepted, and a random 10% of those items is still sent for review so
the agreement error rate can be estimated.

All outputs live in data/gold/v3/ (private).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

GOLD = ROOT / "data" / "gold" / "v3"
CODERS = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}
CANDIDATES = ("haiku", "sonnet")
# Fields compared for agreement and scored against gold. Month-level date is
# compared because day-level dates are often absent from ledes.
FIELDS = ["relevant", "content_type", "type", "subtype", "country", "event_month", "salience", "deed_type", "deed_category", "relationship_signal"]
SPOT_CHECK_SHARE = 0.10


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def candidates_with_ledes() -> list[dict]:
    from enrich_ledes import load_ledes
    rows = load_jsonl(GOLD / "candidates.jsonl")
    run_dir = ROOT / json.loads((GOLD / "sample_summary.json").read_text())["run_dir"]
    ledes = load_ledes(run_dir)
    for a in rows:
        entry = ledes.get(a["article_id"]) or {}
        if entry.get("status") == "ok":
            a["description"] = entry["lede"]
            a["publisher_url"] = entry.get("publisher_url")
        a["lede_status"] = entry.get("status", "not_fetched")
    return rows


def comparable(item: dict | None) -> dict:
    if not item:
        return {f: None for f in FIELDS}
    out = {f: item.get(f) for f in FIELDS if f != "event_month"}
    out["event_month"] = (item.get("event_date") or "")[:7] or None
    if not item.get("relevant"):
        # Nothing else is coded for an irrelevant item.
        out = {f: (out[f] if f in ("relevant", "content_type") else None) for f in FIELDS}
    return out


def cmd_code(args) -> None:
    import anthropic
    from classify_v3 import code
    client = anthropic.Anthropic()
    articles = candidates_with_ledes()
    for name in args.coders:
        coded = code(client, articles, CODERS[name], use_batch=True)
        with (GOLD / f"codes_{name}.jsonl").open("w", encoding="utf-8") as fh:
            for aid, res in coded.items():
                fh.write(json.dumps({"article_id": aid, "coder": name, **res}, ensure_ascii=False) + "\n")
        usage = Counter()
        for res in coded.values():
            for k, v in (res.get("usage") or {}).items():
                if isinstance(v, int):
                    usage[k] += v
        print(name, f"{sum(1 for r in coded.values() if 'item' in r)}/{len(coded)} coded", dict(usage))


def load_codes() -> dict[str, dict[str, dict]]:
    codes = {}
    for name in CODERS:
        path = GOLD / f"codes_{name}.jsonl"
        if path.exists():
            codes[name] = {r["article_id"]: r for r in load_jsonl(path)}
    return codes


def cmd_compare(args) -> None:
    codes = load_codes()
    articles = {a["article_id"]: a for a in candidates_with_ledes()}
    names = list(codes)
    rng = random.Random(29)
    agreement = {f: Counter() for f in FIELDS}
    items = []
    for aid, article in articles.items():
        values = {n: comparable(codes[n].get(aid, {}).get("item")) for n in names}
        disputed = [f for f in FIELDS if len({json.dumps(values[n][f]) for n in names}) > 1]
        for f in FIELDS:
            agreement[f]["agree" if f not in disputed else "disagree"] += 1
        spot = not disputed and rng.random() < SPOT_CHECK_SHARE
        if disputed or spot:
            items.append({
                "article_id": aid,
                "reason": "disagreement" if disputed else "spot_check",
                "disputed": disputed,
                "headline": article.get("title"),
                "source": article.get("source"),
                "published": article.get("date"),
                "url": article.get("publisher_url") or article.get("url"),
                "text": article.get("description") if article.get("lede_status") == "ok" else None,
                "coders": {n: {**values[n],
                               "summary": (codes[n].get(aid, {}).get("item") or {}).get("summary"),
                               "evidence": (codes[n].get(aid, {}).get("item") or {}).get("evidence")} for n in names},
            })
    summary = {f: {"agree": c["agree"], "disagree": c["disagree"],
                   "rate": round(c["agree"] / max(1, c["agree"] + c["disagree"]), 3)} for f, c in agreement.items()}
    (GOLD / "agreement.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    (GOLD / "adjudication.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(f"{sum(1 for i in items if i['reason'] == 'disagreement')} items with disagreements, "
          f"{sum(1 for i in items if i['reason'] == 'spot_check')} spot checks")


def cmd_import(args) -> None:
    """decisions_dir holds the review page's decisions (one JSON per article, from read_db out_dir)."""
    codes = load_codes()
    decisions = {}
    for path in Path(args.decisions_dir).rglob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        body = doc.get("data", doc)
        if body.get("article_id"):
            decisions[body["article_id"]] = body
    names = list(codes)
    articles = candidates_with_ledes()
    written = 0
    with (GOLD / "gold.jsonl").open("w", encoding="utf-8") as fh:
        for a in articles:
            aid = a["article_id"]
            values = {n: comparable(codes[n].get(aid, {}).get("item")) for n in names}
            gold = {}
            for f in FIELDS:
                seen = {json.dumps(values[n][f]) for n in names}
                if aid in decisions and f in (decisions[aid].get("fields") or {}):
                    gold[f] = decisions[aid]["fields"][f]
                elif len(seen) == 1:
                    gold[f] = values[names[0]][f]
                else:
                    gold[f] = "__unresolved__"
            fh.write(json.dumps({"article_id": aid, "gold": gold, "note": (decisions.get(aid) or {}).get("note")}, ensure_ascii=False) + "\n")
            written += 1
    print(f"gold.jsonl: {written} items, {len(decisions)} with owner decisions")


def cmd_score(args) -> None:
    codes = load_codes()
    gold = {r["article_id"]: r["gold"] for r in load_jsonl(GOLD / "gold.jsonl")}
    scores = {}
    for name in codes:
        per = defaultdict(Counter)
        for aid, g in gold.items():
            v = comparable(codes[name].get(aid, {}).get("item"))
            for f in FIELDS:
                if g.get(f) == "__unresolved__":
                    continue
                if f != "relevant" and not g.get("relevant"):
                    continue
                per[f]["correct" if v[f] == g[f] else "wrong"] += 1
        scores[name] = {f: round(c["correct"] / max(1, c["correct"] + c["wrong"]), 3) for f, c in per.items()}
        scores[name]["_n"] = len(gold)
    (GOLD / "scores.json").write_text(json.dumps(scores, indent=1), encoding="utf-8")
    print(json.dumps(scores, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("code")
    c.add_argument("--coders", nargs="+", default=list(CODERS), choices=list(CODERS))
    sub.add_parser("compare")
    i = sub.add_parser("import")
    i.add_argument("decisions_dir")
    sub.add_parser("score")
    args = parser.parse_args()
    {"code": cmd_code, "compare": cmd_compare, "import": cmd_import, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
