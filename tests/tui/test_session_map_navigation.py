from keprix.tui.sessions.map import SessionMapNavigator, SessionMapNode


def test_session_map_navigator_moves_and_wraps() -> None:
    nodes = [
        SessionMapNode(id="s1", title="One"),
        SessionMapNode(id="s2", title="Two"),
        SessionMapNode(id="s3", title="Three"),
    ]
    navigator = SessionMapNavigator(nodes, selected_id="s2")

    assert navigator.selected().id == "s2"
    assert navigator.move(1).id == "s3"
    assert navigator.move(1).id == "s1"
    assert navigator.move(-1).id == "s3"


def test_session_map_navigator_selects_by_id() -> None:
    nodes = [SessionMapNode(id="s1", title="One"), SessionMapNode(id="s2", title="Two")]
    navigator = SessionMapNavigator(nodes)

    assert navigator.select("s2").title == "Two"
    assert navigator.selected().id == "s2"
    assert navigator.select("missing") is None
