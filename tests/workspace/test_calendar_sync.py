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


def test_pick_calendar_uses_google_events_url():
    from types import SimpleNamespace

    from keprix.workspace.calendar_sync import _pick_calendar

    class FakeClient:
        def calendar(self, url=None):
            return SimpleNamespace(url=url, kind="direct")

        def principal(self):
            raise AssertionError("principal should not be used for Google events URL")

    source = {
        "provider": "google",
        "url": "https://apidata.googleusercontent.com/caldav/v2/me%40gmail.com/events",
    }
    calendar = _pick_calendar(FakeClient(), source)
    assert calendar.kind == "direct"
    assert calendar.url.endswith("/events")


def test_google_calendar_api_pulls_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import asyncio

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from keprix.workspace.calendar_sync import sync_one_source

    repo = WorkspaceRepository()
    user = {"id": "u-google"}
    source = repo.add_caldav_source(
        user,
        name="Google Calendar",
        provider="google",
        username="me@example.com",
        password="ya29.access-token",
        sync_direction="pull",
    )
    full = repo.get_caldav_source(user, source["id"])

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "items": [
                    {
                        "id": "evt-dentist",
                        "summary": "Dentist",
                        "start": {"dateTime": "2026-09-20T10:00:00+01:00"},
                        "end": {"dateTime": "2026-09-20T11:00:00+01:00"},
                    },
                    {
                        "id": "evt-holiday",
                        "summary": "Holiday",
                        "start": {"date": "2026-09-21"},
                        "end": {"date": "2026-09-22"},
                    },
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers=None, params=None):
            assert "googleapis.com/calendar/v3/calendars/" in url
            assert headers["Authorization"] == "Bearer ya29.access-token"
            assert params["singleEvents"] == "true"
            return FakeResponse()

    monkeypatch.setattr("keprix.workspace.calendar_sync.httpx.AsyncClient", FakeClient)
    outcome = asyncio.run(sync_one_source(user, full, repo))
    assert outcome["ok"] is True
    assert outcome["pulled"] == 2
    events = repo.list_events(user)
    titles = {event["title"] for event in events}
    assert titles == {"Dentist", "Holiday"}
    holiday = next(event for event in events if event["title"] == "Holiday")
    assert holiday["all_day"] is True


def test_gmail_app_password_detection():
    from keprix.workspace.calendar_sync import looks_like_gmail_app_password, looks_like_google_oauth_token

    assert looks_like_gmail_app_password("abcdefghijklmnop") is True
    assert looks_like_gmail_app_password("abcd efgh ijkl mnop") is True
    assert looks_like_gmail_app_password("ya29.access-token") is False
    assert looks_like_google_oauth_token("ya29.access-token") is True
    assert looks_like_google_oauth_token("abcdefghijklmnop") is False


def test_google_app_password_is_not_sent_as_bearer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import asyncio

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from keprix.workspace.calendar_sync import google_app_password_error, sync_one_source

    repo = WorkspaceRepository()
    user = {"id": "u-app-pw"}
    source = repo.add_caldav_source(
        user,
        name="Google Calendar",
        provider="google",
        username="me@example.com",
        password="abcdefghijklmnop",
        sync_direction="bidirectional",
    )
    full = repo.get_caldav_source(user, source["id"])

    class FakeClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("must not call Google APIs with an app password")

    monkeypatch.setattr("keprix.workspace.calendar_sync.httpx.AsyncClient", FakeClient)
    with pytest.raises(ValueError, match="Gmail app passwords cannot access Google Calendar"):
        asyncio.run(sync_one_source(user, full, repo))
    assert "OAuth" in google_app_password_error()


def test_add_source_rejects_gmail_app_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import asyncio

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from fastapi import HTTPException

    from keprix.workspace.routes import calendar_routes
    from keprix.workspace.schemas import CaldavSourceCreate

    repo = WorkspaceRepository()
    monkeypatch.setattr(calendar_routes, "workspace_repo", repo)
    body = CaldavSourceCreate(
        name="Google Calendar",
        provider="google",
        username="me@example.com",
        password="abcdefghijklmnop",
        sync_direction="bidirectional",
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(calendar_routes.add_source(body, user={"id": "u-reject"}))
    assert exc.value.status_code == 400
    assert "Gmail app passwords" in str(exc.value.detail)


def test_google_ics_url_becomes_pull_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import asyncio

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from keprix.workspace.routes import calendar_routes
    from keprix.workspace.schemas import CaldavSourceCreate

    repo = WorkspaceRepository()

    async def fake_sync(user_arg, source_arg, repo_arg):
        assert source_arg["provider"] == "ics"
        return {"message": "Pulled 0 events from ICS feed", "pulled": 0, "pushed": 0}

    monkeypatch.setattr(calendar_routes, "workspace_repo", repo)
    monkeypatch.setattr(calendar_routes, "sync_one_source", fake_sync)
    body = CaldavSourceCreate(
        name="Google Calendar",
        provider="google",
        url="https://calendar.google.com/calendar/ical/me%40gmail.com/private-abc/basic.ics",
        username="me@example.com",
        sync_direction="bidirectional",
    )
    result = asyncio.run(calendar_routes.add_source(body, user={"id": "u-ics"}))
    stored = repo.get_caldav_source({"id": "u-ics"}, result["id"])
    assert stored["provider"] == "ics"
    assert stored["sync_direction"] == "pull"


def test_add_source_syncs_immediately(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import asyncio

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_SESSION_SECRET", "test-calendar-secret")
    from keprix.workspace.routes import calendar_routes
    from keprix.workspace.schemas import CaldavSourceCreate

    repo = WorkspaceRepository()
    called: dict[str, str] = {}

    async def fake_sync(user_arg, source_arg, repo_arg):
        called["id"] = source_arg["id"]
        repo_arg.upsert_event_by_uid(
            user_arg,
            caldav_source_id=source_arg["id"],
            uid="connected-1",
            title="Imported after connect",
            start_at=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        )
        return {"message": "Google pull=1 push=0", "pulled": 1, "pushed": 0}

    monkeypatch.setattr(calendar_routes, "workspace_repo", repo)
    monkeypatch.setattr(calendar_routes, "sync_one_source", fake_sync)
    body = CaldavSourceCreate(
        name="Google Calendar",
        provider="google",
        username="me@example.com",
        password="token",
        sync_direction="bidirectional",
    )
    result = asyncio.run(calendar_routes.add_source(body, user={"id": "u-connect"}))
    assert called["id"] == result["id"]
    assert result["last_sync_ok"] is True
    assert "Imported after connect" in {event["title"] for event in repo.list_events({"id": "u-connect"})}


def test_list_events_expands_weekly_rrule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    repo = WorkspaceRepository()
    user = {"id": "u-rrule"}
    repo.upsert_event_by_uid(
        user,
        caldav_source_id="src-rrule",
        uid="standup@example",
        title="Standup",
        start_at=datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 8, 3, 9, 30, tzinfo=timezone.utc),
        recurrence="FREQ=WEEKLY;BYDAY=MO",
    )
    rows = repo.list_events(
        user,
        start=datetime(2026, 9, 1, tzinfo=timezone.utc),
        end=datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc),
    )
    mondays = [row for row in rows if row["title"] == "Standup"]
    assert len(mondays) >= 4
    assert all(row["start_at"].month == 9 for row in mondays)


def test_dashboard_lifespan_starts_calendar_scheduler():
    text = Path(__file__).resolve().parents[2] / "src" / "keprix" / "keprix_cli" / "web_server.py"
    source = text.read_text(encoding="utf-8")
    assert "start_calendar_sync_scheduler" in source
    assert "stop_calendar_sync_scheduler" in source
