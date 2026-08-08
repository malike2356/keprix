# keprix - Prompt 75: Obsidian Vault Adapter and Linked Notes

> **Status (2026-07-05):** Implemented `src/keprix/research_workspace/obsidian/` (vault registry, markdown/frontmatter, backlinks, templates, safe sync, graph export), `/api/research/obsidian/*`, Obsidian UI panels, `docs/research/obsidian-vault-adapter.md`, and 13 tests.

## Context

Obsidian is valuable because it stores knowledge as local Markdown files. keprix should integrate with Obsidian through the filesystem first, then optionally through URI or plugin bridges later. keprix should not require Obsidian to be running.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/research_workspace/obsidian/
  __init__.py
  vault.py
  markdown.py
  frontmatter.py
  backlinks.py
  tags.py
  attachments.py
  templates.py
  sync.py
  graph_export.py
frontend/src/components/research/ObsidianVaultSettings.tsx
frontend/src/components/research/LinkedNotesPanel.tsx
tests/research_workspace/test_obsidian_vault.py
tests/research_workspace/test_obsidian_markdown.py
tests/research_workspace/test_obsidian_backlinks.py
docs/research/obsidian-vault-adapter.md
```

## Required Features

### Vault Registration

Allow a user to register an Obsidian vault path:

- Name.
- Local path.
- Allowed folders.
- Excluded folders.
- Attachment folder.
- Note template folder.
- Sync mode: read-only, write-draft, write-approved.

Validate that the path is inside allowed workspace storage unless the user explicitly approves an external path.

### Markdown Support

Read and write:

- Markdown body.
- YAML frontmatter.
- Wiki links.
- Markdown links.
- Tags.
- Tasks.
- Embedded attachments.
- Headings.

### Research Notes

Generate:

- Literature note.
- Source note.
- Claim note.
- Dataset note.
- Meeting note.
- Field note.
- Research summary note.

Each generated note must include provenance frontmatter:

```yaml
keprix_project_id:
keprix_source_id:
keprix_trace_id:
created_by: keprix
review_status: draft
```

### Graph Export

Export keprix relationships as Obsidian-friendly Markdown links:

- Source to claim.
- Claim to citation.
- Dataset to analysis.
- Analysis to report.

## Safety Rules

- Never overwrite user notes without approval.
- Write generated notes as drafts first.
- Keep a backup or diff for every file keprix edits.
- Respect `.gitignore` and configured excluded folders.

## Acceptance Criteria

- keprix can index an Obsidian vault without Obsidian running.
- keprix can create a draft literature note with frontmatter and backlinks.
- keprix can update only approved generated sections.
- Attachment links are preserved.
- Tests cover frontmatter, backlinks, tags, and safe write behavior.
