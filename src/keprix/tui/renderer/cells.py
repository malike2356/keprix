"""Terminal cell primitives."""

from dataclasses import dataclass

from keprix.tui.renderer.measure import measure_text


@dataclass(frozen=True)
class Cell:
    char: str
    style: str = ""
    width: int = 1
    link: str = ""
    selected: bool = False
    cursor: bool = False
    metadata_id: str = ""

    @classmethod
    def from_text(
        cls,
        char: str,
        *,
        style: str = "",
        link: str = "",
        selected: bool = False,
        cursor: bool = False,
        metadata_id: str = "",
    ) -> "Cell":
        return cls(
            char=char,
            style=style,
            width=measure_text(char),
            link=link,
            selected=selected,
            cursor=cursor,
            metadata_id=metadata_id,
        )


@dataclass(frozen=True)
class CellRow:
    cells: tuple[Cell, ...]

    @property
    def text(self) -> str:
        return "".join(cell.char for cell in self.cells)

    @property
    def width(self) -> int:
        return sum(cell.width for cell in self.cells)


def cells_from_text(text: str, *, style: str = "", metadata_id: str = "") -> CellRow:
    return CellRow(tuple(Cell.from_text(char, style=style, metadata_id=metadata_id) for char in text))


__all__ = ["Cell", "CellRow", "cells_from_text"]
