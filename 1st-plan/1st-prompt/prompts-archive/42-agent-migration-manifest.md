# keprix - Prompt 42: Agent Migration Manifest

## Context

Reference: `planning/agents-to-adopt/odysseus/docs/agent-migration.md` and `planning/agents-to-adopt/odysseus/companion/`.

When a user arrives on keprix from another agent system (Hermes, OpenClaw, ChatGPT, a folder of Markdown notes), there is currently no defined path for bringing their state across. They lose their memory, skills, preferences, and conversation history. This is a user acquisition problem: the friction of starting from scratch discourages switching.

The key design insight from Odysseus is that a migration must not blindly import everything as memory. Durable memory should stay compact and useful. The correct separation is:

- **Memory candidates**: short facts and preferences, reviewed before committing to the memory store.
- **Archive documents**: long notes, logs, session transcripts - imported into the document store for search and later extraction, not into memory directly.
- **Skills**: exported skill definitions from the source agent, reviewable before install.
- **Conversation threads**: optional archive import, not replayed as active context.

The migration is source-neutral. Each source agent has its own adapter that produces a normalized `agent-migration.v1` manifest. keprix only needs to understand the manifest format, not every upstream agent's internal schema.

---

## File Structure

```
keprix/backend/migration/
    __init__.py
    manifest.py         - manifest schema, validation, preview
    importer.py         - applies an approved manifest to keprix state
    adapters/
        __init__.py
        hermes.py       - reads hermes-agent export format
        openclaw.py     - reads openclaw export format
        markdown.py     - reads a folder of Markdown notes
        generic.py      - generic JSON/text adapter for unknown sources
    routes.py           - API endpoints
    cli.py              - keprix migrate CLI command

keprix/tests/migration/
    test_manifest.py
    test_importer.py
    test_adapters.py

keprix/ui/web/src/app/(workspace)/migrate/
    page.tsx            - migration wizard UI
    preview/page.tsx    - manifest preview before applying
```

---

## Manifest Format

Version string is `agent-migration.v1`. The format is intentionally source-neutral so adapters for new agents can be written without changing the importer.

```python
# keprix/backend/migration/manifest.py

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class MigrationSource(BaseModel):
    name: str               # e.g. "hermes-agent", "openclaw", "markdown-notes"
    kind: str               # 'hermes' | 'openclaw' | 'markdown' | 'generic'
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
    id: str                 # source-side identifier
    title: str              # human-readable label for the preview UI
    content: str            # the actual content (memory text, skill body, document text, etc.)
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    source_path: str | None = None   # original file path if from filesystem
    # For memory candidates:
    memory_confidence: float | None = None   # 0-1; adapter's guess at how likely this is a real fact vs noise
    # For skills:
    skill_category: str | None = None
    # For conversation threads:
    thread_date: datetime | None = None

class AgentMigrationManifest(BaseModel):
    schema_version: Literal["agent-migration.v1"]
    generated_at: datetime
    source: MigrationSource
    summary: MigrationSummary
    warnings: list[MigrationWarning] = Field(default_factory=list)
    items: list[MigrationItem]

    def validate_integrity(self) -> list[str]:
        """Returns a list of validation errors. Empty = valid."""
        errors = []
        if self.summary.item_count != len(self.items):
            errors.append(f"summary.item_count ({self.summary.item_count}) does not match items length ({len(self.items)})")
        for kind, expected_count in self.summary.counts_by_kind.items():
            actual = sum(1 for item in self.items if item.kind == kind)
            if actual != expected_count:
                errors.append(f"counts_by_kind[{kind}] says {expected_count} but {actual} found")
        return errors
```

---

## Adapters

Each adapter reads a source format and returns an `AgentMigrationManifest`. Adapters are stateless converters.

```python
# keprix/backend/migration/adapters/hermes.py

import json
from pathlib import Path
from keprix.backend.migration.manifest import AgentMigrationManifest, MigrationItem, MigrationSource, MigrationSummary, MigrationWarning

class HermesAdapter:
    """
    Reads a Hermes agent export directory.

    Hermes export structure (produced by `hermes export`):
        export/
            memory.json         - list of {key, value, created_at}
            skills.json         - list of {name, body, category}
            conversations/
                {id}.json       - conversation thread objects
    """

    def convert(self, export_dir: Path) -> AgentMigrationManifest:
        items: list[MigrationItem] = []
        warnings: list[MigrationWarning] = []

        # Memory
        memory_path = export_dir / "memory.json"
        if memory_path.exists():
            memories = json.loads(memory_path.read_text())
            for i, mem in enumerate(memories):
                items.append(MigrationItem(
                    kind="memory",
                    id=f"memory-{i}",
                    title=mem.get("key", f"Memory {i}"),
                    content=mem.get("value", ""),
                    memory_confidence=0.9,
                ))
        else:
            warnings.append(MigrationWarning(item_index=None, message="memory.json not found", severity="warn"))

        # Skills
        skills_path = export_dir / "skills.json"
        if skills_path.exists():
            skills = json.loads(skills_path.read_text())
            for i, skill in enumerate(skills):
                items.append(MigrationItem(
                    kind="skill",
                    id=f"skill-{i}",
                    title=skill.get("name", f"Skill {i}"),
                    content=skill.get("body", ""),
                    skill_category=skill.get("category"),
                ))

        # Conversations (imported as archive documents, not active memory)
        conv_dir = export_dir / "conversations"
        if conv_dir.exists():
            for conv_file in sorted(conv_dir.glob("*.json")):
                try:
                    conv = json.loads(conv_file.read_text())
                    items.append(MigrationItem(
                        kind="archive_document",
                        id=f"conv-{conv_file.stem}",
                        title=f"Conversation {conv_file.stem}",
                        content=self._flatten_conversation(conv),
                        source_path=str(conv_file),
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    warnings.append(MigrationWarning(item_index=None,
                                                      message=f"Could not parse {conv_file.name}: {e}",
                                                      severity="warn"))

        return AgentMigrationManifest(
            schema_version="agent-migration.v1",
            generated_at=__import__("datetime").datetime.utcnow(),
            source=MigrationSource(name="hermes-agent", kind="hermes"),
            summary=MigrationSummary(
                item_count=len(items),
                counts_by_kind=self._count_by_kind(items),
                warning_count=len(warnings),
            ),
            warnings=warnings,
            items=items,
        )

    def _flatten_conversation(self, conv: dict) -> str:
        messages = conv.get("messages", [])
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("content", "")
            if isinstance(text, list):
                text = " ".join(p.get("text", "") for p in text if isinstance(p, dict))
            lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def _count_by_kind(self, items: list[MigrationItem]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            counts[item.kind] = counts.get(item.kind, 0) + 1
        return counts
```

```python
# keprix/backend/migration/adapters/markdown.py

class MarkdownAdapter:
    """
    Reads a directory of Markdown files (e.g. an Obsidian vault, a notes folder).
    All files are imported as archive_documents.
    Files whose content is short (under 300 chars) and looks like a fact statement
    are additionally offered as memory candidates.
    """

    MEMORY_CANDIDATE_MAX_CHARS = 300
    MEMORY_CANDIDATE_PATTERNS = [
        r"^(I|My|The user|User) (prefer|use|like|hate|always|never|am|is|was)",
        r"^(Name|Email|Company|Role|Location|Language):",
    ]

    def convert(self, notes_dir: Path) -> AgentMigrationManifest:
        import re
        items: list[MigrationItem] = []
        md_files = sorted(notes_dir.rglob("*.md"))

        for i, path in enumerate(md_files):
            try:
                text = path.read_text(encoding="utf-8", errors="replace").strip()
                if not text:
                    continue
                item = MigrationItem(
                    kind="archive_document",
                    id=f"md-{i}",
                    title=path.stem,
                    content=text,
                    source_path=str(path.relative_to(notes_dir)),
                )
                items.append(item)

                # Also offer as memory candidate if short and matches patterns
                if len(text) <= self.MEMORY_CANDIDATE_MAX_CHARS:
                    for pattern in self.MEMORY_CANDIDATE_PATTERNS:
                        if re.search(pattern, text, re.IGNORECASE):
                            items.append(MigrationItem(
                                kind="memory",
                                id=f"md-mem-{i}",
                                title=f"Memory candidate from {path.stem}",
                                content=text,
                                memory_confidence=0.5,
                                source_path=str(path.relative_to(notes_dir)),
                            ))
                            break
            except OSError:
                pass

        return AgentMigrationManifest(
            schema_version="agent-migration.v1",
            generated_at=__import__("datetime").datetime.utcnow(),
            source=MigrationSource(name="markdown-notes", kind="markdown"),
            summary=MigrationSummary(
                item_count=len(items),
                counts_by_kind=self._count_by_kind(items),
                warning_count=0,
            ),
            warnings=[],
            items=items,
        )

    def _count_by_kind(self, items): ...  # same as hermes adapter
```

---

## Importer

The importer applies an approved manifest. It is called after the user has reviewed the preview and selected which items to import.

```python
# keprix/backend/migration/importer.py

class MigrationImporter:

    async def apply(
        self,
        manifest: AgentMigrationManifest,
        approved_item_ids: list[str],
        workspace_id: str,
        user_id: str,
    ) -> MigrationResult:
        """
        Applies the approved items from a manifest.

        approved_item_ids: IDs of items the user checked in the preview UI.
        Items not in this list are skipped silently.

        Returns a MigrationResult with per-item outcomes.
        """
        results = []
        approved_set = set(approved_item_ids)

        for item in manifest.items:
            if item.id not in approved_set:
                results.append(MigrationItemResult(id=item.id, status="skipped"))
                continue

            try:
                if item.kind == "memory":
                    await self._import_memory(item, workspace_id, user_id)
                elif item.kind == "skill":
                    await self._import_skill(item, workspace_id)
                elif item.kind in ("archive_document", "conversation_thread"):
                    await self._import_document(item, workspace_id)
                elif item.kind == "preference":
                    await self._import_preference(item, workspace_id, user_id)
                results.append(MigrationItemResult(id=item.id, status="imported"))
            except Exception as exc:
                results.append(MigrationItemResult(id=item.id, status="failed", error=str(exc)))

        return MigrationResult(
            total=len(manifest.items),
            imported=sum(1 for r in results if r.status == "imported"),
            skipped=sum(1 for r in results if r.status == "skipped"),
            failed=sum(1 for r in results if r.status == "failed"),
            items=results,
        )

    async def _import_memory(self, item: MigrationItem, workspace_id: str, user_id: str) -> None:
        """Writes to the memory store (Prompt 06). Tags with 'migrated'."""
        await memory_store.save(
            workspace_id=workspace_id,
            user_id=user_id,
            content=item.content,
            tags=item.tags + ["migrated", f"from:{item.source_path or 'unknown'}"],
            source="migration",
        )

    async def _import_skill(self, item: MigrationItem, workspace_id: str) -> None:
        """Writes to the skill library (Prompt 07). Status = 'pending_review'."""
        await skill_store.create(
            workspace_id=workspace_id,
            name=item.title,
            body=item.content,
            category=item.skill_category or "migrated",
            status="pending_review",  # never auto-activates a migrated skill
            source="migration",
        )

    async def _import_document(self, item: MigrationItem, workspace_id: str) -> None:
        """Writes to the document store (Prompt 10)."""
        await document_store.create(
            workspace_id=workspace_id,
            title=item.title,
            content=item.content,
            tags=item.tags + ["migrated"],
            source="migration",
        )
```

---

## CLI Command

```bash
# Produce a manifest from a source
keprix migrate from hermes --export-dir ~/hermes-export --out migration.json
keprix migrate from openclaw --export-dir ~/openclaw-export --out migration.json
keprix migrate from markdown --notes-dir ~/Documents/notes --out migration.json

# Preview the manifest before applying
keprix migrate preview migration.json

# Apply (interactive: shows preview, prompts for confirmation)
keprix migrate apply migration.json

# Apply non-interactively (CI or scripted setup)
keprix migrate apply migration.json --approve-all --kinds memory,skill
keprix migrate apply migration.json --approve-ids mem-0,mem-1,skill-3
```

---

## API Endpoints

```
POST   /api/migration/parse
       Multipart: source (hermes|openclaw|markdown|generic), file or dir zip
       Returns: AgentMigrationManifest (preview; nothing is written yet)

POST   /api/migration/validate
       Body: { manifest: AgentMigrationManifest }
       Returns: { valid: bool, errors: string[] }

POST   /api/migration/apply
       Body: { manifest: AgentMigrationManifest, approved_item_ids: string[], workspace_id }
       Returns: MigrationResult

GET    /api/migration/history
       Returns: list of past migrations for this workspace (date, source, counts)
```

---

## Migration Wizard UI

`/migrate`

**Step 1 - Source selection:** Choose source type (Hermes, OpenClaw, Markdown folder, Generic JSON). Upload export zip or select directory.

**Step 2 - Parse and preview:** Parse the upload into a manifest. Show summary counts by kind. Show warnings. List all items in a table: checkbox, kind badge, title, confidence (for memory candidates), content preview on hover.

**Step 3 - Review and select:** User checks/unchecks items. Memory candidates with `memory_confidence < 0.6` are unchecked by default. Skills are unchecked by default (require explicit opt-in). Archive documents are checked by default.

**Step 4 - Apply:** Run the importer against the approved set. Show per-item results. Failures are highlighted with the error message. Offer to retry failed items.

**Post-migration:** Imported memories appear in the memory review queue (Prompt 06) for the user to confirm or discard. Imported skills appear in the skill library with `pending_review` status.

---

## Acceptance Criteria

- `HermesAdapter.convert(export_dir)` returns a valid manifest when `memory.json` and `skills.json` are present.
- `MarkdownAdapter.convert(notes_dir)` returns archive_document items for all `.md` files and memory candidates for short files matching the patterns.
- `manifest.validate_integrity()` returns errors when `summary.item_count` does not match `len(items)`.
- `MigrationImporter.apply(manifest, approved_ids, ...)` imports only approved items and skips all others.
- Imported skills always have `status = "pending_review"` - never `active`.
- Imported memories are tagged `["migrated", "from:<source>"]`.
- `POST /api/migration/parse` returns a 422 if the uploaded file cannot be parsed by the selected adapter.
- `POST /api/migration/apply` is idempotent: importing the same manifest twice does not crash, but may produce duplicate memory entries (documented limitation; deduplication is a future enhancement).
- The CLI `keprix migrate preview` prints a human-readable summary with item counts and warnings to stdout.
- Conversation threads are always imported as archive_documents, never as active memory, regardless of adapter or user selection.
