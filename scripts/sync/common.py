#!/usr/bin/env python3
"""Shared helpers for SENTINEL Supabase sync scripts."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATHS = [ROOT / ".env", ROOT / ".env.local"]
_ENV_LOADED = False


def load_local_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    for path in ENV_PATHS:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def require_env(name: str) -> str:
    load_local_env()
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def supabase_base_url() -> str:
    return require_env("SUPABASE_URL").rstrip("/")


def supabase_service_role_key() -> str:
    return (
        os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or require_env("SUPABASE_SERVICE_ROLE_KEY")
    )


def is_legacy_jwt_key(value: str) -> bool:
    return value.startswith("eyJ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def payload_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def payload_row_count(payload: dict[str, Any]) -> int | None:
    for key in ("items", "flags", "candidates", "events", "countries", "actors"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    for key in ("count", "flag_count", "candidate_count", "issue_count"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return None


def postgrest_request(
    method: str,
    table_or_path: str,
    *,
    payload: list[dict[str, Any]] | dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    prefer: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    path = table_or_path if table_or_path.startswith("/") else f"/rest/v1/{table_or_path}"
    url = supabase_base_url() + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)

    body = None
    api_key = supabase_service_role_key()
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
    }
    if is_legacy_jwt_key(api_key):
        headers["Authorization"] = f"Bearer {api_key}"
    if prefer:
        headers["Prefer"] = prefer
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase request failed ({exc.code}) for {url}: {detail}") from exc


def start_sync_run(sync_type: str, metadata: dict[str, Any] | None = None) -> str | None:
    try:
        rows = postgrest_request(
            "POST",
            "sync_runs",
            payload={
                "sync_type": sync_type,
                "status": "started",
                "started_at": now_iso(),
                "metadata": metadata or {},
            },
            prefer="return=representation",
        )
    except RuntimeError:
        return None
    if isinstance(rows, list) and rows:
        return rows[0].get("sync_run_id")
    return None


def finish_sync_run(
    sync_run_id: str | None,
    *,
    status: str,
    rows_processed: int | None = None,
    error_message: str | None = None,
) -> None:
    if not sync_run_id:
        return
    postgrest_request(
        "PATCH",
        "sync_runs",
        payload={
            "status": status,
            "finished_at": now_iso(),
            "rows_processed": rows_processed,
            "error_message": error_message,
        },
        query={"sync_run_id": f"eq.{sync_run_id}"},
    )


def upsert_console_snapshot(snapshot_key: str, source_path: Path, payload: dict[str, Any]) -> None:
    row = {
        "snapshot_key": snapshot_key,
        "payload": payload,
        "source_path": str(source_path.relative_to(ROOT)),
        "content_hash": payload_hash(payload),
        "rows_count": payload_row_count(payload),
        "generated_at": payload.get("generated_at"),
        "updated_at": now_iso(),
    }
    postgrest_request(
        "POST",
        "console_snapshots",
        payload=[row],
        query={"on_conflict": "snapshot_key"},
        prefer="resolution=merge-duplicates,return=representation",
    )


def fetch_console_snapshots(snapshot_keys: list[str]) -> dict[str, dict[str, Any]]:
    quoted = ",".join(snapshot_keys)
    rows = postgrest_request(
        "GET",
        "console_snapshots",
        query={
            "select": "snapshot_key,payload",
            "snapshot_key": f"in.({quoted})",
        },
    )
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("snapshot_key")): row.get("payload") or {}
        for row in rows
        if row.get("snapshot_key")
    }
