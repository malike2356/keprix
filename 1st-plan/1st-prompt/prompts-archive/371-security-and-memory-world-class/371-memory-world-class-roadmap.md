# Memory / Brain: world-class roadmap

Status: COMPLETED and archived 2026-08-02 as `../prompts-archive/371-memory-world-class-roadmap.md`  
Surface priority: highest (`/memory` and Brain graph / galaxy / health / Graphiti)  
Scope: compete with Mem0, Zep, Letta (MemGPT), Graphiti/Cognee-style temporal graphs, ChatGPT/Claude memory UX, SuperMemory, Honcho.

## Honest baseline (Keprix today)

**Not best-in-class yet.** Strength is breadth (brain graph, vault galaxy, health, optional Graphiti, RAG, curated `MEMORY.md`, plugin ports). Weakness is product unity: `/memory` is a thin list/delete over episodic PG vectors, while the real agent memory path is curated files + turn prefetch + activation edges. Stores fragment; docs overclaim Chroma/search/add.

| Peer | What they nail | Keprix relative |
| --- | --- | --- |
| Mem0 | Simple durable facts API, automatic extraction, strong recall DX | Episodic save/search exist; UX and auto-extract weak |
| Zep / Graphiti | Temporal entity+fact graph, session distillation | Graphiti optional external; native brain is activation graph, not temporal KG |
| Letta | Explicit core/archival/recall memory architecture | Partial (MEMORY.md + episodic + RAG) but not one coherently typed model |
| ChatGPT Memory | Invisible write, visible user control, conflict update | Continuity etiquette exists; `/memory` control plane too thin |
| Claude Projects | Project-scoped manuals + retrieval | Workspace RAG + vault; weaker memory governance UI |
| SuperMemory / Honcho | Plugins already listed | Ports exist; not first-party world-class UX |

---

## Must-haves (ship or you are not competitive)

1. **One control plane** for "what the agent knows about me": search, add, edit, delete, pin/unpin, with provenance (session, RAG source, manual, REM).
2. **Automatic durable extraction** at session end (REM consolidator wired; thresholded; no fluff).
3. **Reliable recall into turns**: hybrid retrieval (vector + FTS + graph neighbour boost), ranked, budgeted token window, citation/provenance in debug.
4. **Human overwrite wins**: edit/delete/ contradict → update store and stop zombie recalls.
5. **Correct scopes**: user vs workspace vs agent/persona; never leak across tenants.
6. **Typed memory**: at least profile facts, preferences, decisions, entities, open loops (not one undifferentiated blob).
7. **/memory UI that matches the store the agent uses** (or clear dual panes: Curated vs Episodic vs Documents).
8. **Working eval**: gold-set recall @k and "should not recall" negatives.

Gaps closed in this pass (started 2026-08-02): search/add/edit on `/memory`, `PATCH /api/memory/{id}`, brain panel edit path fix, REM hook from session end path, benchmark harness scaffold.

---

## Nice-to-haves (should)

1. Dedup + merge UI (health already sketches this for brain).
2. Decay/reinforce by use (access count + TTL already partly modeled).
3. Import/export (Obsidian/JSON already on brain; extend to memory list).
4. Memory "why was this injected?" inspector on chat turns.
5. Conflict resolution ("You said X, now Y") with explicit confirm.
6. Project/client packs of memory (CRM-like scopes).
7. Graphiti first-class when MCP is up, with native fallback narrative.
8. Galaxy + List + Graph as one Brain product with shared search.

---

## World-class (wow; rare and differentiating)

1. **Temporal knowledge graph**: entities, relations, valid_from/valid_to, supersession, not just embeddings.
2. **Belief revision**: confidence, sources, disputed state; agent prefers recent confirmed facts.
3. **Dreaming / REM offline jobs**: cluster episodes, promote to semantic, archive noise.
4. **Multi-modal memory**: OCR/gallery/docs/voice notes land in the same recall path with modality tags.
5. **Self-model + user-model separation**: agent skills/playbooks vs user identity facts.
6. **Cross-session continuity score** shown in UI (completeness, staleness, contradiction rate).
7. **Memory Constitution**: policy that agents cannot invent "I remember" without a write tool (Keprix has a gate; make it product-visible and tested).
8. **Eval leaderboard** in CI: nightly recall, contradiction, and privacy isolation tests.

---

## Unification target architecture

```
                    +---------------------+
 Chat turn -------> | Recall orchestrator | ----> budgeted <memory-context>
                    +----------+----------+
                               |
        +----------+-----------+-----------+-----------+
        |          |           |           |           |
   Curated     Episodic     RAG docs    Brain edges  Graphiti
  MEMORY.md    PG vectors   rag_chunks  SQLite graph   (opt)
  USER.md
        ^          ^
        |          |
   /memory hub (List) should manage BOTH + deep-links to Graph/Galaxy/Health
```

Phase A: make List the hub (this week).  
Phase B: shared search API across stores.  
Phase C: temporal KG or Graphiti-native.  
Phase D: multimodal + belief revision.

---

## Immediate build order

1. Must-have UX + API truth on `/memory` (search/add/edit/delete).
2. Wire `run_session_consolidation` into session finalize / memory manager end.
3. Fix `NodeContentPanel` memory PATCH to `/api/memory/{id}`.
4. Benchmark harness + small gold set under `keprix/scripts/` or `tests/`.
5. Docs: rewrite `docs/features/memory.md` to match reality (follow-up).

## Status (COMPLETED 2026-08-02)

Archived to `prompts-archive/371-memory-world-class-roadmap.md`.

## Status (2026-08-02 night)

Implemented and deploying:

- Unified hub API under `/api/memory/hub/*` (overview, recall, dream, graph, conflicts, export/import, multimodal ingest, continuity, constitution)
- Temporal KG tables + belief revision + dreaming service
- Native orchestrator injected into `MemoryManager.prefetch_all`
- `/memory` full control-plane UI
- `/v1/memory/search` wired to orchestrator
- Eval scripts: `scripts/memory_recall_benchmark.py`, `scripts/memory_eval_leaderboard.py`

Remaining polish (non-blocking for local use): rewrite docs/features/memory.md; graphiti live query inside orchestrator (currently availability note); stronger NLP entity extraction.

## Success metrics

- Human can find and fix a wrong fact in under 30s.
- Session that states "my name is X" yields durable recall next session without re-stating.
- Gold-set recall@5 >= 0.8 on local embeddings smoke.
- Zero cross-user recall in multi-user mode.
- Chat never claims memory write without tool/store success.
