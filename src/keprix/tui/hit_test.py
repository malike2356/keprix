"""Hit testing primitives for terminal coordinates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True)
class Region:
    x: int
    y: int
    width: int
    height: int
    id: str = ""

    def contains(self, point: Point) -> bool:
        return self.x <= point.x < self.x + self.width and self.y <= point.y < self.y + self.height


class HitMap:
    def __init__(self) -> None:
        self._regions: list[Region] = []

    def add(self, region: Region) -> None:
        self._regions.append(region)

    def clear(self) -> None:
        self._regions.clear()

    def hit(self, point: Point) -> Region | None:
        for region in reversed(self._regions):
            if region.contains(point):
                return region
        return None

