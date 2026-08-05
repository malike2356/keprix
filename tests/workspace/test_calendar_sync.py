"""Calendar sync source CRUD and ICS pull."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from keprix.workspace.repository import WorkspaceRepository


def test_caldav_source_encrypts_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    repo = WorkspaceRepository()
    user = {"id": "u1", "username": "u1"}
    source = repo.add_caldav_source(
        user,
        name="Nextcloud",
        provider="nextcloud",
        url="https://cloud.example/remote.php/dav/",
        username="alice",
        password="secret-app-password",
        sync_direction="bidirectional",
        push_local_events=True,
    )
    assert source["has_password"] is True
    assert repo.get_source_password(source["id"]) == "secret-app-password"
    public = repo.list_caldav_sources(user)[0]
    assert "password_encrypted" not in public
    assert public["push_local_events"] is True


def test_upsert_event_by_uid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    repo = WorkspaceRepository()
    user = {"id": "u2"}
    first = repo.upsert_event_by_uid(
        user,
        caldav_source_id="src-1",
        uid="evt-1@external",
        title="One",
        start_at=datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc),
        external_readonly=True,
    )
    second = repo.upsert_event_by_uid(
        user,
        caldav_source_id="src-1",
        uid="evt-1@external",
        title="One updated",
        start_at=datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 10, 10, 30, tzinfo=timezone.utc),
        external_readonly=True,
    )
    assert first["id"] == second["id"]
    assert second["title"] == "One updated"


def test_google_url_autofill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    repo = WorkspaceRepository()
    source = repo.add_caldav_source(
        {"id": "u3"},
        name="GCal",
        provider="google",
        url="",
        username="me@example.com",
        password="token",
        sync_direction="pull",
    )
    assert "apidata.googleusercontent.com/caldav/v2/" in source["url"]
    assert "me%40example.com" in source["url"] or "me@example.com" in source["url"]


@pytest.mark.asyncio
async def test_pull_ics_feed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from keprix.workspace.calendar_sync import sync_one_source

    repo = WorkspaceRepository()
    user = {"id": "u4"}
    source = repo.add_caldav_source(
        user,
        name="ICS",
        provider="ics",
        url="https://example.com/calendar.ics",
        sync_direction="pull",
    )
    full = repo.get_caldav_source(user, source["id"])

    ics_payload = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-event-1@keprix
DTSTART:20260715T100000Z
DTEND:20260715T110000Z
SUMMARY:Synced Meeting
END:VEVENT
END:VCALENDAR
"""

    class FakeResponse:
        content = ics_payload

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers=None, auth=None):
            return FakeResponse()

    monkeypatch.setattr("keprix.workspace.calendar_sync.httpx.AsyncClient", FakeClient)
    outcome = await sync_one_source(user, full, repo)
    assert outcome["ok"] is True
    assert outcome["pulled"] == 1
    events = repo.list_events(user)
    assert any(event["title"] == "Synced Meeting" for event in events)


def test_auto_sync_due_and_interval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from keprix.workspace.calendar_sync_scheduler import clamp_sync_interval_minutes, source_is_due

    assert clamp_sync_interval_minutes(0) == 1
    assert clamp_sync_interval_minutes(99999) == 1440
    assert clamp_sync_interval_minutes("15") == 15

    repo = WorkspaceRepository()
    user = {"id": "u5"}
    source = repo.add_caldav_source(
        user,
        name="Auto",
        provider="caldav",
        url="https://caldav.example/",
        username="a",
        password="b",
        auto_sync=True,
        sync_interval_minutes=15,
        push_local_events=True,
    )
    full = repo.get_caldav_source(user, source["id"])
    assert source_is_due(full) is True
    assert source["auto_sync"] is True
    assert source["sync_interval_minutes"] == 15
    assert source["push_local_events"] is True

    repo.mark_source_synced(user, source["id"], ok=True, message="ok")
    full2 = repo.get_caldav_source(user, source["id"])
    assert source_is_due(full2) is False
    assert repo.list_due_caldav_sources() == []

    public = repo.update_caldav_source(user, source["id"], auto_sync=False, sync_interval_minutes=5)
    assert public["auto_sync"] is False
    assert public["sync_interval_minutes"] == 5
    assert public["next_sync_at"] is None


@pytest.mark.asyncio
async def test_run_due_sources_invokes_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from keprix.workspace import calendar_sync_scheduler as sched

    repo = WorkspaceRepository()
    user = {"id": "u6"}
    source = repo.add_caldav_source(
        user,
        name="Due",
        provider="ics",
        url="https://example.com/x.ics",
        auto_sync=True,
        sync_interval_minutes=5,
    )

    async def fake_sync(user_arg, source_arg, repo_arg):
        return {"source_id": source_arg["id"], "ok": True, "pulled": 0, "pushed": 0, "message": "ok"}

    monkeypatch.setattr("keprix.workspace.calendar_sync.sync_one_source", fake_sync)

    summary = await sched.run_due_sources(repo)
    assert summary["due"] == 1
    assert summary["synced"] == 1
    assert summary["errors"] == 0
    refreshed = repo.get_caldav_source(user, source["id"])
    assert refreshed["last_sync_ok"] is True
