"""Pydantic schemas for pack gate API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PackGateConfigOut(BaseModel):
    workspace_id: str
    enabled: bool
    approver_user_id: str | None = None
    approver_email: str | None = None
    notify_on_install: bool = True
    require_changelog: bool = True


class PackGateConfigUpdate(BaseModel):
    enabled: bool = False
    approver_user_id: str | None = None
    notify_on_install: bool = True
    require_changelog: bool = True


class PackGateRecordOut(BaseModel):
    id: str
    workspace_id: str
    pack_id: str
    from_version: str | None = None
    to_version: str
    changelog_text: str | None = None
    status: str
    signed_off_by_user_id: str | None = None
    signed_off_at: str | None = None
    sign_off_note: str | None = None
    requested_at: str
    requested_by_user_id: str | None = None
    sign_off_url: str | None = None


class PackGateRecordsPage(BaseModel):
    records: list[PackGateRecordOut]
    total: int


class SignOffBody(BaseModel):
    note: str | None = None


class RejectBody(BaseModel):
    note: str = Field(min_length=1)


class RollbackBody(BaseModel):
    reason: str = Field(min_length=1)
