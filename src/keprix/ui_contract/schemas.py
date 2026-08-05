"""Pydantic schemas for UI contract payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UiContractResponse(BaseModel):
    product: str = "Keprix"
    terminology_version: str = "1"
    navigation: dict[str, Any]
    installed_apps: list[dict[str, Any]] = Field(default_factory=list)
    statuses: dict[str, dict[str, str]]
    actions: list[dict[str, Any]]
    approvals: dict[str, Any]
    empty_states: dict[str, dict[str, str]]
    errors: dict[str, str]
    forms: dict[str, list[dict[str, str]]] = Field(default_factory=dict)
    tables: dict[str, list[dict[str, str]]] = Field(default_factory=dict)
    agent: dict[str, Any] = Field(default_factory=dict)
    workspace: dict[str, Any] = Field(default_factory=dict)
    feature_flags: dict[str, bool] = Field(default_factory=dict)
