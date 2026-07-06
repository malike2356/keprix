# Four-plane data architecture

Keprix separates storage into four cooperating planes.

## 1. SaaS control plane

Postgres when `DATABASE_URL` is configured; otherwise a local registry at `~/.keprix/control_plane/registry.json`.

Holds tenant and workspace metadata that links hosted SaaS records to portable workspace data planes.

## 2. Agent and workspace data plane

SQLite per workspace at `~/.keprix/workspaces/{workspace_id}/data_plane.sqlite`.

Stores sessions, transcript events, local jobs, research projects, dataset versions, and ML experiments. Portable via file copy backup.

## 3. Analytical and research plane

DuckDB (with SQLite fallback) for CSV and Parquet imports under `~/.keprix/data_plane/`.

Used for profiling, SQL queries, and statistical workflows.

## 4. Memory and retrieval plane

Hosted vector memory uses Postgres pgvector when configured. Local retrieval defers to the existing memory/RAG modules in `src/keprix/memory/`.

## API entry points

- `GET /api/data/planes/status`
- `GET /api/data/catalog`
- `POST /api/data/import` and `POST /api/data/export`
- `GET /api/data/datasets/{dataset_id}/versions`
- `POST /api/jobs` and job claim/heartbeat/complete/fail routes
- `GET/POST /api/research/projects/*`
- `POST /api/stats/import`, `/analyze`, `/export`
- `GET/POST /api/ml/*`

## Job concurrency

Local jobs use SQLite `BEGIN IMMEDIATE` compare-and-swap claims, worker heartbeats, stale reclaim, retries, and dead-letter state.

## Runtime identity

Canonical records use database IDs (`session_id`, `dataset_id`, `job_id`, `research_project_id`). Exported Markdown, Obsidian vaults, notebooks, and reports are artifacts, not runtime identity.
