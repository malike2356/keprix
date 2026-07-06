"""Visible page element mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.browser.drivers import PageSnapshot


@dataclass
class BrowserElement:
    element_id: str
    label: str
    role: str = "generic"
    text: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    iframe_path: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.element_id,
            "element_id": self.element_id,
            "label": self.label,
            "role": self.role,
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "iframe_path": list(self.iframe_path),
            "attributes": dict(self.attributes),
        }


def element_map_from_snapshot(snapshot: PageSnapshot) -> list[BrowserElement]:
    elements: list[BrowserElement] = []
    for index, item in enumerate(snapshot.elements):
        iframe_path = list(item.get("iframe_path") or [])
        elements.append(
            BrowserElement(
                element_id=str(item.get("id") or item.get("element_id") or f"el-{index}"),
                label=str(item.get("label") or item.get("name") or item.get("text") or ""),
                role=str(item.get("role") or "generic"),
                text=str(item.get("text") or ""),
                x=int(item.get("x") or 0),
                y=int(item.get("y") or 0),
                width=int(item.get("width") or 0),
                height=int(item.get("height") or 0),
                iframe_path=iframe_path,
                attributes=dict(item.get("attributes") or {}),
            )
        )
    return elements


def snapshot_with_iframe_elements(url: str, *, iframe_path: list[str] | None = None) -> PageSnapshot:
    """Helper for tests: build a snapshot with iframe-scoped elements."""
    path = iframe_path or ["iframe#main"]
    return PageSnapshot(
        url=url,
        title="Iframe page",
        text="Content inside iframe",
        elements=[
            {
                "id": "email",
                "role": "textbox",
                "label": "Email",
                "iframe_path": path,
            },
            {
                "id": "save",
                "role": "button",
                "label": "Save",
                "iframe_path": path,
            },
        ],
    )
