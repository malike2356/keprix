"""Built-in sheet types and pack registry hook for extra schemas."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from keprix.sheet_preprocess.models import ColumnRole

BUILTIN_SHEET_TYPES: tuple[str, ...] = (
    "generic",
    "leads",
    "tenant_list",
    "property_data",
)

_TYPE_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("tenant_list", ("tenant", "lease", "rent", "landlord")),
    ("leads", ("lead", "contact", "enquiry", "prospect", "source", "pipeline")),
    ("property_data", ("property", "address", "bedroom", "valuation", "postcode")),
)

SheetTypeClassifier = Callable[[Sequence[object]], str | None]
SheetTypeSchemaProvider = Callable[[str], Mapping[str, Any] | None]


@dataclass
class SheetTypeRegistration:
    sheet_type: str
    markers: tuple[str, ...] = ()
    default_roles: dict[str, ColumnRole] = field(default_factory=dict)
    pack_id: str | None = None
    description: str = ""


class SheetTypeRegistry:
    """Registry for built-in and pack-provided sheet type hints."""

    def __init__(self) -> None:
        self._types: dict[str, SheetTypeRegistration] = {}
        self._classifiers: list[SheetTypeClassifier] = []
        self._schema_providers: list[SheetTypeSchemaProvider] = []
        for name in BUILTIN_SHEET_TYPES:
            markers = next((m for t, m in _TYPE_MARKERS if t == name), ())
            self.register(
                SheetTypeRegistration(
                    sheet_type=name,
                    markers=markers,
                    description=f"Built-in sheet type: {name}",
                )
            )

    def register(self, registration: SheetTypeRegistration) -> None:
        self._types[registration.sheet_type] = registration

    def register_classifier(self, classifier: SheetTypeClassifier) -> None:
        self._classifiers.append(classifier)

    def register_schema_provider(self, provider: SheetTypeSchemaProvider) -> None:
        self._schema_providers.append(provider)

    def known_types(self) -> list[str]:
        return sorted(self._types)

    def get(self, sheet_type: str) -> SheetTypeRegistration | None:
        return self._types.get(sheet_type)

    def pack_schema(self, sheet_type: str) -> Mapping[str, Any] | None:
        for provider in self._schema_providers:
            schema = provider(sheet_type)
            if schema is not None:
                return schema
        return None

    def classify(self, columns: Sequence[object]) -> str:
        for classifier in self._classifiers:
            hit = classifier(columns)
            if hit:
                return hit
        text = " ".join(str(column).strip().lower() for column in columns)
        for name, registration in self._types.items():
            if name == "generic":
                continue
            if any(marker in text for marker in registration.markers):
                return name
        for sheet_type, markers in _TYPE_MARKERS:
            if any(marker in text for marker in markers):
                return sheet_type
        return "generic"


_REGISTRY = SheetTypeRegistry()


def get_sheet_type_registry() -> SheetTypeRegistry:
    return _REGISTRY


def register_pack_sheet_type(registration: SheetTypeRegistration) -> None:
    """Hook for vertical packs to register additional sheet types."""
    get_sheet_type_registry().register(registration)


def register_pack_classifier(classifier: SheetTypeClassifier) -> None:
    get_sheet_type_registry().register_classifier(classifier)


def register_pack_schema_provider(provider: SheetTypeSchemaProvider) -> None:
    get_sheet_type_registry().register_schema_provider(provider)
