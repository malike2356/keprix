"""Calendar workspace UI guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CALENDAR = ROOT / "frontend" / "src" / "components" / "calendar"
PAGE = ROOT / "frontend" / "src" / "app" / "(workspace)" / "calendar" / "page.tsx"


def test_calendar_view_components_exist() -> None:
    required = [
        "CalendarMonthView.tsx",
        "CalendarWeekView.tsx",
        "CalendarDayView.tsx",
        "CalendarScheduleView.tsx",
        "CalendarEventChip.tsx",
    ]
    for name in required:
        assert (CALENDAR / name).is_file(), name


def test_calendar_page_exposes_view_modes() -> None:
    text = PAGE.read_text(encoding="utf-8")
    for label in ("Month", "Week", "Day", "Schedule"):
        assert label in text
    assert "CalendarMonthView" in text
    assert "CalendarWeekView" in text
    assert "CalendarDayView" in text
    assert "CalendarScheduleView" in text


def test_calendar_page_honors_event_deeplink_and_booking_create() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert 'searchParams.get("event")' in text
    assert "Open booking" in text
    assert "/vical?booking=" in text
    assert "createHostBooking" in text
    assert 'mode: "booking"' in text
    assert "onSelectSlot" in text
    mesh = (ROOT / "frontend" / "src" / "components" / "vical" / "MeshRelatedLinks.tsx").read_text(
        encoding="utf-8"
    )
    assert "Open booking" in mesh
    vical = (ROOT / "frontend" / "src" / "app" / "(workspace)" / "vical" / "page.tsx").read_text(
        encoding="utf-8"
    )
    assert 'searchParams.get("booking")' in vical
    api = (ROOT / "frontend" / "src" / "lib" / "vical-api.ts").read_text(encoding="utf-8")
    assert "createHostBooking" in api
    assert "skip_slot_check" in api
    routes = (ROOT / "src" / "keprix" / "vical" / "routes.py").read_text(encoding="utf-8")
    assert "skip_slot_check: bool = False" in routes
    day = (CALENDAR / "CalendarDayView.tsx").read_text(encoding="utf-8")
    week = (CALENDAR / "CalendarWeekView.tsx").read_text(encoding="utf-8")
    assert "onSelectSlot" in day
    assert "onSelectSlot" in week