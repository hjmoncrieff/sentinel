#!/usr/bin/env python3
"""
Draw the stratified sample for the codebook v3 gold set.

Reads a staged backfill run and its headline gate (_gate.json from
scripts/classify_v3.py gate), and writes data/gold/v3/candidates.jsonl:
about 220 articles the gate kept and 80 it rejected (so the gold set also tests
relevance), spread across countries and sources with per-stratum caps. The draw
is seeded, so it is reproducible.

data/gold/ is private (gitignored).

Usage:
  python3 scripts/review/sample_gold_set.py data/staging/historical/<run> [--relevant 220 --rejected 80 --seed 29]
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

GOLD_DIR = ROOT / "data" / "gold" / "v3"
COUNTRY_CAP = 22
SOURCE_CAP = 30


def stratified(pool: list[dict], n: int, key, cap: int, rng: random.Random) -> list[dict]:
    """Round-robin across strata so small strata are represented, each capped."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for a in pool:
        groups[key(a)].append(a)
    for items in groups.values():
        rng.shuffle(items)
    picked, taken = [], Counter()
    while len(picked) < n and any(groups.values()):
        for k in sorted(groups, key=lambda k: taken[k]):
            if groups[k] and taken[k] < cap and len(picked) < n:
                picked.append(groups[k].pop())
                taken[k] += 1
        if all(not groups[k] or taken[k] >= cap for k in groups):
            break
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--relevant", type=int, default=220)
    parser.add_argument("--rejected", type=int, default=80)
    parser.add_argument("--seed", type=int, default=29)
    args = parser.parse_args()

    from enrich_ledes import gated_articles
    rng = random.Random(args.seed)
    gate = json.loads((args.run_dir / "_gate.json").read_text(encoding="utf-8"))
    articles = [a for a in gated_articles(args.run_dir) if a.get("article_id") in gate]
    kept = [a for a in articles if gate[a["article_id"]]["relevant"]]
    rejected = [a for a in articles if not gate[a["article_id"]]["relevant"]]

    # Kept: balance countries first (the gate's country guess), then cap sources.
    by_country = stratified(kept, args.relevant * 2, lambda a: gate[a["article_id"]].get("country") or "none", COUNTRY_CAP, rng)
    sample_kept = stratified(by_country, args.relevant, lambda a: a.get("source") or "?", SOURCE_CAP, rng)
    sample_rej = stratified(rejected, args.rejected, lambda a: a.get("source") or "?", SOURCE_CAP, rng)

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    out = GOLD_DIR / "candidates.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for a in sample_kept + sample_rej:
            fh.write(json.dumps({**a, "gate": gate[a["article_id"]]}, ensure_ascii=False) + "\n")
    summary = {
        "run_dir": str(args.run_dir.resolve().relative_to(ROOT)), "seed": args.seed,
        "kept_pool": len(kept), "rejected_pool": len(rejected),
        "sampled_kept": len(sample_kept), "sampled_rejected": len(sample_rej),
        "by_country": Counter(gate[a["article_id"]].get("country") or "none" for a in sample_kept).most_common(),
        "by_source": Counter(a.get("source") for a in sample_kept + sample_rej).most_common(),
    }
    (GOLD_DIR / "sample_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("kept_pool", "rejected_pool", "sampled_kept", "sampled_rejected")}))
    print("countries:", summary["by_country"])


if __name__ == "__main__":
    main()
