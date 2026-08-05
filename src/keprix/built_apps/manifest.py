"""Built app manifest loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class BuiltAppNavItem(BaseModel):
    id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    href: str = Field(..., min_length=1)
    icon: str | None = None
    badge: str | int | None = None


class BuiltAppNavigation(BaseModel):
    style: Literal["sections", "sub_rail", "tabs_only"] = "sections"
    items: list[BuiltAppNavItem] = Field(default_factory=list)


class BuiltAppBrand(BaseModel):
    primary_color: str | None = None


class BuiltAppManifest(BaseModel):
    id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    description: str | None = None
    entry: str = Field(..., min_length=1)
    icon: str | None = "apps"
    version: str | None = None
    brand: BuiltAppBrand | None = None
    navigation: BuiltAppNavigation | None = None

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("id may contain only letters, numbers, hyphens, and underscores")
        return value

    @model_validator(mode="after")
    def validate_routes(self) -> "BuiltAppManifest":
        expected_prefix = f"/apps/{self.id}"
        if not self.entry.startswith(expected_prefix):
            raise ValueError(f"entry must start with {expected_prefix}")
        for item in self.navigation.items if self.navigation else []:
            if not item.href.startswith(expected_prefix):
                raise ValueError(f"navigation href must start with {expected_prefix}")
        return self


def load_built_app_manifest(path: Path) -> BuiltAppManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("built_app.yaml must contain a mapping")
    return BuiltAppManifest.model_validate(raw)
