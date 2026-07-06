"""In-memory workspace repository (PostgreSQL schema compatible)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
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
        for key in ("title", "content", "format", "tags"):
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
            "created_at": now,
            "updated_at": now,
        }
        self.calendar_events[event_id] = event
        return event

    def list_events(
        self,
        user: dict[str, Any],
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        rows = [event for event in self.calendar_events.values() if event["user_id"] == _user_key(user)]
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
        return event

    def update_event(self, user: dict[str, Any], event_id: str, **fields: Any) -> dict[str, Any]:
        event = self.get_event(user, event_id)
        for key in ("title", "description", "location", "start_at", "end_at", "all_day", "recurrence", "reminders"):
            if fields.get(key) is not None:
                event[key] = fields[key]
        event["updated_at"] = _now()
        return event

    def delete_event(self, user: dict[str, Any], event_id: str) -> None:
        self.get_event(user, event_id)
        self.calendar_events.pop(event_id, None)

    def add_caldav_source(self, user: dict[str, Any], **fields: Any) -> dict[str, Any]:
        source_id = str(uuid4())
        source = {
            "id": source_id,
            "user_id": _user_key(user),
            "name": fields["name"],
            "url": fields["url"],
            "username": fields["username"],
            "vault_item_id": fields.get("vault_item_id"),
            "created_at": _now(),
        }
        self.caldav_sources[source_id] = source
        return source

    def list_caldav_sources(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        return [source for source in self.caldav_sources.values() if source["user_id"] == _user_key(user)]

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
