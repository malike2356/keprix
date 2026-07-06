"""Support API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TicketCategory = Literal[
    "installation",
    "provider_setup",
    "channel",
    "billing",
    "data_import",
    "failed_job",
    "security",
    "lost_admin",
    "backup_restore",
    "bug",
    "feature_request",
]

HandoffPrivacy = Literal["minimal", "standard"]


class CreateTicketBody(BaseModel):
    category: TicketCategory
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=3, max_length=8000)
    attach_diagnostics: bool = False


class UpdateChecklistBody(BaseModel):
    item_id: str
    completed: bool


class CreateIncidentBody(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    summary: str = Field(..., min_length=3, max_length=4000)


class IncidentUpdateBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    status: Literal["investigating", "identified", "monitoring", "resolved"] | None = None


class HandoffBody(BaseModel):
    category: TicketCategory
    summary: str = Field(..., min_length=3, max_length=2000)
    privacy: HandoffPrivacy = "minimal"
    contact_email: str | None = None


class TicketResponse(BaseModel):
    id: str
    category: str
    subject: str
    description: str
    status: str
    created_at: str
    diagnostics_attached: bool


class ChecklistItemResponse(BaseModel):
    id: str
    label: str
    completed: bool
    category: str


class IncidentResponse(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    summary: str
    started_at: str
    resolved_at: str | None = None
    updates: list[dict[str, Any]] = Field(default_factory=list)
    public_post: str | None = None
