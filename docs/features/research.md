# Deep research

Deep research runs multi-step, cited research projects using web retrieval, document analysis, and LLM synthesis. Results include source citations, structured outlines, and exportable reports.

## How it works

A research run goes through four stages:

1. **Plan** - the agent outlines the research question into sub-topics and search queries.
2. **Retrieve** - SearXNG (self-hosted web search) fetches results for each query. Document uploads and memory are also searched.
3. **Synthesise** - retrieved content is chunked, ranked by relevance, and fed to the LLM in passes. Each synthesis pass produces a cited section.
4. **Report** - sections are assembled into a final structured report with numbered references.

All stages stream progress to the UI so you can watch the work in real time.

## Web UI (`/research`)

1. Click **New project** or the launcher card **Deep Research**.
2. Enter a research question or topic. Be specific for better results.
3. Choose **Depth**:
   - **Quick**: 1-2 retrieval rounds, ~3-5 minutes
   - **Standard**: 3-4 rounds, ~10-15 minutes
   - **Deep**: 6+ rounds with iterative gap-filling, 20-40 minutes
4. Optionally attach source documents. These are included in retrieval alongside web results.
5. Click **Run research**.

Progress, intermediate sources, and the live draft appear as the run proceeds.

## Export deliverables

When a run finishes, use the action buttons on the report card at `/research`:

| Format | Button | Notes |
| --- | --- | --- |
| PDF | Download PDF | Cover page, serif layout, citation-friendly styling (WeasyPrint) |
| Word | Download Word | Requires Pandoc on the server; falls back to Markdown with a notice if missing |
| HTML | Download HTML | Self-contained HTML with the same research stylesheet |
| Markdown | Copy Markdown | Clipboard copy of the stored report |

Exports read the persisted job report, so they work after page reload or via `?job=rsch-...`.

Optional dependencies:

- **PDF (required for styled output):** `weasyprint` is bundled in `pyproject.toml`. After install or upgrade, restart the API. Without it, PDF export falls back to a single-page plain-text dump (raw `**markdown**` visible).
- **DOCX:** system `pandoc` binary

API:

| Action | Method | Endpoint |
| --- | --- | --- |
| Export job | GET | `/api/research/jobs/{job_id}/export?format=pdf` |
| Export job (body) | POST | `/api/research/jobs/{job_id}/export` |

Formats: `pdf`, `html`, `markdown`, `docx`. Returns `409` while the job is still running.

## Research projects

Each run is a **research project** with:

- Topic and parameters
- Source list with URLs and relevance scores
- Outline (auto-generated, editable before final report)
- Final report in Markdown
- Export: PDF, Word, Markdown, or JSON with full citations

Projects are saved and reusable. You can open a previous project and run a follow-up from the outline.

## Depth controls

```bash
KEPRIX_RESEARCH_MAX_ROUNDS=6         # override max retrieval rounds
KEPRIX_RESEARCH_MAX_SOURCES=40       # max sources to consider per run
KEPRIX_RESEARCH_MIN_RELEVANCE=0.6    # discard sources below this score
KEPRIX_RESEARCH_SEARXNG_URL=http://searxng:8080   # SearXNG endpoint
```

SearXNG runs as a Docker Compose sidecar. If `KEPRIX_RESEARCH_SEARXNG_URL` is not set, the agent falls back to direct web fetch (slower, less complete).

## Slash command

In chat, type `/research` followed by a question to start a quick research run without leaving the chat window. The result appears as a collapsible card in the thread.

## Zotero integration

Connect a Zotero library for citation management:

```bash
KEPRIX_ZOTERO_API_KEY=...
KEPRIX_ZOTERO_LIBRARY_ID=...
KEPRIX_ZOTERO_LIBRARY_TYPE=user   # or 'group'
```

When Zotero is configured, newly retrieved sources can be saved to your library with one click, and existing Zotero items are available as source documents.

## Obsidian vault

Export research notes directly to an Obsidian vault:

```bash
KEPRIX_OBSIDIAN_VAULT_PATH=/path/to/vault
```

Exported notes include front-matter, backlinks, and source citations in Obsidian format.

## Research workspace architecture

For the full technical detail on how research jobs are queued, how artifacts are stored, and how the data plane is separated from the main workspace, see [Research workspace architecture](../research/research-workspace-architecture.md).

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| List projects | GET | `/api/research/projects` |
| Create project | POST | `/api/research/projects` |
| Get project | GET | `/api/research/projects/{id}` |
| Start run | POST | `/api/research/projects/{id}/run` |
| Stream events | GET | `/api/research/projects/{id}/events` |
| Get report | GET | `/api/research/projects/{id}/report` |
| Export | GET | `/api/research/projects/{id}/export?format=pdf` |

Full schema: [REST API reference](../reference/api.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Run produces no sources | SearXNG not reachable | Check `KEPRIX_RESEARCH_SEARXNG_URL`; run `docker compose ps` |
| Sources all low relevance | Topic too broad or ambiguous | Narrow the question; add constraint terms |
| Report truncated | Context window limit | Use **Standard** or **Quick** depth; research question may need splitting |
| Citations missing | Source fetch failed | Check network egress; some sites block scraping |
| Zotero save fails | API key or library ID wrong | Verify at `https://www.zotero.org/settings/keys` |

## Related

- [Memory and RAG](memory.md)
- [Compare models](compare-models.md)
- [Opportunity engine](../opportunity-engine.md)
- [Evals](evals.md)
- [Research workspace architecture](../research/research-workspace-architecture.md)
