"""Pilot mesh: IDs, tools, discovery, parity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from keprix.capability_mesh.discovery import TOOL_SEARCH_SYNONYMS, render_discovery_markdown, write_discovery
from keprix.capability_mesh.dod import assert_dod
from keprix.capability_mesh.graph import load_graph
from keprix.capability_mesh.ids import calendar_event_metadata_for_booking, resolve_booking_links
from keprix.tools.mesh_workspace_tools import (
    PILOT_TOOL_NAMES,
    _handle_calendar_list,
    _handle_vical_create,
    _handle_vical_list,
    _handle_vical_slots,
)
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import vical_store
from keprix.workspace.repository import workspace_repo


@pytest.fixture(autouse=True)
def clean() -> None:
    workspace_repo.calendar_events.clear()
    vical_store.clear()
    yield
    workspace_repo.calendar_events.clear()
    vical_store.clear()


def _slot_start(days: int = 2) -> datetime:
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=days)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    return start


def test_id_roundtrip_and_calendar_metadata() -> None:
    ensure_default_consultation("mesh-user")
    from keprix.vical.bookings import BookingLifecycle

    booking = BookingLifecycle().create(
        "mesh-user",
        slug="consultation",
        guest_name="G",
        guest_email="g@example.com",
        starts_at=_slot_start(),
        contact_id="contact-123",
        skip_slot_check=True,
    )
    assert booking.contact_id == "contact-123"
    assert booking.workspace_event_id
    links = resolve_booking_links("mesh-user", booking.id)
    assert links["contact_id"] == "contact-123"
    assert links["workspace_event_id"] == booking.workspace_event_id
    event = workspace_repo.calendar_events[booking.workspace_event_id]
    assert event["metadata"]["vical_booking_id"] == booking.id
    assert calendar_event_metadata_for_booking(booking)["vical_booking_id"] == booking.id


def test_pilot_tools_slots_book_list() -> None:
    ensure_default_consultation("mesh-user")
    slots = _handle_vical_slots({"user_id": "mesh-user", "count": 3})
    assert "items" in slots
    start = _slot_start(3)
    created = _handle_vical_create(
        {
            "user_id": "mesh-user",
            "guest_name": "Tool Guest",
            "guest_email": "tool@example.com",
            "starts_at": start.isoformat(),
            "skip_slot_check": True,
        }
    )
    assert "id" in created or '"id"' in created
    listed = _handle_vical_list({"user_id": "mesh-user"})
    assert "Tool Guest" in listed or "tool@example.com" in listed
    cal = _handle_calendar_list({"user_id": "mesh-user"})
    assert "items" in cal


def test_pilot_tools_in_core_and_telegram() -> None:
    from keprix.toolsets import _KEPRIX_CORE_TOOLS, resolve_toolset

    for name in PILOT_TOOL_NAMES:
        assert name in _KEPRIX_CORE_TOOLS
    resolved = set(resolve_toolset("keprix-telegram"))
    for name in PILOT_TOOL_NAMES:
        assert name in resolved


def test_graph_pilot_nodes_wired_and_dod() -> None:
    graph = load_graph()
    for node_id in ("vical", "calendar", "contacts", "companies-house"):
        node = graph.get_node(node_id)
        assert node.status == "wired"
        assert "telegram" in node.channel_surfaces
        assert node.tools
    assert assert_dod(graph)["ok"] is True


def test_discovery_mentions_pilot_tools(tmp_path) -> None:
    text = render_discovery_markdown()
    assert "vical_offer_slots" in text
    assert "companies-house" in text
    path = write_discovery(tmp_path / "DISCOVERY.md")
    assert path.is_file()
    assert "vical_create_booking" in TOOL_SEARCH_SYNONYMS


def test_channel_parity_platforms_include_core_pilot() -> None:
    from keprix.toolsets import resolve_toolset

    for platform in ("keprix-telegram", "keprix-discord", "keprix-slack", "keprix-whatsapp", "keprix-cli"):
        tools = set(resolve_toolset(platform))
        for name in ("vical_offer_slots", "calendar_list_events", "contacts_search", "search:companies_house"):
            assert name in tools, f"{name} missing from {platform}"
