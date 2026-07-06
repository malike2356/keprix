"""Pydantic schemas for hub API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InstallPackBody(BaseModel):
    name: str
    version: str | None = None
    approved: bool = False


class DisablePackBody(BaseModel):
    name: str


class RollbackBody(BaseModel):
    name: str
    version: str | None = None


class PackSummary(BaseModel):
    name: str
    version: str
    type: str
    author: str
    license: str
    description: str = ""
    risk_level: str = "low"
    trust_label: str = "community"
    review_score: float | None = None
    installed: bool = False
    enabled: bool = True
    source: str = "local"


class PackListResponse(BaseModel):
    packs: list[PackSummary]
    templates: list[PackSummary] = Field(default_factory=list)
    connectors: list[PackSummary] = Field(default_factory=list)


class InstallResponse(BaseModel):
    status: str
    pack: dict[str, Any] | None = None
    message: str = ""
