# Research workspace architecture

keprix provides a **Research Workspace** product surface for academic research, market research, NGO field studies, survey analysis, policy reports, and business intelligence. keprix orchestrates work through files, APIs, CLI adapters, and reproducible playbooks. It does **not** replace specialist tools.

## Data model

Every first-class research object carries:

| Field | Purpose |
| --- | --- |
| `workspace_id` | Tenant workspace scope |
| `project_id` | Research project container |
| `owner` | User or agent that created the object |
| `source_ref` | File path or URI for the underlying material |
| `provenance` | JSON lineage metadata |
| `created_at` / `updated_at` | Audit timestamps |
| `trace_id` | Cross-system trace correlation |
| `sensitivity_level` | `public`, `internal`, or `restricted` |
| `export_policy` | `allow`, `redact`, or `deny` |

### Object types

| Object | Description |
| --- | --- |
| Research project | Top-level container with question and policies |
| Source | Ingested URL, file, dataset reference, or note path |
| Citation | Bibliographic label linked to a source |
| Note | Research note (exported to Obsidian; not an Obsidian replacement) |
| Claim | Evidence-backed assertion with optional source link |
| Dataset | Registered dataset path with engine hint (see [dataset-codebook-manager.md](dataset-codebook-manager.md)) |
| Codebook | Variable dictionary metadata (stored as research object) |
| Analysis run | Queued adapter job for external stats tooling |
| Statistical output | Output artifact from an analysis run |
| Figure | Chart or image artifact |
| Report | Assembled report path |
| Evidence bundle | Named bundle of traced member objects |

Objects are stored in `research_objects` (SQLite data plane) with legacy tables for projects, sources, claims, and citations.

## Integration boundary

### keprix owns

- Project orchestration
- Source ingestion
- Evidence tracking
- Agent analysis
- Playbook execution
- Artifact store
- Report assembly
- Audit trail

### External tools own

| Tool | keprix role |
| --- | --- |
| Obsidian | Vault export; graph UX stays in Obsidian (see [obsidian-vault-adapter.md](obsidian-vault-adapter.md)) |
| Zotero | Library import adapter (see [zotero-citation-adapter.md](zotero-citation-adapter.md)) |
| PSPP | CLI adapter for statistical engine (see [pspp-runner.md](pspp-runner.md)) |
| jamovi | Bridge API and job dispatch (see [jamovi-bridge.md](jamovi-bridge.md)) |
| R / Python | CLI and analytics workspace adapters |
| Jupyter | Notebook export and handoff |
| Pandoc / Quarto | Render adapters for report output |

keprix must never embed PSPP, jamovi GUI, or Quarto rendering as a replacement product surface.

## Related keprix modules (reference, do not duplicate)

| Capability | Module | Prompt |
| --- | --- | --- |
| Document agents and cited Q&A | `src/keprix/documents/` | 69 |
| Production RAG pipelines | `src/keprix/rag_pipeline/` | 72 |
| Analytics code workspace | `src/keprix/analytics/` | 54 |
| Deep research jobs | `src/keprix/research/` | prior research plane |
| Data plane and jobs | `src/keprix/data_architecture/`, `src/keprix/jobs/` | 32, 40 |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/research/projects/boundary` | Integration boundary summary |
| GET/POST | `/api/research/projects` | List or create projects |
| GET | `/api/research/projects/{id}` | Project detail and objects |
| POST | `/api/research/projects/{id}/sources` | Register a source |
| POST | `/api/research/projects/{id}/claims` | Add evidence claim |
| POST | `/api/research/projects/{id}/datasets` | Register dataset artifact |
| POST | `/api/research/projects/{id}/analysis-runs` | Queue external-tool adapter run |
| POST | `/api/research/projects/{id}/evidence-bundles` | Build evidence bundle |
| GET | `/api/research/projects/{id}/lineage/{object_id}` | Provenance chain |
| POST | `/api/research/projects/{id}/export/obsidian` | Obsidian vault export |

## UI

`/research` provides:

- **Deep research** tab: cited web research jobs (existing pipeline)
- **Research workspace** tab: project list, project shell, adapter actions, Obsidian export

## Permissions

- `restricted` projects are readable only by `owner` (unless admin)
- `export_policy=deny` blocks Obsidian and bundle exports except for admins
- `export_policy=redact` allows owner-only export

## Provenance rule

Every artifact must trace to a registered source and/or a generated analysis run. Claims without a `source_id` are allowed but cannot join an evidence bundle that requires full lineage unless explicitly listed.
