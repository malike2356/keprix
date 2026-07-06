"""Apply approved migration manifests (Prompt 42)."""

from __future__ import annotations

from keprix.backend.migration.manifest import (
    AgentMigrationManifest,
    MigrationItem,
    MigrationItemResult,
    MigrationResult,
)
from keprix.backend.migration.store import get_migration_history_store
from keprix.memory.episodic.store import create_episodic_store
from keprix.workspace.repository import workspace_repo


class MigrationImporter:
    async def apply(
        self,
        manifest: AgentMigrationManifest,
        approved_item_ids: list[str],
        *,
        workspace_id: str,
        user_id: str,
    ) -> MigrationResult:
        results: list[MigrationItemResult] = []
        approved_set = set(approved_item_ids)
        memory_store = create_episodic_store()
        history = get_migration_history_store()

        for item in manifest.items:
            if item.id not in approved_set:
                results.append(MigrationItemResult(id=item.id, status="skipped"))
                continue
            try:
                normalized = self._normalize_item(item)
                if normalized.kind == "memory":
                    await self._import_memory(
                        normalized,
                        user_id=user_id,
                        memory_store=memory_store,
                        source_kind=manifest.source.kind,
                    )
                elif normalized.kind == "skill":
                    self._import_skill(normalized, workspace_id=workspace_id)
                elif normalized.kind in {"archive_document", "conversation_thread"}:
                    self._import_document(normalized, user_id=user_id)
                elif normalized.kind == "preference":
                    self._import_preference(normalized, user_id=user_id)
                results.append(MigrationItemResult(id=item.id, status="imported"))
            except Exception as exc:
                results.append(MigrationItemResult(id=item.id, status="failed", error=str(exc)))

        result = MigrationResult(
            total=len(manifest.items),
            imported=sum(1 for row in results if row.status == "imported"),
            skipped=sum(1 for row in results if row.status == "skipped"),
            failed=sum(1 for row in results if row.status == "failed"),
            items=results,
        )
        history.record(
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "source": manifest.source.model_dump(mode="json"),
                "summary": manifest.summary.model_dump(),
                "result": result.model_dump(),
            }
        )
        return result

    def _normalize_item(self, item: MigrationItem) -> MigrationItem:
        if item.kind == "conversation_thread":
            return item.model_copy(update={"kind": "archive_document"})
        return item

    async def _import_memory(self, item: MigrationItem, *, user_id: str, memory_store, source_kind: str) -> None:
        await memory_store.save(
            user_id,
            item.content,
            metadata={
                "tags": item.tags + ["migrated", f"from:{source_kind}"],
                "source": "migration",
            },
        )

    def _import_skill(self, item: MigrationItem, *, workspace_id: str) -> None:
        get_migration_history_store().save_skill(
            workspace_id,
            {
                "name": item.title,
                "body": item.content,
                "category": item.skill_category or "migrated",
                "status": "pending_review",
                "source": "migration",
                "tags": item.tags,
            },
        )

    def _import_document(self, item: MigrationItem, *, user_id: str) -> None:
        user = {"id": user_id}
        workspace_repo.create_document(
            user,
            title=item.title,
            content=item.content,
            format="markdown",
            tags=item.tags + ["migrated"],
        )

    def _import_preference(self, item: MigrationItem, *, user_id: str) -> None:
        workspace_repo.prefs[user_id] = {
            **workspace_repo.prefs.get(user_id, {}),
            item.title: item.content,
            "migrated": True,
        }


def preview_manifest(manifest: AgentMigrationManifest) -> str:
    lines = [
        f"Schema: {manifest.schema_version}",
        f"Source: {manifest.source.name} ({manifest.source.kind})",
        f"Items: {manifest.summary.item_count}",
        f"Warnings: {manifest.summary.warning_count}",
    ]
    for kind, count in sorted(manifest.summary.counts_by_kind.items()):
        lines.append(f"  - {kind}: {count}")
    for warning in manifest.warnings:
        lines.append(f"WARNING [{warning.severity}]: {warning.message}")
    return "\n".join(lines)
