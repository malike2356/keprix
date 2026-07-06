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


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    format: str | None = None
    tags: list[str] | None = None


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
    url: str
    username: str
    vault_item_id: str | None = None


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
