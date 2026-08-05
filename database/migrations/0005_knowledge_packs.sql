CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS knowledge_packs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pack_id TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  description TEXT,
  embedding_model TEXT NOT NULL DEFAULT 'voyage-3',
  embedding_dims INTEGER NOT NULL DEFAULT 1024,
  chunk_count INTEGER NOT NULL DEFAULT 0,
  indexed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pack_id TEXT NOT NULL REFERENCES knowledge_packs(pack_id) ON DELETE CASCADE,
  source_uri TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  embedding vector(1024),
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
  ON knowledge_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS knowledge_chunks_pack_idx ON knowledge_chunks(pack_id);
CREATE INDEX IF NOT EXISTS knowledge_chunks_source_idx ON knowledge_chunks(pack_id, source_uri);
