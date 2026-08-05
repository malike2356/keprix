# RAG admin

Operator UI (primary): `/data?tab=rag` uses `/api/rag-pipeline`.

Facade for operators/scripts: `GET/POST /api/rag-admin/pipelines|ingest` calls the real `RagPipeline` registry (not an in-memory stub).

Training: unsupported in CE; the admin payload reports `training.supported=false`.
