"""Pydantic schemas for contacts API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ContactEmail(BaseModel):
    address: str
    label: str = ""
    primary: bool = False


class ContactPhone(BaseModel):
    number: str
    label: str = ""
    primary: bool = False


class ContactAddress(BaseModel):
    street: str = ""
    city: str = ""
    region: str = ""
    postal_code: str = ""
    country: str = ""
    label: str = ""


class ContactCreate(BaseModel):
    display_name: str
    given_name: str | None = None
    family_name: str | None = None
    emails: list[ContactEmail] = Field(default_factory=list)
    phones: list[ContactPhone] = Field(default_factory=list)
    addresses: list[ContactAddress] = Field(default_factory=list)
    organisation: str | None = None
    job_title: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    whatsapp: str | None = None
    telegram: str | None = None
    role: str | None = None


class ContactUpdate(BaseModel):
    display_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    emails: list[ContactEmail] | None = None
    phones: list[ContactPhone] | None = None
    addresses: list[ContactAddress] | None = None
    organisation: str | None = None
    job_title: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    whatsapp: str | None = None
    telegram: str | None = None
    role: str | None = None


class ContactOut(BaseModel):
    id: str
    display_name: str
    given_name: str | None
    family_name: str | None
    emails: list[dict[str, Any]]
    phones: list[dict[str, Any]]
    addresses: list[dict[str, Any]]
    organisation: str | None
    job_title: str | None
    notes: str | None
    photo_url: str | None
    source: str
    source_id: str | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
    editable: bool = True
    tags: list[str] = Field(default_factory=list)
    whatsapp: str | None = None
    telegram: str | None = None
    role: str | None = None


class ContactEnrichmentUpdate(BaseModel):
    tags: list[str] | None = None
    whatsapp: str | None = None
    telegram: str | None = None
    role: str | None = None


class ContactPreferencesOut(BaseModel):
    user_id: str
    confirm_before_email: bool
    confirm_before_call: bool
    read_back_draft: bool
    updated_at: datetime


class ContactPreferencesUpdate(BaseModel):
    confirm_before_email: bool | None = None
    confirm_before_call: bool | None = None
    read_back_draft: bool | None = None


class ImportSummary(BaseModel):
    added: int
    updated: int
    skipped: int
