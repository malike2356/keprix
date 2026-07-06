# Obsidian vault adapter

keprix integrates with Obsidian through the **filesystem first**. Obsidian does not need to be running for indexing, draft note creation, or graph export.

## Vault registration

Register a vault via `POST /api/research/obsidian/vaults`:

| Field | Purpose |
| --- | --- |
| `name` | Display label |
| `local_path` | Absolute or workspace-relative vault directory |
| `allowed_folders` | Subfolders keprix may read/write (default `.`) |
| `excluded_folders` | Skipped paths (default `.obsidian`, `.trash`) |
| `attachment_folder` | Expected attachment location |
| `template_folder` | Note templates folder |
| `sync_mode` | `read-only`, `write-draft`, or `write-approved` |
| `allow_external_path` | Approve paths outside workspace storage |

Paths must live under workspace storage unless `allow_external_path` is true.

Vault configs persist in `{workspace}/obsidian_vaults.json`.

## Markdown support

The adapter reads and writes:

- YAML frontmatter
- Wiki links (`[[note]]`)
- Markdown links
- Tags (frontmatter and inline `#tag`)
- Tasks (`- [ ]` / `- [x]`)
- Embedded attachments (`![[file.png]]`)
- Headings

## Research note templates

| Type | Use |
| --- | --- |
| `literature` | Paper or bibliography summary |
| `source` | Registered source material |
| `claim` | Evidence-backed assertion |
| `dataset` | Dataset artifact |
| `meeting` | Meeting notes |
| `field` | Field study or analysis run |
| `research_summary` | Project or report summary |

Generated notes include provenance frontmatter:

```yaml
keprix_project_id:
keprix_source_id:
keprix_trace_id:
created_by: keprix
review_status: draft
```

Draft content is wrapped in `<!-- keprix:generated:start/end -->` markers so approved updates touch only generated sections.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/research/obsidian/vaults` | List registered vaults |
| POST | `/api/research/obsidian/vaults` | Register vault |
| POST | `/api/research/obsidian/vaults/{id}/index` | Index vault (no Obsidian required) |
| POST | `/api/research/obsidian/projects/{id}/notes` | Create draft research note |
| GET | `/api/research/obsidian/projects/{id}/backlinks?vault_id=` | Project note backlinks |
| POST | `/api/research/projects/{id}/export/obsidian` | Export project graph to Markdown |

## Safety rules

- Never overwrite user-authored notes unless `sync_mode=write-approved` and the note is a keprix-generated draft.
- Draft writes create `.bak.md` and `.diff` files under `{workspace}/obsidian_backups/`.
- `.gitignore` patterns and excluded folders are respected during indexing.
- Attachment embeds are preserved when updating generated sections.

## Graph export

`graph_export.py` writes Obsidian-friendly wiki links for:

- Source to claim
- Claim to citation (literature note)
- Dataset to analysis run
- Analysis run to report

A `graph-links.md` index is included in each project export folder.

## Related docs

- [research-workspace-architecture.md](research-workspace-architecture.md) (Prompt 74)
- Obsidian skill: `src/keprix/skills/note-taking/obsidian/SKILL.md`
