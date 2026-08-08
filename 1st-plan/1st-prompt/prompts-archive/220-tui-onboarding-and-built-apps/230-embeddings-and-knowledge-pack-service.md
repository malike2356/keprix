# keprix ML: Embeddings and Knowledge Pack Service (Prompt 230)

**Series:** ML infrastructure (229-232). Builds on scaffold from 229.
**Platform:** keprix agent OS kernel
**Phase:** Phase 1 (build now, use immediately for ABBIS RAG and any future domain app)
**Principle:** Every agent retrieval call goes through the `search_domain_knowledge` tool. No application queries pgvector directly.

---

## 1. What this prompt builds

- pgvector PostgreSQL extension and the `knowledge_chunks` table
- Voyage AI embedding pipeline with Redis cache layer
- KnowledgePack ingestion API: ingest a corpus, chunk it, embed it, store it
- `search_domain_knowledge` keprix tool: semantic similarity search over a named pack
- Seed corpus for borehole and GBDA domain knowledge
- Management API: list packs, delete pack, re-index pack

---

## 2. Database schema (migration)

Create migration file `database/migrations/0005_knowledge_packs.sql`:

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Knowledge pack registry
CREATE TABLE knowledge_packs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pack_id         TEXT UNIQUE NOT NULL,   -- slug: "borehole-ops", "wrc-act-522", "gbda-guidelines"
  display_name    TEXT NOT NULL,
  description     TEXT,
  embedding_model TEXT NOT NULL DEFAULT 'voyage-3',
  embedding_dims  INTEGER NOT NULL DEFAULT 1024,
  chunk_count     INTEGER NOT NULL DEFAULT 0,
  indexed_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chunks with vector embeddings
CREATE TABLE knowledge_chunks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pack_id     TEXT NOT NULL REFERENCES knowledge_packs(pack_id) ON DELETE CASCADE,
  source_uri  TEXT NOT NULL,              -- file path or URL of source document
  chunk_index INTEGER NOT NULL,
  content     TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  embedding   vector(1024),              -- matches voyage-3 dims
  metadata    JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cosine similarity index (HNSW - best recall vs IVFFlat at this scale)
CREATE INDEX knowledge_chunks_embedding_idx
  ON knowledge_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Fast pack-scoped lookups
CREATE INDEX knowledge_chunks_pack_idx ON knowledge_chunks(pack_id);

-- Fast source dedup check
CREATE INDEX knowledge_chunks_source_idx ON knowledge_chunks(pack_id, source_uri);
```

For voyage-3-lite (512 dims) or custom dims: store in `knowledge_packs.embedding_dims` and cast the column when re-indexing. For MVP, all packs use voyage-3 at 1024 dims.

---

## 3. Embedding service (services/embedding_service.py)

```python
import asyncio
from dataclasses import dataclass
from typing import Any
import asyncpg

from ..providers.base import EmbeddingProvider
from ..utils.chunking import chunk_document, Chunk
from ..utils.caching import get_cached, set_cached
from ..config import settings

@dataclass
class SearchResult:
    content: str
    score: float
    source_uri: str
    chunk_index: int
    metadata: dict[str, Any]

class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider, db_pool: asyncpg.Pool):
        self.provider = provider
        self.pool = db_pool

    # --- Ingestion ---

    async def ingest_document(
        self,
        pack_id: str,
        source_uri: str,
        content: str,
        metadata: dict | None = None,
        max_tokens_per_chunk: int = 512,
        overlap_tokens: int = 64,
    ) -> int:
        """Chunk, embed, and store a document. Returns number of chunks stored."""
        chunks = chunk_document(content, max_tokens_per_chunk, overlap_tokens, metadata or {})
        if not chunks:
            return 0

        # Batch embed: Voyage AI supports up to 128 texts per call
        batch_size = 96
        embeddings: list[list[float]] = []
        for i in range(0, len(chunks), batch_size):
            batch_texts = [c.text for c in chunks[i:i + batch_size]]
            batch_embs = await self.provider.embed(batch_texts)
            embeddings.extend(batch_embs)

        # Delete existing chunks for this source in this pack (re-index)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM knowledge_chunks WHERE pack_id=$1 AND source_uri=$2",
                pack_id, source_uri,
            )
            await conn.executemany(
                """
                INSERT INTO knowledge_chunks
                  (pack_id, source_uri, chunk_index, content, token_count, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::vector, $7)
                """,
                [
                    (pack_id, source_uri, c.index, c.text, c.token_count,
                     str(emb), c.metadata)
                    for c, emb in zip(chunks, embeddings)
                ]
            )
            await conn.execute(
                """
                UPDATE knowledge_packs
                SET chunk_count = (
                  SELECT COUNT(*) FROM knowledge_chunks WHERE pack_id=$1
                ), indexed_at=now(), updated_at=now()
                WHERE pack_id=$1
                """,
                pack_id,
            )
        return len(chunks)

    # --- Search ---

    async def search(
        self,
        pack_id: str,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.65,
    ) -> list[SearchResult]:
        cache_key_payload = {"pack_id": pack_id, "query": query, "top_k": top_k}
        cached = await get_cached("search", cache_key_payload)
        if cached:
            return [SearchResult(**r) for r in cached]

        query_emb = await self.provider.embed([query])
        vec = str(query_emb[0])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT content, source_uri, chunk_index, metadata,
                       1 - (embedding <=> $1::vector) AS score
                FROM knowledge_chunks
                WHERE pack_id = $2
                  AND 1 - (embedding <=> $1::vector) >= $3
                ORDER BY embedding <=> $1::vector
                LIMIT $4
                """,
                vec, pack_id, score_threshold, top_k,
            )

        results = [
            SearchResult(
                content=r["content"],
                score=float(r["score"]),
                source_uri=r["source_uri"],
                chunk_index=r["chunk_index"],
                metadata=dict(r["metadata"] or {}),
            )
            for r in rows
        ]

        ttl = 3600  # search results cached 1h (documents don't change often)
        await set_cached("search", cache_key_payload, [r.__dict__ for r in results], ttl)
        return results

    # --- Pack management ---

    async def create_pack(self, pack_id: str, display_name: str, description: str = "") -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO knowledge_packs (pack_id, display_name, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (pack_id) DO NOTHING
                """,
                pack_id, display_name, description,
            )

    async def delete_pack(self, pack_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM knowledge_packs WHERE pack_id=$1", pack_id)

    async def list_packs(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT pack_id, display_name, chunk_count, indexed_at FROM knowledge_packs ORDER BY pack_id"
            )
        return [dict(r) for r in rows]
```

---

## 4. Embeddings router (routers/embeddings.py)

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.embedding_service import EmbeddingService
from ..dependencies import get_embedding_service  # wire in main.py

router = APIRouter()

class IngestRequest(BaseModel):
    pack_id: str
    source_uri: str
    content: str
    metadata: dict = Field(default_factory=dict)
    max_tokens_per_chunk: int = 512
    overlap_tokens: int = 64

class IngestResponse(BaseModel):
    pack_id: str
    source_uri: str
    chunks_stored: int

class SearchRequest(BaseModel):
    pack_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.65, ge=0.0, le=1.0)

class SearchResponse(BaseModel):
    results: list[dict]
    pack_id: str
    query: str

class CreatePackRequest(BaseModel):
    pack_id: str
    display_name: str
    description: str = ""

@router.post("/packs", status_code=201)
async def create_pack(req: CreatePackRequest, svc: EmbeddingService = Depends(get_embedding_service)):
    await svc.create_pack(req.pack_id, req.display_name, req.description)
    return {"pack_id": req.pack_id, "status": "created"}

@router.get("/packs")
async def list_packs(svc: EmbeddingService = Depends(get_embedding_service)):
    return {"packs": await svc.list_packs()}

@router.delete("/packs/{pack_id}")
async def delete_pack(pack_id: str, svc: EmbeddingService = Depends(get_embedding_service)):
    await svc.delete_pack(pack_id)
    return {"pack_id": pack_id, "status": "deleted"}

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest, svc: EmbeddingService = Depends(get_embedding_service)):
    n = await svc.ingest_document(
        pack_id=req.pack_id,
        source_uri=req.source_uri,
        content=req.content,
        metadata=req.metadata,
        max_tokens_per_chunk=req.max_tokens_per_chunk,
        overlap_tokens=req.overlap_tokens,
    )
    return IngestResponse(pack_id=req.pack_id, source_uri=req.source_uri, chunks_stored=n)

@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, svc: EmbeddingService = Depends(get_embedding_service)):
    results = await svc.search(req.pack_id, req.query, req.top_k, req.score_threshold)
    return SearchResponse(
        results=[r.__dict__ for r in results],
        pack_id=req.pack_id,
        query=req.query,
    )
```

---

## 5. TypeScript client (packages/ml-client/src/embedding-client.ts)

```typescript
import { MLServiceClient } from "./index"
import type {
  EmbedRequest,
  EmbedResponse,
  SearchRequest,
  SearchResult,
} from "./types"

export class EmbeddingClient extends MLServiceClient {
  async search(req: SearchRequest): Promise<{ results: SearchResult[] }> {
    return this.post("/embeddings/search", req)
  }

  async ingest(
    packId: string,
    sourceUri: string,
    content: string,
    metadata?: Record<string, unknown>,
  ): Promise<{ chunks_stored: number }> {
    return this.post("/embeddings/ingest", {
      pack_id: packId,
      source_uri: sourceUri,
      content,
      metadata: metadata ?? {},
    })
  }

  async createPack(packId: string, displayName: string, description?: string): Promise<void> {
    await this.post("/embeddings/packs", { pack_id: packId, display_name: displayName, description })
  }

  async listPacks(): Promise<Array<{ pack_id: string; display_name: string; chunk_count: number }>> {
    const res = await fetch(`${this["baseUrl"]}/embeddings/packs`)
    const data = await res.json()
    return data.packs
  }
}
```

---

## 6. keprix tool implementation: `search_domain_knowledge`

Replace the stub from 229 with this implementation:

```typescript
// In keprix tool registry
{
  name: "search_domain_knowledge",
  description: "Search a named knowledge pack for context relevant to a query. Use this before answering domain questions to ground the response in verified content.",
  parameters: {
    query: { type: "string", required: true, description: "Natural-language search query" },
    pack_id: { type: "string", required: true, description: "Slug of the knowledge pack to search" },
    top_k: { type: "number", default: 5, description: "Max results to return (1-20)" },
    score_threshold: { type: "number", default: 0.65, description: "Minimum similarity score (0-1)" },
  },
  handler: async (args: { query: string; pack_id: string; top_k?: number; score_threshold?: number }) => {
    const results = await embeddingClient.search({
      query: args.query,
      pack_id: args.pack_id,
      top_k: args.top_k ?? 5,
      score_threshold: args.score_threshold ?? 0.65,
    })
    if (results.results.length === 0) {
      return { found: false, message: "No relevant content found in this knowledge pack." }
    }
    return {
      found: true,
      results: results.results.map((r) => ({
        content: r.content,
        score: r.score,
        source: r.metadata?.source_label ?? r.source_uri,
      })),
    }
  },
}
```

---

## 7. Seed knowledge packs

Create `apps/ml-service/seed/` directory with these seed files. Run ingestion at startup if the pack does not exist (check `list_packs` first).

### 7.1 Packs to seed

| pack_id | display_name | Source documents |
|---|---|---|
| `borehole-operations` | Borehole Operations Corpus | Daily Drilling Log fields, WRC register category definitions, GBDA 12 standards, formation description glossary |
| `wrc-regulations` | WRC Regulations (LI 1827) | WRC Act 522 summary, licence categories A/B/C descriptions, registration requirements |
| `gbda-guidelines` | GBDA Guidelines | GBDA About page, constitution extracts, membership benefits, 3-stage membership description |
| `abbis-platform-help` | ABBIS Platform Help | ABBIS feature descriptions, FAQ, platform terminology |

### 7.2 Seed script (seed/seed_packs.py)

```python
import asyncio, httpx, json
from pathlib import Path

BASE_URL = "http://localhost:8200"
SEED_DIR = Path(__file__).parent / "corpus"

PACKS = [
    {"pack_id": "borehole-operations", "display_name": "Borehole Operations Corpus"},
    {"pack_id": "wrc-regulations", "display_name": "WRC Regulations (LI 1827)"},
    {"pack_id": "gbda-guidelines", "display_name": "GBDA Guidelines"},
    {"pack_id": "abbis-platform-help", "display_name": "ABBIS Platform Help"},
]

async def seed():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120) as client:
        existing = {p["pack_id"] for p in (await client.get("/embeddings/packs")).json()["packs"]}

        for pack in PACKS:
            if pack["pack_id"] not in existing:
                await client.post("/embeddings/packs", json=pack)
                print(f"Created pack: {pack['pack_id']}")

        # Ingest corpus files: SEED_DIR/{pack_id}/*.txt
        for corpus_file in SEED_DIR.rglob("*.txt"):
            pack_id = corpus_file.parent.name
            content = corpus_file.read_text(encoding="utf-8")
            resp = await client.post("/embeddings/ingest", json={
                "pack_id": pack_id,
                "source_uri": str(corpus_file.name),
                "content": content,
                "metadata": {"source_label": corpus_file.stem},
            })
            data = resp.json()
            print(f"Ingested {data['chunks_stored']} chunks from {corpus_file.name} into {pack_id}")

asyncio.run(seed())
```

### 7.3 Corpus text files to create

Create plain text files in `seed/corpus/`:

`seed/corpus/borehole-operations/daily-drilling-log-fields.txt`
Key sections:
- 16 operation timestamps (Start Moving from, Reach Site, Start Drill 10.5", Temp. Casing Install, Start Drill 6.5", Reach Final Depth, PVC Installation, Gravel Packing, Development, Pump-Test/Start, Pump-Test/Finish, Leaving Site, plus 4 interruption/description rows)
- Summary fields: Movement(Km), Site Clearance, Final Depth(m), Screen Casing(m), Plain Casing(m), Temp. Casing depth(m), Bail Plug(m), Centralizer(pieces), Top Cap(unit), Gravel(m3), Development(hrs), Water level(m), Water yield(L/min), First water strike(m), Cement(bags)
- Hole results: Successful Hole, Marginal Hole, Dry Hole
- Geological Formation table fields: From(m), To(m), Comments

`seed/corpus/borehole-operations/formation-glossary.txt`
Key geological formations and characteristics:
- Laterite: weathered surface layer, reddish-brown, low yield risk
- Saprolite/weathered granite: partially weathered, moderate permeability
- Fresh basement (granite/gneiss): low primary porosity, fracture zones critical
- Shale: confining layer, poor aquifer
- Sandstone: sedimentary aquifer, moderate to high yield
- Alluvium: unconsolidated sediment, high yield near rivers

`seed/corpus/wrc-regulations/wrc-licence-categories.txt`
- Category A: large rigs, deep boreholes (greater than 60m), commercial operations
- Category B: medium rigs, boreholes 30-60m, institutional and community
- Category C: small rigs, shallow boreholes (under 30m), hand-pump domestic
- Licence format: WRC/WDL/[serial]/[year]
- Validity: 36 months from issue date
- L.I. 1827 governs all groundwater extraction and drilling activities in Ghana

`seed/corpus/gbda-guidelines/membership-stages.txt`
Stage 1: Registration approved by admin. Member receives Member ID. Member has read access to platform.
Stage 2: Annual dues paid plus ID card issued. Member has full forum access. Certificate of Membership generated.
Stage 3: WRC drilling licence registered through association. Member is Certified Driller.

`seed/corpus/gbda-guidelines/about-page.txt`
Content from the full GBDA About page: founded 2014, 6 member benefits, standards, advocacy and data collection mandate.

---

## 8. RAG pattern for ABBIS agents

When an ABBIS agent needs to answer a domain question, the standard pattern:

```typescript
// Agent calls search_domain_knowledge first
const context = await callTool("search_domain_knowledge", {
  query: userMessage,
  pack_id: "borehole-operations",
  top_k: 4,
})

// Then passes context to Claude
const prompt = context.found
  ? `Answer using this verified domain knowledge:\n${context.results.map(r => r.content).join("\n\n")}\n\nUser: ${userMessage}`
  : `Answer from general knowledge. Note: domain knowledge pack returned no results.\n\nUser: ${userMessage}`
```

Do not hard-code this pattern in one place; make it a composable helper in the keprix agent runtime.

---

## 9. Dependencies for wiring (main.py additions from 229)

```python
import asyncpg
from .providers.voyage_provider import VoyageProvider
from .providers.openai_provider import OpenAIEmbeddingProvider
from .services.embedding_service import EmbeddingService
from .config import settings

_db_pool: asyncpg.Pool | None = None
_embedding_svc: EmbeddingService | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db_pool, _embedding_svc
    configure_logging()
    await init_cache()
    _db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    if settings.primary_embedding_provider == "voyage":
        provider = VoyageProvider(settings.voyage_api_key)
    else:
        provider = OpenAIEmbeddingProvider(settings.openai_api_key)
    _embedding_svc = EmbeddingService(provider, _db_pool)
    yield
    await _db_pool.close()

async def get_embedding_service() -> EmbeddingService:
    return _embedding_svc
```

---

## 10. Acceptance criteria

1. `POST /embeddings/packs` creates a pack entry in the database
2. `POST /embeddings/ingest` with a 5,000-word document produces 10-12 chunks with stored embeddings
3. `POST /embeddings/search` with query "water yield in granite formations" returns the formation-glossary chunk with score >= 0.7
4. Calling `search_domain_knowledge` tool from a keprix agent returns a structured result with `found: true` and populated `results` array
5. Calling search twice returns the same result from Redis cache (verify with Redis monitor)
6. Re-ingesting the same source_uri replaces old chunks (no duplicates)
7. `DELETE /embeddings/packs/{pack_id}` removes pack and all associated chunks (cascade)
8. `GET /embeddings/packs` lists all four seeded packs with non-zero `chunk_count`
9. Seed script runs without error against a fresh database
10. All four seed packs are queryable before any ABBIS agent is started

---

## 11. Performance budget

- Single ingest call (1 page ~500 tokens): under 500ms
- Batch ingest (20 page document, ~10,000 tokens): under 10 seconds
- Search query: under 200ms (cold), under 30ms (cache hit)
- 100k vectors (HNSW index): search latency under 50ms
