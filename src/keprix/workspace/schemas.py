"""Workspace entity schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = "Untitled"
    content: str = ""
    format: str = "markdown"
    tags: list[str] = Field(default_factory=list)
    folder: str = ""
    is_favorite: bool = False


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    format: str | None = None
    tags: list[str] | None = None
    folder: str | None = None
    is_favorite: bool | None = None


class DocumentAIEdit(BaseModel):
    instruction: str


class NoteCreate(BaseModel):
    title: str = ""
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    is_pinned: bool = False


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    is_pinned: bool | None = None


class NoteSearch(BaseModel):
    query: str
    limit: int = 20


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "todo"
    priority: str = "normal"
    due_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    agent_scheduled: bool = False


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_at: datetime | None = None
    tags: list[str] | None = None


class TaskReorder(BaseModel):
    order: list[str]


class CalendarEventCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    recurrence: str | None = None
    reminders: list[int] = Field(default_factory=lambda: [15])


class CalendarEventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    recurrence: str | None = None
    reminders: list[int] | None = None


class CaldavSourceCreate(BaseModel):
    name: str
    provider: str = "caldav"
    url: str = ""
    username: str = ""
    password: str | None = None
    vault_item_id: str | None = None
    sync_direction: str = "bidirectional"
    calendar_href: str | None = None
    calendar_name: str | None = None
    push_local_events: bool = True
    enabled: bool = True
    pull_past_days: int = 90
    pull_future_days: int = 365
    auto_sync: bool = True
    sync_interval_minutes: int = 15


class CaldavSourceUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    url: str | None = None
    username: str | None = None
    password: str | None = None
    vault_item_id: str | None = None
    sync_direction: str | None = None
    calendar_href: str | None = None
    calendar_name: str | None = None
    push_local_events: bool | None = None
    enabled: bool | None = None
    pull_past_days: int | None = None
    pull_future_days: int | None = None
    auto_sync: bool | None = None
    sync_interval_minutes: int | None = None


class SessionRename(BaseModel):
    title: str


class PresetCreate(BaseModel):
    name: str
    system_prompt: str
    description: str = ""


class PresetUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    description: str | None = None


class AssistantCreate(BaseModel):
    name: str
    system_prompt: str
    model: str = "gpt-4.1-mini"
    tools: list[str] = Field(default_factory=list)


class AssistantUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    language: str | None = None


class PrefsUpdate(BaseModel):
    theme: str | None = None
    font_size: str | None = None
    layout_density: str | None = None
    active_preset_id: str | None = None
