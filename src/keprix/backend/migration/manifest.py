"""Agent migration manifest schemas (Prompt 42)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _count_by_kind(items: list["MigrationItem"]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind] = counts.get(item.kind, 0) + 1
    return counts


class MigrationSource(BaseModel):
    name: str
    kind: str
    exported_at: datetime | None = None
    version: str | None = None


class MigrationSummary(BaseModel):
    item_count: int
    counts_by_kind: dict[str, int]
    warning_count: int


class MigrationWarning(BaseModel):
    item_index: int | None
    message: str
    severity: Literal["info", "warn", "error"]


class MigrationItem(BaseModel):
    kind: Literal["memory", "skill", "conversation_thread", "archive_document", "preference"]
    id: str
    title: str
    content: str
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    source_path: str | None = None
    memory_confidence: float | None = None
    skill_category: str | None = None
    thread_date: datetime | None = None


class AgentMigrationManifest(BaseModel):
    schema_version: Literal["agent-migration.v1"]
    generated_at: datetime
    source: MigrationSource
    summary: MigrationSummary
    warnings: list[MigrationWarning] = Field(default_factory=list)
    items: list[MigrationItem]

    def validate_integrity(self) -> list[str]:
        errors: list[str] = []
        if self.summary.item_count != len(self.items):
            errors.append(
                f"summary.item_count ({self.summary.item_count}) does not match items length ({len(self.items)})"
            )
        for kind, expected_count in self.summary.counts_by_kind.items():
            actual = sum(1 for item in self.items if item.kind == kind)
            if actual != expected_count:
                errors.append(f"counts_by_kind[{kind}] says {expected_count} but {actual} found")
        return errors


def build_manifest(
    *,
    source: MigrationSource,
    items: list[MigrationItem],
    warnings: list[MigrationWarning] | None = None,
) -> AgentMigrationManifest:
    warning_rows = warnings or []
    return AgentMigrationManifest(
        schema_version="agent-migration.v1",
        generated_at=datetime.now(timezone.utc),
        source=source,
        summary=MigrationSummary(
            item_count=len(items),
            counts_by_kind=_count_by_kind(items),
            warning_count=len(warning_rows),
        ),
        warnings=warning_rows,
        items=items,
    )


class MigrationItemResult(BaseModel):
    id: str
    status: Literal["imported", "skipped", "failed"]
    error: str | None = None


class MigrationResult(BaseModel):
    total: int
    imported: int
    skipped: int
    failed: int
    items: list[MigrationItemResult]
