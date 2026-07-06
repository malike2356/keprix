from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Field:
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    entity: str | None = None
    values: list[str] | None = None


@dataclass
class Operation:
    name: str
    confirmation_required: bool = False


@dataclass
class Entity:
    name: str
    fields: list[Field] = field(default_factory=list)
    operations: list[Operation] = field(default_factory=list)


@dataclass
class Domain:
    name: str
    entities: list[Entity] = field(default_factory=list)
