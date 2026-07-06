"""World model tests."""

from keprix.browser.drivers import StubBrowserDriver
from keprix.browser.element_map import element_map_from_snapshot, snapshot_with_iframe_elements
from keprix.browser.world_model import build_world_state


def test_build_world_state_includes_objective() -> None:
    snapshot = StubBrowserDriver().navigate("https://example.com")
    state = build_world_state(snapshot, "search the site")
    assert state["objective"] == "search the site"
    assert state["url"] == "https://example.com"


def test_element_map_preserves_iframe_path() -> None:
    snapshot = snapshot_with_iframe_elements("https://example.com/form")
    elements = element_map_from_snapshot(snapshot)
    assert elements[0].iframe_path == ["iframe#main"]
    state = build_world_state(snapshot, "fill form")
    assert state["visible_elements"][0]["iframe_path"] == ["iframe#main"]
