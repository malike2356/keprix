"""Codebook and variable metadata models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class VariableDefinition:
    name: str
    label: str = ""
    var_type: str = "string"
    measurement_level: str = "nominal"
    value_labels: dict[str, str] = field(default_factory=dict)
    missing_codes: list[str] = field(default_factory=list)
    derived_expression: str | None = None
    source_column: str | None = None
    validation_rules: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VariableDefinition:
        return cls(
            name=str(data["name"]),
            label=str(data.get("label") or ""),
            var_type=str(data.get("var_type") or "string"),
            measurement_level=str(data.get("measurement_level") or "nominal"),
            value_labels={str(k): str(v) for k, v in (data.get("value_labels") or {}).items()},
            missing_codes=[str(code) for code in (data.get("missing_codes") or [])],
            derived_expression=data.get("derived_expression"),
            source_column=data.get("source_column"),
            validation_rules=[str(rule) for rule in (data.get("validation_rules") or [])],
            notes=str(data.get("notes") or ""),
        )


@dataclass
class Codebook:
    dataset_id: str
    version_id: str
    variables: list[VariableDefinition] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version_id": self.version_id,
            "notes": self.notes,
            "variables": [variable.to_dict() for variable in self.variables],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Codebook:
        return cls(
            dataset_id=str(data["dataset_id"]),
            version_id=str(data["version_id"]),
            notes=str(data.get("notes") or ""),
            variables=[VariableDefinition.from_dict(item) for item in data.get("variables") or []],
        )

    def get_variable(self, name: str) -> VariableDefinition | None:
        for variable in self.variables:
            if variable.name == name:
                return variable
        return None
