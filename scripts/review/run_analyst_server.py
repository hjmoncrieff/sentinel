#!/usr/bin/env python3
"""
Run a lightweight local analyst server with authenticated edit persistence.

Features:
- serves the repo as static files
- exposes authenticated API endpoints for analyst-console login/session/edit actions
- writes directly to data/review/edits.local.json
- writes controlled registry changes to data/review/registry_edits.local.json
- refreshes review-layer edited outputs after each save
"""

from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
import sys
import argparse
from datetime import UTC, datetime
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
USERS_PATH = ROOT / "data" / "review" / "users.local.json"
EDITS_PATH = ROOT / "data" / "review" / "edits.local.json"
APPLY_SCRIPT = ROOT / "scripts" / "review" / "apply_analyst_edits.py"
REGISTRY_EDITS_PATH = ROOT / "data" / "review" / "registry_edits.local.json"
REGISTRY_APPLY_SCRIPT = ROOT / "scripts" / "review" / "apply_registry_edits.py"
SESSION_COOKIE = "sentinel_session"

SESSIONS: dict[str, dict[str, str]] = {}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_users() -> dict[str, dict[str, Any]]:
    payload = load_json(USERS_PATH)
    return {user["username"]: user for user in payload.get("users", [])}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_local_runtime_files() -> None:
    missing = []
    if not USERS_PATH.exists():
        missing.append(str(USERS_PATH.relative_to(ROOT)))
    if not EDITS_PATH.exists():
        missing.append(str(EDITS_PATH.relative_to(ROOT)))
    if not REGISTRY_EDITS_PATH.exists():
        missing.append(str(REGISTRY_EDITS_PATH.relative_to(ROOT)))
    if missing:
        raise FileNotFoundError(
            "Missing local analyst files: "
            + ", ".join(missing)
            + ". Copy the matching *.template.json files first."
        )

    users_payload = load_json(USERS_PATH)
    placeholder_users = [
        user.get("username", "unknown")
        for user in users_payload.get("users", [])
        if user.get("password_sha256") in {"replace_me", "", None}
    ]
    if placeholder_users:
        raise ValueError(
            "Refusing to start with placeholder password hashes for: "
            + ", ".join(placeholder_users)
            + ". Replace them in data/review/users.local.json first."
        )


def run_apply_step() -> None:
    subprocess.run([sys.executable, str(APPLY_SCRIPT)], cwd=ROOT, check=True)


def run_registry_apply_step() -> None:
    subprocess.run([sys.executable, str(REGISTRY_APPLY_SCRIPT)], cwd=ROOT, check=True)


def role_can_edit(role_rules: dict[str, Any], field_path: str) -> bool:
    editable_fields = role_rules.get("editable_fields", [])
    return "*" in editable_fields or field_path in editable_fields


def role_can_set_status(role_rules: dict[str, Any], value: str | None) -> bool:
    if value is None:
        return True
    return value in role_rules.get("allowed_review_statuses", [])


def validate_edit_against_clearance(edit: dict[str, Any], edits_payload: dict[str, Any]) -> tuple[bool, list[str]]:
    role = edit.get("editor_role", "ra")
    roles = edits_payload.get("clearance_model", {}).get("roles", {})
    role_rules = roles.get(role, roles.get("ra", {}))
    warnings: list[str] = []

    for field in (edit.get("patch") or {}).keys():
        if not role_can_edit(role_rules, field):
            warnings.append(f"Role {role} cannot edit {field}.")
        if field == "review_status" and not role_can_set_status(role_rules, (edit.get("patch") or {}).get(field)):
            warnings.append(f"Role {role} cannot set review_status to {(edit.get('patch') or {}).get(field)}.")

    for actor_patch in edit.get("actor_patches", []) or []:
        action = actor_patch.get("action", "update")
        if action == "create" and not role_can_edit(role_rules, "actors.create"):
            warnings.append(f"Role {role} cannot create actors.")
        if action == "remove" and not role_can_edit(role_rules, "actors.remove"):
            warnings.append(f"Role {role} cannot remove actors.")
        for field in (actor_patch.get("patch") or {}).keys():
            field_path = f"actors.{field}"
            if not role_can_edit(role_rules, field_path):
                warnings.append(f"Role {role} cannot edit {field_path}.")

    return (len(warnings) == 0), warnings


def ensure_payload_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("schema_version", "1.0")
    payload.setdefault("updated_at", None)
    payload.setdefault("clearance_model", {})
    payload.setdefault("edits", [])
    payload.setdefault("qa_resolutions", [])
    payload.setdefault("duplicate_resolutions", [])
    return payload


def ensure_registry_payload_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("schema_version", "1.0")
    payload.setdefault("updated_at", None)
    payload.setdefault("edits", [])
    return payload


def normalize_actor_patch(actor_patch: dict[str, Any]) -> dict[str, Any]:
    patch = dict(actor_patch.get("patch") or {})
    for key in ("actor_aliases", "actor_relationship_tags"):
        value = patch.get(key)
        if isinstance(value, str):
            patch[key] = [part.strip() for part in value.split(",") if part.strip()]
    if "actor_uncertain" in patch:
        patch["actor_uncertain"] = bool(patch["actor_uncertain"])
    return {**actor_patch, "patch": patch}


class AnalystHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/session":
            self.handle_session()
            return
        if parsed.path == "/api/edits":
            self.handle_get_edits()
            return
        if parsed.path == "/api/qa-resolutions":
            self.handle_get_qa_resolutions()
            return
        if parsed.path == "/api/duplicate-resolutions":
            self.handle_get_duplicate_resolutions()
            return
        if parsed.path == "/api/registry-edits":
            self.handle_get_registry_edits()
            return
        if parsed.path in {
            "/data/review/users.local.json",
            "/data/review/edits.local.json",
            "/data/review/registry_edits.local.json",
            "/data/review/users.template.json"
        }:
            self.send_error(HTTPStatus.FORBIDDEN, "Use the API for this resource.")
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/login":
            self.handle_login()
            return
        if parsed.path == "/api/logout":
            self.handle_logout()
            return
        if parsed.path == "/api/edits":
            self.handle_save_edit()
            return
        if parsed.path == "/api/qa-resolution":
            self.handle_save_qa_resolution()
            return
        if parsed.path == "/api/undo-qa-resolution":
            self.handle_undo_qa_resolution()
            return
        if parsed.path == "/api/duplicate-resolution":
            self.handle_save_duplicate_resolution()
            return
        if parsed.path == "/api/undo-duplicate-resolution":
            self.handle_undo_duplicate_resolution()
            return
        if parsed.path == "/api/registry-edits":
            self.handle_save_registry_edit()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint.")

    def parse_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def send_json(self, payload: dict[str, Any], status: int = 200, cookie: str | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def get_session(self) -> dict[str, str] | None:
        raw_cookie = self.headers.get("Cookie")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        morsel = cookie.get(SESSION_COOKIE)
        if not morsel:
            return None
        return SESSIONS.get(morsel.value)

    def require_session(self) -> dict[str, str] | None:
        session = self.get_session()
        if not session:
            self.send_json({"ok": False, "error": "authentication_required"}, status=401)
            return None
        return session

    def handle_session(self) -> None:
        session = self.get_session()
        if not session:
            self.send_json({"authenticated": False, "user": None})
            return
        self.send_json({"authenticated": True, "user": session})

    def handle_login(self) -> None:
        body = self.parse_json_body()
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        users = load_users()
        user = users.get(username)
        if not user or user.get("password_sha256") != hash_password(password):
            self.send_json({"ok": False, "error": "invalid_credentials"}, status=401)
            return
        token = secrets.token_urlsafe(24)
        session = {
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
            "role": user["role"],
        }
        SESSIONS[token] = session
        cookie = f"{SESSION_COOKIE}={token}; HttpOnly; Path=/; SameSite=Lax"
        self.send_json({"ok": True, "user": session}, cookie=cookie)

    def handle_logout(self) -> None:
        raw_cookie = self.headers.get("Cookie")
        if raw_cookie:
            cookie = SimpleCookie()
            cookie.load(raw_cookie)
            morsel = cookie.get(SESSION_COOKIE)
            if morsel and morsel.value in SESSIONS:
                SESSIONS.pop(morsel.value, None)
        self.send_json({"ok": True}, cookie=f"{SESSION_COOKIE}=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax")

    def handle_get_edits(self) -> None:
        if not self.require_session():
            return
        payload = ensure_payload_defaults(load_json(EDITS_PATH))
        self.send_json(payload)

    def handle_get_qa_resolutions(self) -> None:
        if not self.require_session():
            return
        payload = ensure_payload_defaults(load_json(EDITS_PATH))
        self.send_json({"qa_resolutions": payload.get("qa_resolutions", [])})

    def handle_get_duplicate_resolutions(self) -> None:
        if not self.require_session():
            return
        payload = ensure_payload_defaults(load_json(EDITS_PATH))
        self.send_json({"duplicate_resolutions": payload.get("duplicate_resolutions", [])})

    def handle_get_registry_edits(self) -> None:
        if not self.require_session():
            return
        payload = ensure_registry_payload_defaults(load_json(REGISTRY_EDITS_PATH))
        self.send_json({"registry_edits": payload.get("edits", [])})

    def handle_save_edit(self) -> None:
        session = self.require_session()
        if not session:
            return

        incoming = self.parse_json_body()
        payload = ensure_payload_defaults(load_json(EDITS_PATH))

        edit = {
            "edit_id": incoming.get("edit_id") or secrets.token_hex(8),
            "event_id": incoming.get("event_id"),
            "editor_name": session["display_name"],
            "editor_role": session["role"],
            "edited_at": now_iso(),
            "status": incoming.get("status") or "saved",
            "comment": incoming.get("comment"),
            "patch": incoming.get("patch") or {},
            "actor_patches": [normalize_actor_patch(item) for item in (incoming.get("actor_patches") or [])],
        }

        is_valid, warnings = validate_edit_against_clearance(edit, payload)
        if not is_valid:
            self.send_json({"ok": False, "error": "clearance_violation", "warnings": warnings}, status=403)
            return

        payload["edits"] = [existing for existing in payload.get("edits", []) if existing.get("event_id") != edit["event_id"]]
        payload["edits"].append(edit)
        payload["updated_at"] = now_iso()
        write_json(EDITS_PATH, payload)

        try:
            run_apply_step()
        except subprocess.CalledProcessError as exc:
            self.send_json({"ok": False, "error": "apply_failed", "detail": str(exc)}, status=500)
            return

        self.send_json({"ok": True, "edit": edit, "warnings": warnings})

    def handle_save_qa_resolution(self) -> None:
        session = self.require_session()
        if not session:
            return

        incoming = self.parse_json_body()
        payload = ensure_payload_defaults(load_json(EDITS_PATH))
        resolution = {
            "resolution_id": incoming.get("resolution_id") or secrets.token_hex(8),
            "flag_id": incoming.get("flag_id"),
            "event_id": incoming.get("event_id"),
            "editor_name": session["display_name"],
            "editor_role": session["role"],
            "resolved_at": now_iso(),
            "status": incoming.get("status") or "resolved",
            "comment": incoming.get("comment"),
            "resolution_type": incoming.get("resolution_type") or "manual_fix",
        }
        payload["qa_resolutions"] = [
            existing for existing in payload.get("qa_resolutions", [])
            if existing.get("flag_id") != resolution["flag_id"]
        ]
        payload["qa_resolutions"].append(resolution)
        payload["updated_at"] = now_iso()
        write_json(EDITS_PATH, payload)
        run_apply_step()
        self.send_json({"ok": True, "qa_resolution": resolution})

    def handle_undo_qa_resolution(self) -> None:
        session = self.require_session()
        if not session:
            return

        incoming = self.parse_json_body()
        flag_id = incoming.get("flag_id")
        if not flag_id:
            self.send_json({"ok": False, "error": "flag_id_required"}, status=400)
            return

        payload = ensure_payload_defaults(load_json(EDITS_PATH))
        updated = None
        for resolution in payload.get("qa_resolutions", []):
            if resolution.get("flag_id") != flag_id:
                continue
            resolution["status"] = "undone"
            resolution["undone_at"] = now_iso()
            resolution["undone_by"] = session["display_name"]
            resolution["undo_comment"] = incoming.get("comment") or "QA resolution undone in analyst console."
            updated = resolution
            break

        if not updated:
            self.send_json({"ok": False, "error": "qa_resolution_not_found"}, status=404)
            return

        payload["updated_at"] = now_iso()
        write_json(EDITS_PATH, payload)
        run_apply_step()
        self.send_json({"ok": True, "qa_resolution": updated})

    def handle_save_duplicate_resolution(self) -> None:
        session = self.require_session()
        if not session:
            return

        incoming = self.parse_json_body()
        payload = ensure_payload_defaults(load_json(EDITS_PATH))
        resolution = {
            "resolution_id": incoming.get("resolution_id") or secrets.token_hex(8),
            "candidate_id": incoming.get("candidate_id"),
            "keeper_event_id": incoming.get("keeper_event_id"),
            "merged_event_ids": incoming.get("merged_event_ids") or [],
            "event_ids": incoming.get("event_ids") or [],
            "reason_code": incoming.get("reason_code"),
            "manual": bool(incoming.get("manual")),
            "keeper_patch": incoming.get("keeper_patch") or {},
            "editor_name": session["display_name"],
            "editor_role": session["role"],
            "resolved_at": now_iso(),
            "status": incoming.get("status") or "merged",
            "comment": incoming.get("comment"),
        }
        payload["duplicate_resolutions"] = [
            existing for existing in payload.get("duplicate_resolutions", [])
            if existing.get("candidate_id") != resolution["candidate_id"]
        ]
        payload["duplicate_resolutions"].append(resolution)
        payload["updated_at"] = now_iso()
        write_json(EDITS_PATH, payload)
        run_apply_step()
        self.send_json({"ok": True, "duplicate_resolution": resolution})

    def handle_undo_duplicate_resolution(self) -> None:
        session = self.require_session()
        if not session:
            return

        incoming = self.parse_json_body()
        candidate_id = incoming.get("candidate_id")
        if not candidate_id:
            self.send_json({"ok": False, "error": "candidate_id_required"}, status=400)
            return

        payload = ensure_payload_defaults(load_json(EDITS_PATH))
        updated = None
        for resolution in payload.get("duplicate_resolutions", []):
            if resolution.get("candidate_id") != candidate_id:
                continue
            resolution["status"] = "undone"
            resolution["undone_at"] = now_iso()
            resolution["undone_by"] = session["display_name"]
            resolution["undo_comment"] = incoming.get("comment") or "Duplicate merge undone in analyst console."
            updated = resolution
            break

        if not updated:
            self.send_json({"ok": False, "error": "duplicate_resolution_not_found"}, status=404)
            return

        payload["updated_at"] = now_iso()
        write_json(EDITS_PATH, payload)
        run_apply_step()
        self.send_json({"ok": True, "duplicate_resolution": updated})

    def handle_save_registry_edit(self) -> None:
        session = self.require_session()
        if not session:
            return
        if session.get("role") not in {"analyst", "coordinator"}:
            self.send_json({"ok": False, "error": "registry_clearance_violation"}, status=403)
            return

        incoming = self.parse_json_body()
        payload = ensure_registry_payload_defaults(load_json(REGISTRY_EDITS_PATH))
        edit = {
            "edit_id": incoming.get("edit_id") or secrets.token_hex(8),
            "action": incoming.get("action") or "upsert_registry_entry",
            "registry_id": incoming.get("registry_id"),
            "source_event_id": incoming.get("source_event_id"),
            "source_actor_id": incoming.get("source_actor_id"),
            "editor_name": session["display_name"],
            "editor_role": session["role"],
            "edited_at": now_iso(),
            "comment": incoming.get("comment"),
            "entry": incoming.get("entry") or {},
        }
        payload["edits"].append(edit)
        payload["updated_at"] = now_iso()
        write_json(REGISTRY_EDITS_PATH, payload)

        try:
            run_registry_apply_step()
        except subprocess.CalledProcessError as exc:
            self.send_json({"ok": False, "error": "registry_apply_failed", "detail": str(exc)}, status=500)
            return

        self.send_json({"ok": True, "registry_edit": edit})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local authenticated analyst server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    args = parser.parse_args()

    ensure_local_runtime_files()
    host = args.host
    port = args.port
    server = ThreadingHTTPServer((host, port), AnalystHandler)
    print(f"SENTINEL analyst server running at http://{host}:{port}")
    print("Using local-only analyst files:")
    print(f"  Credentials: {USERS_PATH.relative_to(ROOT)}")
    print(f"  Edits: {EDITS_PATH.relative_to(ROOT)}")
    print(f"  Registry edits: {REGISTRY_EDITS_PATH.relative_to(ROOT)}")
    server.serve_forever()


if __name__ == "__main__":
    main()
