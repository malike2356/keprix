# Zotero citation adapter

keprix uses Zotero as the primary reference manager for research workflows. Better BibTeX is supported for stable citation keys and text-based writing pipelines.

## Modes

| Mode | Description |
| --- | --- |
| `web` | Zotero Web API (`https://api.zotero.org`) |
| `local` | Zotero local connector (`http://127.0.0.1:23119`) |
| `file` | BibTeX or Better BibTeX import only |

API keys are stored in the encrypted vault (`category=api_key`, tag `zotero`). Only the vault item ID is persisted in `zotero_settings.json`.

## Citation objects

Imported references normalize to:

- `item_key`, `citation_key`, `title`, `authors`, `year`
- `publication`, `doi`, `url`, `abstract`
- `tags`, `collections`, `attachments`, `notes`
- `source` (`zotero_web`, `zotero_local`, `bibtex`, `better_bibtex`)

Better BibTeX `citationKey` fields override generated keys so exports stay stable.

## Literature notes

`literature_notes.py` generates structured notes with:

- Citation metadata block
- Summary, key claims, methods, findings, limitations
- Relevance to project
- Optional Obsidian draft write when a vault is configured

## Bibliography export

| Format | Output |
| --- | --- |
| `bibtex` | `.bib` entries |
| `csl-json` | CSL JSON array |
| `markdown` | Numbered reference list |
| `report` | `## Bibliography` section for reports |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/research/zotero/settings` | Connection status |
| POST | `/api/research/zotero/settings` | Connect web/local/file mode |
| POST | `/api/research/zotero/import` | Import BibTeX or Better BibTeX text |
| POST | `/api/research/zotero/sync/{project_id}` | Sync web/local library |
| GET | `/api/research/zotero/projects/{id}/citations` | List project citations |
| POST | `/api/research/zotero/projects/{id}/literature-notes` | Create literature notes |
| POST | `/api/research/zotero/projects/{id}/bibliography` | Export bibliography |

## Security and privacy

- Zotero API keys live in the vault; never returned by settings endpoints.
- `upload_attachments` defaults to false; remote attachment upload is blocked unless explicitly approved.
- Group library access follows Zotero permissions for the supplied API key.

## Related docs

- [research-workspace-architecture.md](research-workspace-architecture.md)
- [obsidian-vault-adapter.md](obsidian-vault-adapter.md)
