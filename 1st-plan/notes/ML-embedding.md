
This is a layered decision. Here is how to think about it, what already fits, and what to build.

---
The right mental model first

keprix is an agent OS kernel; it does not need to "do ML" itself. It needs to invoke ML at the right points through its tool registry. Every ML capability should be exposed as a keprix tool that agents call, not wired directly into application code. That is the architectural rule. The question is which ML capabilities to cover and where each one comes from.

---
The four ML layers keprix needs (priority order)

Layer 1: LLM inference (already covered)

Anthropic Claude via the API. This is already the keprix core. Route through an inference adapter so you can swap providers without touching agent code. Keep this as-is. Add Groq as a fallback for speed-critical tool calls.

Layer 2: Embeddings + vector search (build this first)

This is the most important ML primitive for keprix and the one most worth building as a first-party keprix service. It powers the domain knowledge packs (borehole corpus, ABBIS domain data, GBDA rulebook).

How to build it:
- Pick one embedding API: Voyage AI (voyage-3-lite for cost, voyage-3 for quality) or OpenAI text-embedding-3-large. Voyage has the best retrieval quality for technical/domain text right now.
- Vector store: pgvector extension on your existing PostgreSQL instance. No new infrastructure needed for MVP. Migrate to Qdrant or Weaviate when the corpus exceeds 1M vectors.
- Build a KnowledgePack service inside keprix that handles: ingest -> chunk -> embed -> store -> retrieve. Domain packs (borehole geology, Ghana water regulations, WRC Act 522) load into this.
- Expose as keprix tool: search_domain_knowledge(query, pack_id, top_k).

Do not use 3rd party MCP for this. Own the data. The knowledge pack contents are proprietary (GBDA drilling data, member records) and cannot go to an external embedding service without data handling agreements.

Layer 3: Language intelligence (build or self-host)

This is the most uniquely valuable piece for West Africa and the one where public APIs will fail you.

What exists publicly:
- Meta NLLB (No Language Left Behind): open-weight model supporting Akan, Twi, Ewe, Hausa, Ga, Dagbani. Runs on CPU. Free.
- OpenAI Whisper: STT, handles Twi and Ghanaian-accented English reasonably well. Open-weight; run it yourself or use OpenAI API.
- Google Translate API: covers Twi and Ewe but not Dagbani or Ga; costs $20/1M chars.
- ElevenLabs or Azure TTS: English/French only; useless for Twi responses.

Recommendation: Self-host NLLB-200 (600M param distilled version) for translation. Self-host Whisper (medium model) for STT. Use Coqui TTS or a fine-tuned model for Twi/Ga responses; this is not yet commercial-ready so Phase 2. Build a LanguageService inside keprix with tools: detect_language(text), translate(text, from_lang, to_lang), transcribe_audio(audio_file).

Layer 4: Domain classifiers (build when data exists)

These are small, fast models trained on your own domain data. They are cheaper and faster than calling an LLM for structured decisions.

┌───────────────────────────┬──────────────────────────────────────────┬─────────────────────────────────────────────┬──────────────────────────────────────────────────┐
│        Classifier         │                  Input                   │                   Output                    │                  When to build                   │
├───────────────────────────┼──────────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Intent router             │ WhatsApp message text                    │ Enum: quote, report, dues, complaint, other │ After 500+ labelled examples from real usage     │
├───────────────────────────┼──────────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Formation classifier      │ Drilling log geological description      │ Formation enum (granite, laterite, etc.)    │ After 200+ completed drilling reports            │
├───────────────────────────┼──────────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Borehole yield predictor  │ Formation type + GPS coordinates + depth │ Water yield L/min range                     │ After 1,000+ drilling reports with outcomes      │
├───────────────────────────┼──────────────────────────────────────────┼─────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Duplicate member detector │ Registration fields                      │ Similarity score to existing members        │ Build at launch; use fuzzy string matching first │
└───────────────────────────┴──────────────────────────────────────────┴─────────────────────────────────────────────┴──────────────────────────────────────────────────┘

Build with scikit-learn or a tiny fine-tuned BERT variant. Host inside keprix as a Python subprocess or FastAPI micro-service. Expose as keprix tools.

---
What public APIs to use and when

┌───────────────────────────────┬─────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────┐
│             Task              │                           Recommended API                           │                         When to switch                         │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ LLM inference                 │ Anthropic Claude (Sonnet 4.6 for most, Haiku 4.5 for cheap/fast)    │ Never switch primary; add Groq for speed fallback              │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Embeddings                    │ Voyage AI (voyage-3)                                                │ Switch to self-hosted when cost becomes prohibitive            │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ STT (speech to text)          │ OpenAI Whisper via API (MVP), self-host later                       │ Self-host Whisper medium when WhatsApp volume > 10k mins/month │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Vision/document understanding │ Claude vision API (already available)                               │ No need to change                                              │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Translation                   │ Google Translate API for Twi/Ewe (MVP); NLLB self-hosted for others │ Move to NLLB self-hosted at scale                              │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ TTS                           │ ElevenLabs for English-language responses                           │ No Twi TTS option yet; Phase 2                                 │
└───────────────────────────────┴─────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────┘

---
On 3rd party MCP servers

Use MCP servers selectively. Good uses:
- Brave Search MCP or Exa MCP: let agents do live web search for regulatory updates (WRC changes, CWSA standards)
- Firecrawl MCP: scrape and ingest regulatory PDFs into the knowledge pack
- Database MCP: expose read-only keprix memory to agents at query time

Do NOT use MCP servers for ML inference or for anything that sends member data (names, phone numbers, national IDs) to an external service. Run inference locally or via direct API call with data handling agreements in place.

---
Whether to build your own ML module

Yes, but define what "own ML module" means precisely:

Build this (the keprix ML service):
keprix/
  services/
    ml/
      inference.ts      # routes LLM calls to providers
      embeddings.ts     # chunk -> embed -> store -> retrieve
      language.ts       # detect, translate, transcribe
      vision.ts         # wraps Claude vision for documents
      classifiers/      # lightweight domain classifiers (Python)
    vector-store/
      pgvector.ts       # pgvector adapter

Expose everything as keprix tools. Agents never call ML APIs directly; they call tools.

Do NOT build:
- Your own LLM. Not in this decade.
- Your own embedding model. Voyage/OpenAI are better than anything you can train.
- Your own vector DB for MVP. pgvector is sufficient for up to 1M vectors.
- Your own STT model. Whisper already handles Ghanaian English adequately.

---
How to go about it (sequenced)

Phase 1 (build now, needed for ABBIS + GBDA AMS):
1. Set up pgvector on the existing Postgres instance
2. Build the KnowledgePack service with Voyage AI embeddings
3. Load the borehole knowledge pack (borehole corpus, WRC Act 522, GBDA guidelines)
4. Expose search_domain_knowledge as a keprix tool
5. Wire it into the ABBIS domain pack (prompt 21)

Phase 2 (build when WhatsApp goes live):
1. Self-host Whisper medium
2. Build LanguageService with NLLB for Twi/Ewe/Ga translation
3. Build the intent router classifier on first 500 real messages
4. Expose detect_language, translate, transcribe_audio as keprix tools

Phase 3 (build when drilling report data accumulates):
1. Formation classifier from GBDA drilling report database
2. Yield predictor (this becomes a real competitive differentiator for ABBIS)
3. Anomaly detector for the mutation engine (detect when agent behavior diverges from playbook)

The single most important move right now is Phase 1: embeddings + vector search. Without that, the domain knowledge packs are just static text files and the AI agents have no retrieval capability. Everything else depends on having that foundation.
