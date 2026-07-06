"""Browser world model."""

from __future__ import annotations

from typing import Any

from keprix.browser.drivers import PageSnapshot
from keprix.browser.element_map import element_map_from_snapshot


def build_world_state(snapshot: PageSnapshot, objective: str) -> dict[str, Any]:
    elements = [item.to_dict() for item in element_map_from_snapshot(snapshot)]
    return {
        "objective": objective,
        "url": snapshot.url,
        "title": snapshot.title,
        "visible_elements": elements,
        "summary": snapshot.text[:500],
        "next_instruction": _suggest_instruction(elements, objective),
    }


def _suggest_instruction(elements: list[dict[str, Any]], objective: str) -> str:
    if "search" in objective.lower() and elements:
        return "Fill the search field, then click submit."
    return "Read the current page and identify the next safe action."
