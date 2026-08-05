from keprix.tui.client import SessionItem
from keprix.tui.sessions.map import build_session_map, render_session_map
from keprix.tui.widgets.session_map import SessionMapWidget


def test_session_map_degrades_to_flat_recent_list() -> None:
    sessions = [
        SessionItem(id="s1", title="First", preview="Latest note", last_active="2026-07-13T10:00:00Z"),
        SessionItem(id="s2", title="Second"),
    ]

    nodes = build_session_map(sessions)

    assert [node.relation for node in nodes] == ["flat", "flat"]
    rendered = render_session_map(nodes)
    assert "First" in rendered
    assert "recent:" in rendered


def test_session_item_relationship_defaults_are_safe() -> None:
    first = SessionItem(id="s1", title="First")
    second = SessionItem(id="s2", title="Second")

    first.related_ids.append("s2")

    assert second.related_ids == []


def test_session_map_widget_updates_text() -> None:
    widget = SessionMapWidget("")
    widget.update_map([build_session_map([SessionItem(id="s1", title="First")])[0]])

    assert "Session map" in str(widget.render())
