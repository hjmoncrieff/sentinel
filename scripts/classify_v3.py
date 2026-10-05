#!/usr/bin/env python3
"""
Codebook v3 classifier (two passes).

Pass 1, gate: headline-only relevance screen, 25 items per request.
Pass 2, code: one article per request, with the rendered codebook as a cached
system prompt and a structured-output schema from scripts/codebook.py.

Model-specific request settings live in MODEL_PARAMS so the same code runs the
Haiku 4.5 vs Sonnet 5.5 head-to-head. Large runs go through the Message Batches
API (half price); small checks can run synchronously.

Usage:
  python3 scripts/classify_v3.py gate <run_dir>                 # writes <run_dir>/_gate.json
  python3 scripts/classify_v3.py code <articles.jsonl> --model claude-sonnet-5-5 --out <codes.jsonl> [--batch]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import codebook  # noqa: E402
from prompt_library import render_prompt  # noqa: E402

log = logging.getLogger("classify_v3")

GATE_MODEL = "claude-haiku-4-5-20251001"
GATE_BATCH = 25
LEDE_CHARS = 1200

# Request settings per model. Haiku 4.5 still honours temperature (sent through
# extra_body under SDK 1.x); Sonnet 5.5 and Opus 5.5 reject sampling parameters.
# Sonnet 5.5 turns extended thinking off with "between_tools"; Opus 5.5 always
# thinks, so it runs at low effort.
MODEL_PARAMS: dict[str, dict] = {
    "claude-haiku-4-5-20251001": {"max_tokens": 2000, "body": {"temperature": 0}},
    "claude-sonnet-5-5": {"max_tokens": 2000, "body": {"thinking": {"type": "between_tools"}}},
    "claude-opus-5-5": {"max_tokens": 8000, "body": {}, "effort": "low"},
}


def gate_schema() -> dict:
    item = {
        "type": "object",
        "properties": {
            "idx": {"type": "integer"},
            "relevant": {"type": "boolean"},
            "content_type": {"type": "string", "enum": codebook.CONTENT_TYPES},
            "country": {"anyOf": [{"type": "string", "enum": codebook.countries()}, {"type": "null"}]},
        },
        "required": ["idx", "relevant", "content_type", "country"],
        "additionalProperties": False,
    }
    return {"type": "object", "properties": {"items": {"type": "array", "items": item}},
            "required": ["items"], "additionalProperties": False}


def _output_config(schema: dict, model: str) -> dict:
    cfg: dict = {"format": {"type": "json_schema", "schema": schema}}
    if MODEL_PARAMS[model].get("effort"):
        cfg["effort"] = MODEL_PARAMS[model]["effort"]
    return cfg


def _text(message) -> str:
    return next(b.text for b in message.content if b.type == "text")


def article_text(article: dict) -> str:
    text = (article.get("description") or "").strip()
    if not text or text.lower().startswith((article.get("title") or "").lower()[:50]):
        return "(headline only; no article text available)"
    return text[:LEDE_CHARS]


def code_request(article: dict, model: str) -> dict:
    """Request body for coding one article (usable for messages.create or a batch)."""
    system = render_prompt("code_event_v3_system", codebook=codebook.render_definitions())
    user = render_prompt(
        "code_event_v3",
        source=article.get("source") or "unknown",
        published=article.get("date") or "unknown",
        headline=article.get("title") or "",
        text=article_text(article),
    )
    return {
        "model": model,
        "max_tokens": MODEL_PARAMS[model]["max_tokens"],
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user}],
        "output_config": _output_config(codebook.item_schema(), model),
        **MODEL_PARAMS[model]["body"],
    }


def gate_request(batch: list[dict], model: str = GATE_MODEL) -> dict:
    lines = [f"[{i}] ({a.get('source')}, {a.get('date')}) {a.get('title')}" for i, a in enumerate(batch)]
    return {
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": render_prompt("relevance_gate", items="\n".join(lines))}],
        "output_config": _output_config(gate_schema(), model),
        **MODEL_PARAMS[model]["body"],
    }


def _sync_kwargs(body: dict) -> dict:
    """Split raw-body fields the typed SDK call does not accept into extra_body."""
    typed = {"model", "max_tokens", "system", "messages", "output_config", "thinking"}
    kwargs = {k: v for k, v in body.items() if k in typed}
    extra = {k: v for k, v in body.items() if k not in typed}
    if extra:
        kwargs["extra_body"] = extra
    return kwargs


def call_sync(client, body: dict) -> dict:
    message = client.messages.create(**_sync_kwargs(body))
    if message.stop_reason == "refusal":
        raise RuntimeError("model refused")
    return {"parsed": json.loads(_text(message)), "usage": message.usage.model_dump()}


def run_batch(client, bodies: dict[str, dict], poll: int = 30) -> dict[str, dict]:
    """Submit {custom_id: body} to the Message Batches API and wait for results."""
    batch = client.messages.batches.create(requests=[{"custom_id": cid, "params": body} for cid, body in bodies.items()])
    log.info(f"Batch {batch.id}: {len(bodies)} requests submitted")
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        log.info(f"  {batch.processing_status}: {batch.request_counts.processing} processing, {batch.request_counts.succeeded} done")
        time.sleep(poll)
    out: dict[str, dict] = {}
    for result in client.messages.batches.results(batch.id):
        if result.result.type == "succeeded":
            msg = result.result.message
            try:
                out[result.custom_id] = {"parsed": json.loads(_text(msg)), "usage": msg.usage.model_dump(), "stop": msg.stop_reason}
            except (StopIteration, json.JSONDecodeError) as exc:
                out[result.custom_id] = {"error": f"unparseable: {exc}", "stop": msg.stop_reason}
        else:
            out[result.custom_id] = {"error": result.result.type}
    log.info(f"Batch {batch.id} ended: {sum(1 for v in out.values() if 'parsed' in v)}/{len(bodies)} parsed")
    return out


def gate(client, articles: list[dict], use_batch: bool = True, model: str = GATE_MODEL) -> dict[str, dict]:
    """Headline relevance for every article; returns {article_id: {relevant, content_type, country}}."""
    chunks = [articles[i:i + GATE_BATCH] for i in range(0, len(articles), GATE_BATCH)]
    bodies = {f"gate-{n}": gate_request(chunk, model) for n, chunk in enumerate(chunks)}
    results = run_batch(client, bodies) if use_batch else {cid: call_sync(client, b) for cid, b in bodies.items()}
    decisions: dict[str, dict] = {}
    for n, chunk in enumerate(chunks):
        items = {it["idx"]: it for it in (results.get(f"gate-{n}", {}).get("parsed") or {}).get("items", [])}
        for i, article in enumerate(chunk):
            it = items.get(i)
            decisions[article["article_id"]] = (
                {"relevant": it["relevant"], "content_type": it["content_type"], "country": it["country"]}
                if it else {"relevant": True, "content_type": "event", "country": None, "gate_error": True}
            )
    return decisions


def run_concurrent(client, bodies: dict[str, dict], workers: int = 4) -> dict[str, dict]:
    """Direct calls, a few at a time. Every request after the first reads the cached
    codebook, which on 2026-09-30 cost less per article than the Batch API, whose
    caching inside a batch is best-effort."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out: dict[str, dict] = {}
    items = list(bodies.items())
    if items:  # warm the cache with one request before fanning out
        cid, body = items[0]
        out[cid] = _safe_call(client, body)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_safe_call, client, body): cid for cid, body in items[1:]}
        for n, fut in enumerate(as_completed(futures), 1):
            out[futures[fut]] = fut.result()
            if n % 100 == 0:
                log.info(f"  {n}/{len(items) - 1} coded")
    return out


def _safe_call(client, body: dict, attempts: int = 3) -> dict:
    for attempt in range(attempts):
        try:
            return call_sync(client, body)
        except Exception as exc:  # rate limits and transient errors: back off, then record
            if attempt == attempts - 1:
                return {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            time.sleep(10 * (attempt + 1))
    return {"error": "unreachable"}


def code(client, articles: list[dict], model: str, use_batch: bool = True, workers: int = 4) -> dict[str, dict]:
    bodies = {a["article_id"]: code_request(a, model) for a in articles}
    results = run_batch(client, bodies) if use_batch else run_concurrent(client, bodies, workers)
    coded = {}
    for aid, res in results.items():
        if "parsed" in res:
            item = codebook.normalize(res["parsed"])
            coded[aid] = {"item": item, "problems": codebook.validate(item), "usage": res.get("usage")}
        else:
            coded[aid] = {"error": res.get("error")}
    return coded


def _client():
    import anthropic
    return anthropic.Anthropic()


def main() -> None:
    parser = argparse.ArgumentParser(description="Codebook v3 classifier")
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("run_dir", type=Path)
    g.add_argument("--model", default=GATE_MODEL, choices=sorted(MODEL_PARAMS))
    g.add_argument("--recheck-rejected", action="store_true",
                   help="Re-screen only the articles an earlier gate rejected, and merge (relevant if either pass kept it)")
    c = sub.add_parser("code")
    c.add_argument("articles", type=Path)
    c.add_argument("--model", required=True, choices=sorted(MODEL_PARAMS))
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--batch", action="store_true")
    c.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = _client()
    if args.cmd == "gate":
        from enrich_ledes import gated_articles
        articles = gated_articles(args.run_dir)
        path = args.run_dir / "_gate.json"
        previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if args.recheck_rejected:
            articles = [a for a in articles if a["article_id"] in previous and not previous[a["article_id"]]["relevant"]]
        decisions = gate(client, articles, model=args.model)
        recovered = 0
        for aid, d in decisions.items():
            d["gate_model"] = args.model
            if args.recheck_rejected and d["relevant"]:
                recovered += 1
            if not args.recheck_rejected or d["relevant"]:
                previous[aid] = d
        path.write_text(json.dumps(previous, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info(f"Gate ({args.model}): {sum(1 for d in decisions.values() if d['relevant'])}/{len(decisions)} relevant"
                 + (f"; {recovered} recovered from the earlier rejections" if args.recheck_rejected else "")
                 + f"; {sum(1 for d in previous.values() if d['relevant'])} relevant in total")
    else:
        articles = [json.loads(line) for line in args.articles.read_text(encoding="utf-8").splitlines() if line.strip()]
        coded = code(client, articles, args.model, use_batch=args.batch, workers=args.workers)
        with args.out.open("w", encoding="utf-8") as fh:
            for aid, res in coded.items():
                fh.write(json.dumps({"article_id": aid, "model": args.model, **res}, ensure_ascii=False) + "\n")
        log.info(f"Coded {len(coded)} articles with {args.model} → {args.out}")


if __name__ == "__main__":
    main()
