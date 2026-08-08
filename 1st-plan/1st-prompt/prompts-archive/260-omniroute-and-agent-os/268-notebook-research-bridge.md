# Keprix - Prompt 268: Notebook research bridge

**Series:** Chase five tools adoption **267-272**.  
**Master reference:** `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

A **NotebookLM-style research bridge**: optional sidecar/MCP integration plus a native **Quick Notebook** depth on existing `/research` (Chase "NotebookLM CLI" pattern).

Two tiers:

| Tier | Behavior |
| --- | --- |
| **Native Quick Notebook** | Keprix-only: upload/paste sources, synthesize grounded report without external NotebookLM |
| **External bridge** | Connect NotebookLM CLI or MCP when operator configures credentials |

Research depth selector on `/research`:

| Depth | Engine |
| --- | --- |
| `web` | Existing SearXNG / web research (default) |
| `notebook` | Native Quick Notebook |
| `notebook-external` | External bridge when configured |

**Non-goals:**

- NotebookLM as required core engine
- Storing Google account tokens in repo
- Replacing Deep Research for long-running jobs

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Deep research | `/research`, research routes |
| Web search | SearXNG integration |
| Gitignore hints | `.notebooklm-*` in `.gitignore` |
| Template variables | **237** (future coach integration) |

---

## 3. Architecture

```text
/research UI (depth selector)
        |
        v
research_service.py
  - web (existing)
  - notebook_native.py   # source bundle + synthesis
  - notebook_bridge.py   # spawns CLI or MCP client
        |
        v
ResearchReport { sources[], citations[], body_md }
        |
        v
Optional export to 258 vault / 269 graph ingest
```

---

## 4. Data model

```python
@dataclass
class NotebookSource:
    id: str
    kind: str              # text | url | file | session_export
    ref: str
    title: str
    excerpt: str | None

@dataclass
class NotebookResearchJob:
    job_id: str
    depth: str               # notebook | notebook-external
    sources: list[NotebookSource]
    query: str
    report_md: str | None
    citations: list[dict]
    status: str
    external_notebook_id: str | None
```

Persist under `{KEPRIX_HOME}/research/notebook/{job_id}.json`.

---

## 5. Configuration

```yaml
# cli-config.yaml / env
notebook_research:
  enabled: true
  native_max_sources: 20
  external:
    enabled: false
    command: ""              # path to notebooklm CLI if used
    mcp_url: ""              # optional MCP endpoint
```

Env: `NOTEBOOKLM_BRIDGE_CMD`, `NOTEBOOKLM_MCP_URL` (optional).

---

## 6. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/research/notebook` | Start native notebook job |
| POST | `/api/research/notebook/sources` | Add source to draft bundle |
| GET | `/api/research/notebook/{job_id}` | Status + report |
| POST | `/api/research/notebook/{job_id}/export` | Markdown to vault |

Extend existing `/api/research/*` with `depth` parameter where appropriate.

---

## 7. MCP bridge (external tier)

When `external.enabled`:

- Register MCP server in catalog (same pattern as `GRAPHITI_MCP_URL` in `profile_distribution.py`)
- Tools: `notebook_create`, `notebook_add_source`, `notebook_query`, `notebook_export`
- Graceful fallback message if bridge unavailable: use native tier

---

## 8. UI

`/research` additions:

- **Depth** toggle: Web | Quick Notebook | External (if configured)
- Source tray: paste text, add URL, upload PDF/txt, import session export
- Citation sidebar in report view
- "Send to graph ingest" button (**269** hook)

---

## 9. Files to create

```
src/keprix/research/
  notebook_native.py
  notebook_bridge.py
  notebook_job_store.py

src/keprix/api/
  notebook_research_routes.py

frontend/src/app/(workspace)/research/
  NotebookDepthPanel.tsx    # or extend existing page

docs/features/notebook-research-bridge.md

tests/research/
  test_notebook_native.py
  test_notebook_bridge_mock.py
  test_notebook_research_routes.py
```

---

## 10. Acceptance criteria

- Native Quick Notebook produces a grounded report from 2+ text sources with inline citations.
- External bridge path is feature-flagged; when disabled, UI hides External depth.
- When external command configured, bridge spawns process with timeout and captures stdout (mock in tests).
- Reports export as Markdown to configurable path.
- No secrets committed; `.env.example` documents optional vars.
- Research jobs persist and are listable via API.

---

## 11. Dependencies

- **Uses:** existing `/research` infrastructure
- **Soft:** **237** template variables for report templates
- **Next:** **269** graph ingest from notebook reports
