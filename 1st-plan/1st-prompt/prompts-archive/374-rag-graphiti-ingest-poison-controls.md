# Prompt 374: RAG and Graphiti ingest poison controls

Status: COMPLETED and archived 2026-08-03 as `../prompts-archive/374-rag-graphiti-ingest-poison-controls.md`  
Series: LLM threat-model hardening (ByteByteGo / Tips-and_Bits)  
Depends on: RAG pipeline, Graphiti bridge, Channel Shield memory guard patterns, 372 quarantine helper (reuse if present)  
Related: `data-ops-surfaces-upgrade.md` P3 RAG Must (UI polish; this prompt owns security on ingest)  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Threat model: poisoning retrieval and knowledge graphs is more durable than a single prompt injection. Keprix can ingest Notion, files, URLs, research, session text, and Graphiti episodes. Memory tools already soft-block some poisoned-on-disk entries; ingest paths for RAG stores and Graphiti are weaker and can later be recalled as trusted context.

## Goal

Every ingest path into RAG stores and Graphiti must scan, classify, and either accept, quarantine, or reject content before it is indexed or graphed. Retrieval must prefer safe snippets and never elevate quarantined text to system-instruction trust.

## Baseline

| Piece | Path |
| --- | --- |
| RAG routes / pipeline | `src/keprix/rag_pipeline/` |
| RAG memory indexer | `src/keprix/memory/rag/` |
| Graphiti bridge | `src/keprix/brain/graphiti_bridge.py`, `/api/brain/graphiti/*` |
| Graphiti docs | `docs/features/graphiti-bridge.md` |
| Memory scanner | `src/keprix/security/memory_content_scanner.py` |
| Channel Shield memory sync | `channel_shield/memory_guard_sync.py` |
| Prompt heuristics | `security/prompt_guard.py` (reuse) |

## Must-haves

1. **Shared ingest gate** (`src/keprix/security/ingest_poison_gate.py` or equivalent):
   - Inputs: text, optional metadata (source, connector, url, user_id).
   - Runs: prompt-injection heuristics, instruction-boundary / HTML smuggling checks, secret pattern scan, optional executable attachment reject.
   - Outputs: `allow | quarantine | reject` + reasons + confidence + redacted preview.
2. **Wire into all ingest entrypoints**:
   - RAG pipeline: manual, Notion, files, URL (whatever connectors are live).
   - Memory RAG indexer paths used by chat/self-knowledge.
   - Graphiti: `POST /api/brain/graphiti/ingest` and any auto-ingest from session/research/vault_file.
3. **Storage semantics**:
   - `reject`: do not persist chunk/episode; return clear API error.
   - `quarantine`: persist with `trust=quarantined` (or equivalent flag), never inject raw text into agent prompts; allow operator review UI later.
   - `allow`: normal index with `trust=trusted` / source provenance intact.
4. **Retrieval semantics**:
   - Retriever filters or ranks down quarantined by default (`include_quarantined=false`).
   - If quarantine is returned for forensics, wrap as opaque evidence ref (align with 372 context quarantine).
5. **Graphiti bridge**:
   - Do not call remote MCP ingest with unscreened payloads when gate rejects.
   - Job list shows quarantine/reject reason on failed or partial jobs.
6. **Operator + docs**:
   - Minimal admin or Data RAG panel signal: last N ingest verdicts.
   - Document poison model in `docs/security/` and note Graphiti MCP is not a trust boundary.
7. **Tests**:
   - Fixture corpus: classic injection, "ignore previous...", embedded system tags, credential bait.
   - Assert RAG index count does not increase on reject; quarantine not returned in default query.
   - Graphiti ingest endpoint returns structured verdict.

## Nice-to-haves

1. Re-scan job for existing stores (migration / doctor command).
2. Per-connector policy (Notion stricter than operator paste).
3. Scout signal on quarantine/reject storm.

## Ultimate

1. Content signing of trusted corpora + provenance chain into citations UI.
2. Canary documents that alert if retrieved + complied with by the agent.

## Out of scope

- Full Data UX rebuild (see `data-ops-surfaces-upgrade.md`)
- Replacing Graphiti MCP image
- Changing embedding model selection

## Delivery order

1. Implement shared ingest gate + unit fixtures
2. Wire RAG connectors + indexer
3. Wire Graphiti ingest + jobs metadata
4. Retriever default filter
5. Thin UI/API surface for verdicts
6. Docs + tests + deploy backend; smoke Notion/manual ingest with poison string

## Acceptance

- [ ] No live connector bypasses the gate
- [ ] Default retrieval never elevates quarantined text as trusted instructions
- [ ] Graphiti remote ingest not called on reject
- [ ] Tests cover allow/quarantine/reject
- [ ] Docs state that indexed data is untrusted until gate + provenance say otherwise

## Archive / queue pointers

- Build order: `../prompts-archive/ref-372-llm-threat-model-hardening-build-order.md`
- Data UX sibling: `./data-ops-surfaces-upgrade.md` (P3)
