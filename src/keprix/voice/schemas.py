"""Pydantic schemas for voice wake HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WakeWordRoutingConfigOut(BaseModel):
    version: int = 1
    default_target: dict[str, Any] = Field(default_factory=lambda: {"mode": "current"})
    device_targets: dict[str, dict[str, Any]] = Field(default_factory=dict)


class WakeWordsOut(BaseModel):
    triggers: list[str]
    routing: WakeWordRoutingConfigOut


class WakeWordsUpdate(BaseModel):
    triggers: list[str] = Field(default_factory=list)


class WakeWordRoutingUpdate(BaseModel):
    version: int = 1
    default_target: dict[str, Any] = Field(default_factory=lambda: {"mode": "current"})
    device_targets: dict[str, dict[str, Any]] = Field(default_factory=dict)


class NodeWakeStatusOut(BaseModel):
    node_id: str
    platform: str
    wake_enabled: bool
    permission_granted: bool
    last_seen_at: float
    wake_detection_available: bool


class NodeWakeStatusList(BaseModel):
    nodes: list[NodeWakeStatusOut]
