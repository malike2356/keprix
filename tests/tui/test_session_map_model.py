from keprix.tui.client import SessionItem
from keprix.tui.sessions.map import build_session_map, render_session_map


def test_session_map_renders_relationship_types() -> None:
    sessions = [
        SessionItem(id="s1", title="Current", preview="Working now"),
        SessionItem(id="s2", title="Pinned", pinned=True),
        SessionItem(id="s3", title="Forked", forked_from="s1"),
        SessionItem(id="s4", title="Resumed", resumed_from="s1"),
        SessionItem(id="s5", title="Related", related_ids=["s1"]),
    ]

    nodes = build_session_map(sessions, current_session_id="s1")

    assert [node.relation for node in nodes] == ["current", "pinned", "forked", "resumed", "related"]
    text = render_session_map(nodes, selected_id="s1")
    assert "Session map" in text
    assert "> Current" in text
    assert "pinned:" in text
    assert "fork:" in text
    assert "resume:" in text
    assert "related:" in text


def test_session_map_marks_search_matches() -> None:
    sessions = [
        SessionItem(id="s1", title="Normal"),
        SessionItem(id="s2", title="Client recovery", preview="Invoice thread"),
    ]

    nodes = build_session_map(sessions, query="invoice")

    assert nodes[1].relation == "search"
