# Structured workspace memory

Prompt **258** adds structured workspace folders, deterministic `index.md`
generation, and a root `KEPRIX.md` navigation guide.

## Templates

| Template | Folders |
| --- | --- |
| `knowledge_pipeline` | `raw`, `wiki`, `outputs` |
| `property_investor` | `deals`, `tenants`, `compliance`, `reports` |
| `developer` | `specs`, `architecture`, `releases`, `reviews` |
| `client_delivery` | `clients`, `deliverables`, `feedback` |
| `executive_assistant` | `context`, `raw`, `wiki`, `outputs` |
| `blank` | none |

## API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/workspaces/templates` | List template presets |
| POST | `/api/workspaces` | Create workspace with `template_id` |
| POST | `/api/workspaces/{id}/reindex` | Regenerate all indexes or one folder |
| POST | `/api/workspaces/{id}/memory/link` | Link a workspace file into memory search |

## CLI

```bash
keprix workspace init --template knowledge_pipeline --name my-hub
keprix workspace index --name my-hub --folder wiki
keprix workspace templates
```

Indexes are deterministic and do not call a live LLM. Each generated
`KEPRIX.md` tells the agent to read index files before loading individual files.
