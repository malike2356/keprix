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
