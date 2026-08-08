# Chase Five Tools Adoption Master Reference (Keprix 267-272)

**Source:** [5 Open Source Repos That Fix 95% of Claude Code's Problems](https://www.youtube.com/watch?v=IRPEfl2BD_c)  
**Transcript:** `planning/competitor-research/youtube-IRPEfl2BD_c-transcript.txt`  
**Competitive note:** `planning/competitor-research/chase-ai-five-tools-adoption.md`  
**Do not archive until prompts 267-272 ship.**

---

## 1. Strategic decision (non-negotiable)

| Adopt | Skip |
| --- | --- |
| Video ingest with frame modes | AI video generation as core feature |
| NotebookLM as optional research bridge | NotebookLM required for all research |
| Graphiti MCP + native graph ingest | Replace ChromaDB/RAG with graph-only |
| Design live preview in builder/coding | Fork Impeccable repo into core without review |
| Coding preflight gates (Ponytail pattern) | Mid-conversation cache-breaking gates |
| Obsidian vault starter Hub pack | Obsidian desktop plugin in core |

**Provider rule:** Video and research bridges stay **multi-provider**; no Gemini-only default path.

---

## 2. Prompt map

| Prompt | Title | Delivers |
| --- | --- | --- |
| **267** | Video ingest skill pack | Local/URL video, transcript + frame modes |
| **268** | Notebook research bridge | MCP/sidecar + Quick Notebook research depth |
| **269** | Graphiti MCP + brain ingest | MCP catalog, ingest jobs, graph retrieval hook |
| **270** | Design live preview studio | Localhost artifact preview + component pick |
| **271** | Coding preflight gates | Pre-build checks, ledger metrics |
| **272** | Obsidian vault starter pack | Hub pack + vault conventions for **259** |

Build order: `266-chase-five-tools-adoption-build-order.md`

---

## 3. Keprix surface map

| Chase gap | Existing Keprix | After pack |
| --- | --- | --- |
| Video | `youtube-content`, `vision_analyze` | **267** full video ingest |
| Research | `/research`, web search | **268** notebook bridge + quick depth |
| Memory | Brain graph drafts, Hindsight, RAG | **269** Graphiti bridge + ingest |
| Front-end | `claude-design`, `design-md` | **270** live preview |
| Tokens | compression, usage, mutation | **271** preflight gates |
| Obsidian | obsidian export, **259** planned | **272** starter pack |

---

## 4. System diagram

```text
267 video-ingest -----> 258 raw/ vault folder
        |
        v
268 notebook-bridge --> /research (quick notebook depth)
        |
269 graphiti-bridge --> brain graph API (246+) + MCP tools
        |
272 obsidian-pack -----> 259 vault provider
        |
270 design-preview ---> builder / coding workspace
        |
271 coding-preflight -> 261 run ledger (token savings)
```

---

## 5. Verification checklist (pack complete)

| Check | Prompt |
| --- | --- |
| MP4/YouTube ingests with mode=caption-only and balanced frames | 267 |
| Notebook bridge runs OR native quick notebook produces report | 268 |
| Graphiti MCP connects; ingest job adds graph nodes | 269 |
| HTML artifact opens in live preview; component inspect works | 270 |
| Preflight blocks redundant codegen; ledger shows token delta | 271 |
| Hub installs Obsidian pack; KEPRIX.md loads in vault session | 272 |

---

## 6. Status table

| Area | Status | Prompt |
| --- | --- | --- |
| YouTube transcripts | **Shipped** | `youtube-content` |
| Video frame ingest | **Shipped** | 267 |
| Deep research | **Shipped** | `/research` |
| Notebook bridge | **Shipped** | 268 |
| Brain graph API | **Missing** | 246+ (parallel) |
| Graphiti MCP | **Shipped** | 269 |
| Design skills | **Shipped** | `claude-design` |
| Live design preview | **Shipped** | 270 |
| Token usage/budgets | **Shipped** | `/usage` |
| Coding preflight | **Shipped** | 271 |
| Vault starter pack | **Shipped** | 272 |
