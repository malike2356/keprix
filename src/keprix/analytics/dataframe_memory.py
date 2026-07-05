"""DataFrame schema memory without storing raw sensitive data in logs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DataFrameSchema:
    name: str
    columns: dict[str, str]
    row_count: int | None = None
    source: str = "memory"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": dict(self.columns),
            "row_count": self.row_count,
            "source": self.source,
            "notes": list(self.notes),
        }


class DataFrameMemory:
    def __init__(self) -> None:
        self._schemas: dict[str, DataFrameSchema] = {}
        self._data: dict[str, list[dict[str, Any]]] = {}

    def remember_records(self, name: str, records: list[dict[str, Any]], *, source: str = "upload") -> DataFrameSchema:
        columns: dict[str, str] = {}
        for record in records:
            for key, value in record.items():
                columns.setdefault(key, type(value).__name__)
        schema = DataFrameSchema(
            name=name,
            columns=columns,
            row_count=len(records),
            source=source,
        )
        self._schemas[name] = schema
        self._data[name] = [dict(record) for record in records]
        return schema

    def remember_schema(self, schema: DataFrameSchema) -> None:
        self._schemas[schema.name] = schema

    def get_schema(self, name: str) -> DataFrameSchema | None:
        return self._schemas.get(name)

    def get_records(self, name: str) -> list[dict[str, Any]]:
        return [dict(record) for record in self._data.get(name, [])]

    def list_schemas(self) -> list[DataFrameSchema]:
        return list(self._schemas.values())
