"""Viewport model exports."""

from keprix.tui.viewport import ViewportState


def stable_append_viewport(state: ViewportState, appended_lines: int) -> ViewportState:
    state.content_height += max(0, appended_lines)
    if state.auto_scroll or state.at_bottom:
        state.scroll_to_bottom()
    return state


def stable_resize_viewport(state: ViewportState, height: int, content_height: int) -> ViewportState:
    state.update_dimensions(viewport_height=height, content_height=content_height)
    return state


__all__ = ["ViewportState", "stable_append_viewport", "stable_resize_viewport"]
