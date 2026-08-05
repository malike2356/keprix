"""In-memory workspace repository (PostgreSQL schema compatible)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.workspace.core.exceptions import NotFoundError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_key(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _message_preview(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = str(block.get("content") or "").strip()
                if text:
                    return text
    return ""


def _calendar_store_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir())
    except Exception:
        root = Path(os.environ.get("KEPRIX_DATA_DIR") or Path.home() / ".keprix")
    path = root / "workspace" / "calendar_store.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _fernet():
    from cryptography.fernet import Fernet

    raw = (
        os.environ.get("KEPRIX_VAULT_KEY")
        or os.environ.get("KEPRIX_SESSION_SECRET")
        or os.environ.get("SESSION_SECRET")
        or "keprix-local-calendar-secret"
    )
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Not serializable: {type(value)}")


def _parse_dt_value(value: Any) -> Any:
    if isinstance(value, str) and "T" in value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value


class WorkspaceRepository:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.notes: dict[str, dict[str, Any]] = {}
        self.tasks: dict[str, dict[str, Any]] = {}
        self.calendar_events: dict[str, dict[str, Any]] = {}
        self.caldav_sources: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.presets: dict[str, dict[str, Any]] = {}
        self.assistants: dict[str, dict[str, Any]] = {}
        self.profiles: dict[str, dict[str, Any]] = {}
        self.prefs: dict[str, dict[str, Any]] = {}
        self.active_presets: dict[str, str] = {}
        self._load_calendar_store()

    def _load_calendar_store(self) -> None:
        path = _calendar_store_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        for event_id, event in (payload.get("events") or {}).items():
            row = dict(event)
            row["start_at"] = _parse_dt_value(row.get("start_at"))
            row["end_at"] = _parse_dt_value(row.get("end_at"))
            row["created_at"] = _parse_dt_value(row.get("created_at")) or _now()
            row["updated_at"] = _parse_dt_value(row.get("updated_at")) or _now()
            self.calendar_events[event_id] = row
        for source_id, source in (payload.get("sources") or {}).items():
            row = dict(source)
            row["created_at"] = _parse_dt_value(row.get("created_at")) or _now()
            row["last_sync_at"] = _parse_dt_value(row.get("last_sync_at"))
            self.caldav_sources[source_id] = row

    def _persist_calendar_store(self) -> None:
        path = _calendar_store_path()
        payload = {
            "events": self.calendar_events,
            "sources": self.caldav_sources,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
        tmp.replace(path)

    # Documents
    def create_document(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        doc_id = str(uuid4())
        now = _now()
        doc = {
            "id": doc_id,
            "user_id": _user_key(user),
            "title": fields.get("title", "Untitled"),
            "content": fields.get("content", ""),
            "format": fields.get("format", "markdown"),
            "tags": fields.get("tags") or [],
            "is_shared": False,
            "share_token": None,
            "is_favorite": bool(fields.get("is_favorite", False)),
            "folder": fields.get("folder") or "",
            "created_at": now,
            "updated_at": now,
        }
        self.documents[doc_id] = doc
        return doc

    def list_documents(
        self,
        user: dict[str, Any],
        *,
        tag: str | None = None,
        fmt: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = [doc for doc in self.documents.values() if doc["user_id"] == _user_key(user)]
        if tag:
            rows = [doc for doc in rows if tag in (doc.get("tags") or [])]
        if fmt:
            rows = [doc for doc in rows if doc.get("format") == fmt]
        rows.sort(key=lambda row: row["updated_at"], reverse=True)
        return rows[offset : offset + limit]

    def get_document(self, user: dict[str, Any], doc_id: str) -> dict[str, Any]:
        doc = self.documents.get(doc_id)
        if not doc or doc["user_id"] != _user_key(user):
            raise NotFoundError(doc_id)
        return doc

    def update_document(self, user: dict[str, Any], doc_id: str, **fields: Any) -> dict[str, Any]:
        doc = self.get_document(user, doc_id)
        for key in ("title", "content", "format", "tags", "is_favorite", "folder", "is_shared", "share_token"):
            if fields.get(key) is not None:
                doc[key] = fields[key]
        doc["updated_at"] = _now()
        return doc

    def delete_document(self, user: dict[str, Any], doc_id: str) -> None:
        self.get_document(user, doc_id)
        self.documents.pop(doc_id, None)

    def share_document(self, user: dict[str, Any], doc_id: str) -> dict[str, Any]:
        doc = self.get_document(user, doc_id)
        doc["is_shared"] = True
        doc["share_token"] = secrets.token_urlsafe(24)
        doc["updated_at"] = _now()
        return doc

    # Notes
    def create_note(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        note_id = str(uuid4())
        now = _now()
        note = {
            "id": note_id,
            "user_id": _user_key(user),
            "title": fields.get("title", ""),
            "content": fields.get("content", ""),
            "tags": fields.get("tags") or [],
            "is_pinned": fields.get("is_pinned", False),
            "created_at": now,
            "updated_at": now,
        }
        self.notes[note_id] = note
        return note

    def list_notes(self, user: dict[str, Any], *, tag: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
        rows = [note for note in self.notes.values() if note["user_id"] == _user_key(user)]
        if tag:
            rows = [note for note in rows if tag in (note.get("tags") or [])]
        if search:
            q = search.lower()
            rows = [
                note
                for note in rows
                if q in note.get("title", "").lower() or q in note.get("content", "").lower()
            ]
        rows.sort(key=lambda row: (not row.get("is_pinned"), row["updated_at"]), reverse=True)
        return rows

    def get_note(self, user: dict[str, Any], note_id: str) -> dict[str, Any]:
        note = self.notes.get(note_id)
        if not note or note["user_id"] != _user_key(user):
            raise NotFoundError(note_id)
        return note

    def update_note(self, user: dict[str, Any], note_id: str, **fields: Any) -> dict[str, Any]:
        note = self.get_note(user, note_id)
        for key in ("title", "content", "tags", "is_pinned"):
            if fields.get(key) is not None:
                note[key] = fields[key]
        note["updated_at"] = _now()
        return note

    def delete_note(self, user: dict[str, Any], note_id: str) -> None:
        self.get_note(user, note_id)
        self.notes.pop(note_id, None)

    def search_notes(self, user: dict[str, Any], query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self.list_notes(user, search=query)[:limit]

    # Tasks
    def create_task(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        task_id = str(uuid4())
        now = _now()
        sort_order = len([t for t in self.tasks.values() if t["user_id"] == _user_key(user)])
        task = {
            "id": task_id,
            "user_id": _user_key(user),
            "title": fields["title"],
            "description": fields.get("description", ""),
            "status": fields.get("status", "todo"),
            "priority": fields.get("priority", "normal"),
            "due_at": fields.get("due_at"),
            "sort_order": sort_order,
            "tags": fields.get("tags") or [],
            "agent_scheduled": fields.get("agent_scheduled", False),
            "created_at": now,
            "updated_at": now,
        }
        self.tasks[task_id] = task
        return task

    def list_tasks(
        self,
        user: dict[str, Any],
        *,
        status: str | None = None,
        tag: str | None = None,
        due_before: datetime | None = None,
    ) -> list[dict[str, Any]]:
        rows = [task for task in self.tasks.values() if task["user_id"] == _user_key(user)]
        if status:
            rows = [task for task in rows if task.get("status") == status]
        if tag:
            rows = [task for task in rows if tag in (task.get("tags") or [])]
        if due_before:
            rows = [task for task in rows if task.get("due_at") and task["due_at"] <= due_before]
        rows.sort(key=lambda row: (row.get("sort_order", 0), row["created_at"]))
        return rows

    def get_task(self, user: dict[str, Any], task_id: str) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if not task or task["user_id"] != _user_key(user):
            raise NotFoundError(task_id)
        return task

    def update_task(self, user: dict[str, Any], task_id: str, **fields: Any) -> dict[str, Any]:
        task = self.get_task(user, task_id)
        for key in ("title", "description", "status", "priority", "due_at", "tags"):
            if fields.get(key) is not None:
                task[key] = fields[key]
        task["updated_at"] = _now()
        return task

    def delete_task(self, user: dict[str, Any], task_id: str) -> None:
        self.get_task(user, task_id)
        self.tasks.pop(task_id, None)

    def complete_task(self, user: dict[str, Any], task_id: str) -> dict[str, Any]:
        return self.update_task(user, task_id, status="done")

    def reorder_tasks(self, user: dict[str, Any], order: list[str]) -> list[dict[str, Any]]:
        for index, task_id in enumerate(order):
            task = self.get_task(user, task_id)
            task["sort_order"] = index
            task["updated_at"] = _now()
        return self.list_tasks(user)

    # Calendar
    def create_event(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        event_id = str(uuid4())
        uid = fields.get("uid") or f"keprix-{event_id}@local"
        now = _now()
        tenant_id = fields.get("tenant_id")
        if not tenant_id:
            try:
                from keprix.tenancy.isolation import current_tenant_id

                tenant_id = current_tenant_id()
            except Exception:
                tenant_id = None
        event = {
            "id": event_id,
            "user_id": _user_key(user),
            "uid": uid,
            "title": fields["title"],
            "description": fields.get("description", ""),
            "location": fields.get("location", ""),
            "start_at": fields["start_at"],
            "end_at": fields["end_at"],
            "all_day": fields.get("all_day", False),
            "recurrence": fields.get("recurrence"),
            "reminders": fields.get("reminders") or [15],
            "caldav_source_id": fields.get("caldav_source_id"),
            "external_readonly": bool(fields.get("external_readonly", False)),
            "metadata": dict(fields.get("metadata") or {}),
            "tenant_id": tenant_id,
            "created_at": now,
            "updated_at": now,
        }
        self.calendar_events[event_id] = event
        self._persist_calendar_store()
        return event

    def upsert_event_by_uid(self, user: dict[str, Any], *, caldav_source_id: str, **fields: Any) -> dict[str, Any]:
        uid = str(fields.get("uid") or "").strip()
        if not uid:
            raise ValueError("uid is required")
        user_id = _user_key(user)
        for event in self.calendar_events.values():
            if event.get("user_id") == user_id and event.get("uid") == uid:
                for key in ("title", "description", "location", "start_at", "end_at", "all_day", "recurrence", "reminders"):
                    if fields.get(key) is not None:
                        event[key] = fields[key]
                event["caldav_source_id"] = caldav_source_id
                event["external_readonly"] = bool(fields.get("external_readonly", event.get("external_readonly", False)))
                event["updated_at"] = _now()
                self._persist_calendar_store()
                return event
        return self.create_event(
            user,
            uid=uid,
            caldav_source_id=caldav_source_id,
            external_readonly=fields.get("external_readonly", False),
            title=fields["title"],
            description=fields.get("description", ""),
            location=fields.get("location", ""),
            start_at=fields["start_at"],
            end_at=fields["end_at"],
            all_day=fields.get("all_day", False),
            recurrence=fields.get("recurrence"),
            reminders=fields.get("reminders") or [15],
        )

    def list_events(
        self,
        user: dict[str, Any],
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        rows = [event for event in self.calendar_events.values() if event["user_id"] == _user_key(user)]
        try:
            from keprix.tenancy.isolation import assert_tenant_owns, current_tenant_id, isolation_enabled

            if isolation_enabled():
                tid = current_tenant_id()
                filtered = []
                for event in rows:
                    if event.get("tenant_id") in (None, tid):
                        filtered.append(event)
                rows = filtered
        except Exception:
            pass
        if start:
            rows = [event for event in rows if event["end_at"] >= start]
        if end:
            rows = [event for event in rows if event["start_at"] <= end]
        rows.sort(key=lambda row: row["start_at"])
        return rows

    def get_event(self, user: dict[str, Any], event_id: str) -> dict[str, Any]:
        event = self.calendar_events.get(event_id)
        if not event or event["user_id"] != _user_key(user):
            raise NotFoundError(event_id)
        try:
            from keprix.tenancy.isolation import TenantIsolationError, assert_tenant_owns

            assert_tenant_owns(event)
        except TenantIsolationError as exc:
            raise NotFoundError(event_id) from exc
        return event

    def update_event(self, user: dict[str, Any], event_id: str, **fields: Any) -> dict[str, Any]:
        event = self.get_event(user, event_id)
        for key in (
            "title",
            "description",
            "location",
            "start_at",
            "end_at",
            "all_day",
            "recurrence",
            "reminders",
            "caldav_source_id",
            "uid",
            "external_readonly",
        ):
            if key in fields and fields.get(key) is not None:
                event[key] = fields[key]
            elif key in fields and fields.get(key) is None and key in {"caldav_source_id", "recurrence"}:
                event[key] = None
        if fields.get("external_etag") is True:
            event["external_synced_at"] = _now()
        event["updated_at"] = _now()
        self._persist_calendar_store()
        return event

    def delete_event(self, user: dict[str, Any], event_id: str) -> None:
        self.get_event(user, event_id)
        self.calendar_events.pop(event_id, None)
        self._persist_calendar_store()

    def add_caldav_source(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        from keprix.workspace.calendar_sync_scheduler import clamp_sync_interval_minutes

        source_id = str(uuid4())
        password = fields.get("password")
        provider = str(fields.get("provider") or "caldav").lower()
        url = str(fields.get("url") or "").strip()
        username = str(fields.get("username") or "").strip()
        if provider == "google" and username and not url:
            from keprix.workspace.calendar_sync import default_google_caldav_url

            url = default_google_caldav_url(username)
        is_ics = provider == "ics"
        default_direction = "pull" if is_ics else "bidirectional"
        default_push = False if is_ics else bool(fields.get("push_local_events", True))
        source = {
            "id": source_id,
            "user_id": _user_key(user),
            "name": fields["name"],
            "provider": provider,
            "url": url,
            "username": username,
            "vault_item_id": fields.get("vault_item_id"),
            "password_encrypted": _encrypt_secret(password) if password else None,
            "has_password": bool(password or fields.get("vault_item_id")),
            "sync_direction": fields.get("sync_direction") or default_direction,
            "calendar_href": fields.get("calendar_href"),
            "calendar_name": fields.get("calendar_name"),
            "push_local_events": False if is_ics else default_push,
            "enabled": bool(fields.get("enabled", True)),
            "auto_sync": bool(fields.get("auto_sync", True)),
            "sync_interval_minutes": clamp_sync_interval_minutes(fields.get("sync_interval_minutes")),
            "pull_past_days": int(fields.get("pull_past_days") or 90),
            "pull_future_days": int(fields.get("pull_future_days") or 365),
            "last_sync_at": None,
            "last_sync_ok": None,
            "last_sync_message": None,
            "created_at": _now(),
        }
        if is_ics:
            source["sync_direction"] = "pull"
        self.caldav_sources[source_id] = source
        self._persist_calendar_store()
        return self._public_source(source)

    def update_caldav_source(self, user: dict[str, Any], source_id: str, **fields: Any) -> dict[str, Any]:
        from keprix.workspace.calendar_sync_scheduler import clamp_sync_interval_minutes

        source = self.get_caldav_source(user, source_id)
        for key in (
            "name",
            "url",
            "username",
            "provider",
            "sync_direction",
            "calendar_href",
            "calendar_name",
            "push_local_events",
            "enabled",
            "auto_sync",
            "pull_past_days",
            "pull_future_days",
            "vault_item_id",
        ):
            if key in fields and fields.get(key) is not None:
                source[key] = fields[key]
        if fields.get("sync_interval_minutes") is not None:
            source["sync_interval_minutes"] = clamp_sync_interval_minutes(fields.get("sync_interval_minutes"))
        if fields.get("password"):
            source["password_encrypted"] = _encrypt_secret(str(fields["password"]))
            source["has_password"] = True
        if source.get("provider") == "google" and source.get("username") and not source.get("url"):
            from keprix.workspace.calendar_sync import default_google_caldav_url

            source["url"] = default_google_caldav_url(source["username"])
        if source.get("provider") == "ics":
            source["sync_direction"] = "pull"
            source["push_local_events"] = False
        self._persist_calendar_store()
        return self._public_source(source)

    def get_caldav_source(self, user: dict[str, Any], source_id: str) -> dict[str, Any]:
        source = self.caldav_sources.get(source_id)
        if not source or source["user_id"] != _user_key(user):
            raise NotFoundError(source_id)
        return source

    def delete_caldav_source(self, user: dict[str, Any], source_id: str, *, remove_events: bool = False) -> None:
        self.get_caldav_source(user, source_id)
        self.caldav_sources.pop(source_id, None)
        if remove_events:
            for event_id, event in list(self.calendar_events.items()):
                if event.get("user_id") == _user_key(user) and event.get("caldav_source_id") == source_id:
                    self.calendar_events.pop(event_id, None)
        self._persist_calendar_store()

    def list_caldav_sources(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        rows = [source for source in self.caldav_sources.values() if source["user_id"] == _user_key(user)]
        rows.sort(key=lambda row: str(row.get("created_at") or ""))
        return [self._public_source(row) for row in rows]

    def list_due_caldav_sources(self) -> list[dict[str, Any]]:
        from keprix.workspace.calendar_sync_scheduler import source_is_due

        due = [source for source in self.caldav_sources.values() if source_is_due(source)]
        due.sort(key=lambda row: str(row.get("last_sync_at") or ""))
        return due

    def get_source_password(self, source_id: str) -> str | None:
        source = self.caldav_sources.get(source_id)
        if not source:
            return None
        token = source.get("password_encrypted")
        if not token:
            return None
        try:
            return _decrypt_secret(token)
        except Exception:
            return None

    def mark_source_synced(
        self,
        user: dict[str, Any],
        source_id: str,
        *,
        ok: bool,
        message: str | None = None,
    ) -> dict[str, Any]:
        source = self.get_caldav_source(user, source_id)
        source["last_sync_at"] = _now()
        source["last_sync_ok"] = bool(ok)
        source["last_sync_message"] = message
        self._persist_calendar_store()
        return self._public_source(source)

    def default_push_source(self, user: dict[str, Any]) -> dict[str, Any] | None:
        for source in self.list_caldav_sources(user):
            full = self.get_caldav_source(user, source["id"])
            if full.get("enabled") is False:
                continue
            if full.get("provider") == "ics":
                continue
            if str(full.get("sync_direction") or "").lower() in {"push", "bidirectional"} and full.get("push_local_events"):
                return full
        return None

    def _public_source(self, source: dict[str, Any]) -> dict[str, Any]:
        from keprix.workspace.calendar_sync_scheduler import clamp_sync_interval_minutes, next_sync_at

        nxt = next_sync_at(source)
        return {
            "id": source["id"],
            "name": source.get("name"),
            "provider": source.get("provider") or "caldav",
            "url": source.get("url"),
            "username": source.get("username"),
            "vault_item_id": source.get("vault_item_id"),
            "has_password": bool(source.get("has_password") or source.get("password_encrypted")),
            "sync_direction": source.get("sync_direction") or "bidirectional",
            "calendar_href": source.get("calendar_href"),
            "calendar_name": source.get("calendar_name"),
            "push_local_events": bool(source.get("push_local_events", False)),
            "enabled": source.get("enabled", True),
            "auto_sync": source.get("auto_sync", True),
            "sync_interval_minutes": clamp_sync_interval_minutes(source.get("sync_interval_minutes")),
            "pull_past_days": source.get("pull_past_days", 90),
            "pull_future_days": source.get("pull_future_days", 365),
            "last_sync_at": source.get("last_sync_at"),
            "last_sync_ok": source.get("last_sync_ok"),
            "last_sync_message": source.get("last_sync_message"),
            "next_sync_at": nxt.isoformat() if nxt else None,
            "created_at": source.get("created_at"),
        }

    # Sessions
    def create_session(self, user: dict[str, Any], title: str, messages: list | None = None) -> dict[str, Any]:
        session_id = str(uuid4())
        now = _now()
        session = {
            "id": session_id,
            "user_id": _user_key(user),
            "title": title,
            "messages": messages or [],
            "created_at": now,
            "updated_at": now,
        }
        self.sessions[session_id] = session
        return session

    def list_sessions(self, user: dict[str, Any], limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        rows = [session for session in self.sessions.values() if session["user_id"] == _user_key(user)]
        rows.sort(key=lambda row: row["updated_at"], reverse=True)
        return rows[offset : offset + limit]

    def get_session(self, user: dict[str, Any], session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session or session["user_id"] != _user_key(user):
            raise NotFoundError(session_id)
        return session

    def rename_session(self, user: dict[str, Any], session_id: str, title: str) -> dict[str, Any]:
        session = self.get_session(user, session_id)
        session["title"] = title
        session["updated_at"] = _now()
        return session

    def delete_session(self, user: dict[str, Any], session_id: str) -> None:
        self.get_session(user, session_id)
        self.sessions.pop(session_id, None)

    def append_message(self, user: dict[str, Any], session_id: str, message: dict[str, Any]) -> dict[str, Any]:
        session = self.get_session(user, session_id)
        messages = session.setdefault("messages", [])
        messages.append(message)
        session["updated_at"] = _now()
        if message.get("role") == "user" and len(messages) == 1:
            preview = _message_preview(message)
            if preview and session.get("title") in (None, "", "New conversation"):
                session["title"] = preview[:80]
        return message

    def set_messages(self, user: dict[str, Any], session_id: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        session = self.get_session(user, session_id)
        session["messages"] = messages
        session["updated_at"] = _now()
        return session

    # Presets / assistants / profile / prefs
    def create_preset(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        preset_id = str(uuid4())
        now = _now()
        preset = {
            "id": preset_id,
            "user_id": _user_key(user),
            "name": fields["name"],
            "system_prompt": fields["system_prompt"],
            "description": fields.get("description", ""),
            "created_at": now,
            "updated_at": now,
        }
        self.presets[preset_id] = preset
        return preset

    def list_presets(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        return [preset for preset in self.presets.values() if preset["user_id"] == _user_key(user)]

    def update_preset(self, user: dict[str, Any], preset_id: str, **fields: Any) -> dict[str, Any]:
        preset = self.presets.get(preset_id)
        if not preset or preset["user_id"] != _user_key(user):
            raise NotFoundError(preset_id)
        for key in ("name", "system_prompt", "description"):
            if fields.get(key) is not None:
                preset[key] = fields[key]
        preset["updated_at"] = _now()
        return preset

    def delete_preset(self, user: dict[str, Any], preset_id: str) -> None:
        preset = self.presets.get(preset_id)
        if not preset or preset["user_id"] != _user_key(user):
            raise NotFoundError(preset_id)
        self.presets.pop(preset_id, None)

    def activate_preset(self, user: dict[str, Any], preset_id: str) -> dict[str, Any]:
        preset = self.update_preset(user, preset_id)  # validates ownership
        self.active_presets[_user_key(user)] = preset_id
        return preset

    def create_assistant(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        assistant_id = str(uuid4())
        now = _now()
        assistant = {
            "id": assistant_id,
            "user_id": _user_key(user),
            "name": fields["name"],
            "system_prompt": fields["system_prompt"],
            "model": fields.get("model", "gpt-4.1-mini"),
            "tools": fields.get("tools") or [],
            "created_at": now,
            "updated_at": now,
        }
        self.assistants[assistant_id] = assistant
        return assistant

    def list_assistants(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        return [assistant for assistant in self.assistants.values() if assistant["user_id"] == _user_key(user)]

    def update_assistant(self, user: dict[str, Any], assistant_id: str, **fields: Any) -> dict[str, Any]:
        assistant = self.assistants.get(assistant_id)
        if not assistant or assistant["user_id"] != _user_key(user):
            raise NotFoundError(assistant_id)
        for key in ("name", "system_prompt", "model", "tools"):
            if fields.get(key) is not None:
                assistant[key] = fields[key]
        assistant["updated_at"] = _now()
        return assistant

    def delete_assistant(self, user: dict[str, Any], assistant_id: str) -> None:
        assistant = self.assistants.get(assistant_id)
        if not assistant or assistant["user_id"] != _user_key(user):
            raise NotFoundError(assistant_id)
        self.assistants.pop(assistant_id, None)

    def get_profile(self, user: dict[str, Any]) -> dict[str, Any]:
        return self.profiles.setdefault(
            _user_key(user),
            {"name": user.get("username", ""), "timezone": "UTC", "language": "en"},
        )

    def update_profile(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        profile = self.get_profile(user)
        for key in ("name", "timezone", "language"):
            if fields.get(key) is not None:
                profile[key] = fields[key]
        self.profiles[_user_key(user)] = profile
        return profile

    def get_prefs(self, user: dict[str, Any]) -> dict[str, Any]:
        return self.prefs.setdefault(
            _user_key(user),
            {"theme": "system", "font_size": "medium", "layout_density": "comfortable", "active_preset_id": None},
        )

    def update_prefs(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        prefs = self.get_prefs(user)
        for key in ("theme", "font_size", "layout_density", "active_preset_id"):
            if fields.get(key) is not None:
                prefs[key] = fields[key]
        self.prefs[_user_key(user)] = prefs
        return prefs

    def wipe_user_data(self, user_id: str) -> dict[str, int]:
        counts = {}
        for name, store in (
            ("documents", self.documents),
            ("notes", self.notes),
            ("tasks", self.tasks),
            ("calendar_events", self.calendar_events),
            ("sessions", self.sessions),
        ):
            before = len(store)
            for key in list(store.keys()):
                if store[key].get("user_id") == user_id:
                    store.pop(key, None)
            counts[name] = before - len(store)
        return counts


workspace_repo = WorkspaceRepository()
