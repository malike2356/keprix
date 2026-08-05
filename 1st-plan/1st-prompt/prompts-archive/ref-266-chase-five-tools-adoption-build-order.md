# Chase five tools adoption build order (Keprix 267-272)

**Master reference:** `266-chase-five-tools-adoption-master-reference.md`  
**Transcript:** `planning/competitor-research/youtube-IRPEfl2BD_c-transcript.txt`

---

## Critical path

```text
267 (video) --> 258 raw ingest (Agentic OS; soft dependency)

269 (graphiti) --> brain 246+ (parallel OK)

271 (preflight) --> 261 ledger (Agentic OS; soft)

272 (obsidian pack) --> 259 vault (Agentic OS; soft)

268 (notebook) and 270 (design) parallel anytime after 267
```

---

## Prompt order

| Order | Prompt | Title | Depends on | Parallel OK? | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | **267** | Video ingest skill pack | `youtube-content`, ffmpeg | - | Shipped |
| 2a | **271** | Coding preflight gates | mutation, **261** stub OK | Yes with 269 | Shipped |
| 2b | **269** | Graphiti MCP + brain ingest | graph_edges, MCP catalog | Yes with 271 | Shipped |
| 3 | **268** | Notebook research bridge | `/research` | Yes with 270 | Shipped |
| 3b | **270** | Design live preview studio | builder/coding | Yes with 268 | Shipped |
| 4 | **272** | Obsidian vault starter pack | **259** stub OK | Last | Shipped |

---

## Minimum viable Chase parity (demo)

Ship **267 + 269 + 271**:

- Ingest a competitor YouTube/MP4 with frames
- Query corpus via graph bridge
- Show token savings on coding task with preflight on

Add **270** for design story; **268** for research story; **272** with vault pack.

---

## Cross-product rules

1. **Skills first, core tools last** (Footprint Ladder in `AGENTS.md`).
2. **Optional installs** via Hub/optional-skills; core stays lean.
3. **Measure token claims** via **261** ledger, not upstream benchmarks.
4. **No Claude Code marketplace** assumptions in UI copy.

---

## Archive order

Archive each prompt to `prompts-archive/` when AC pass. Update `PROMPT-IMPLEMENTATION-AUDIT.md` and master reference status table.

All **267-272** shipped on 2026-07-09; `chase-ai-five-tools-adoption.md` is marked shipped.
