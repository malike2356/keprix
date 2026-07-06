"""SDK type definitions shared by backend routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FieldSpec(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    entity: str | None = None
    values: list[str] | None = None


class OperationSpec(BaseModel):
    name: str
    confirmation_required: bool = False


class EntitySpec(BaseModel):
    name: str
    fields: list[FieldSpec] = Field(default_factory=list)
    operations: list[OperationSpec] = Field(default_factory=list)


class DomainSchema(BaseModel):
    name: str
    entities: list[EntitySpec] = Field(default_factory=list)


class ActionStepModel(BaseModel):
    entity: str
    operation: str
    fields: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    confirmation_required: bool = False
    confidence: float = 0.0
    result: Any = None


class ActionPlanModel(BaseModel):
    plan_id: str | None = None
    user_input: str
    session_id: str | None = None
    steps: list[ActionStepModel]
    requires_confirmation: bool = False
    confirmation_prompt: str = ""


class RegisterAppRequest(BaseModel):
    name: str
    version: str = "1.0.0"
    domain: DomainSchema
    webhook_url: str | None = None


class ExecuteRequest(BaseModel):
    app_id: str
    message: str
    session_id: str | None = None
    user_id: str | None = None


class ConfirmRequest(BaseModel):
    plan_id: str
    confirmed: bool = True
