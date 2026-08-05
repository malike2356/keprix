# keprix - Prompt 32: Combined Data, ML, Research, And Workspace Architecture

> **Status (2026-07-05):** Foundation shipped in `src/keprix/data_architecture/`, `jobs/`, `research_workspace/`, `ml_workspace/`, `stats/`, extended `data_plane/` routes, slash commands, tests in `tests/data_architecture/`, and docs at `docs/docs/architecture/data-planes.md`. Excel (`.xlsx`) and SPSS (`.sav`) import added in `data_plane/tabular_import.py` with optional `openpyxl` / `pyreadstat`. Full Postgres control-plane tables and hosted pgvector graph edges remain follow-up work.

## Purpose

Define keprix's final data and research workspace architecture by combining the strongest patterns from Carina itself and the adopted reference agents:

- OpenClaw-style database-first runtime architecture.
- Odysseus-style product and workspace schema breadth.
- Hermes-style concurrency and job safety.
- Aiva (commercial, separate product)-style SaaS, governance, Scout, billing, analytics, and production readiness.

This prompt makes keprix a core workspace on which any AI app can be built, including apps for machine learning, data analytics, deep research, Obsidian-style knowledge management, academic research, social science workflows, SPSS/PSPP/jamovi-style statistical analysis, operational dashboards, and vertical SaaS products.

## Core Decision

Carina should not copy one database model. It should combine the best parts:

- Use OpenClaw's split between global control-plane state and agent/workspace data-plane state.
- Use Odysseus's broad workspace entities for sessions, messages, documents, versions, files, email, notes, calendar, providers, tools, tasks, memory, integrations, webhooks, and user workspace assets.
- Use Hermes's concurrency model for agent work queues: WAL where SQLite is used, `BEGIN IMMEDIATE`, compare-and-swap claiming, stale claim recovery, bounded worker context, integrity checks, and corruption backup.
- Use Carina's production layer for multi-tenant SaaS, billing, analytics, audit, governance, role enforcement, Scout, and app-building workflows.

## Architecture Shape

Build the storage layer as four cooperating planes.

### 1. SaaS Control Plane

Use Postgres for multi-tenant, commercial, and governed platform state:

- Tenants.
- Workspaces.
- Users.
- Roles.
- Invitations.
- Products.
- Plans.
- Subscriptions.
- Billing events.
- Usage events.
- Analytics events.
- Entitlements.
- Audit logs.
- Policy.
- App registry.
- Plugin registry.
- Workspace configuration.
- Scout enrollment metadata.
- Compliance records.

This is the system of record for hosted SaaS and any managed commercial product.

### 2. Agent And Workspace Data Plane

Use a per-workspace or per-agent SQLite data plane for local-first runtime state:

- Agent sessions.
- Transcript event streams.
- Tool artifacts.
- Scratch workspace files.
- Runtime cache.
- Local automation state.
- Local model catalog.
- Local task queues.
- Local research notebook state.
- Offline-first knowledge graph snapshots.
- User-owned work in self-host mode.

The data plane must be portable, backup-friendly, and able to run without a managed cloud.

### 3. Analytical And Research Plane

Use columnar and statistical formats for analysis workloads:

- DuckDB for local analytical SQL over CSV, Parquet, JSON, Excel, SQLite, and Postgres exports.
- Parquet for durable analytical datasets and research exports.
- Arrow for in-memory tabular exchange.
- Polars and pandas adapters for Python analysis.
- R integration where practical for specialist statistical packages.
- PSPP export/import for open SPSS-compatible workflows.
- jamovi export/import through supported tabular formats and metadata.
- SPSS `.sav` import/export through a safe optional bridge where licensing and environment allow it.
- Jupyter notebook export for reproducible analysis.
- HTML, PDF, DOCX, Markdown, and Quarto-style report export.

This plane lets Carina act as a research and data-analysis workspace, not only a chat agent.

### 4. Memory And Retrieval Plane

Use a dedicated retrieval layer:

- Postgres `pgvector` for hosted workspace memory and SaaS-scale RAG.
- SQLite vector extension or LanceDB for local-first memory where practical.
- Qdrant or another vector database as an optional external provider.
- Full-text search for notes, transcripts, documents, research material, and Obsidian-style vaults.
- Graph relationships for people, documents, claims, citations, datasets, tools, tasks, and research findings.

The retrieval plane must separate source material, embeddings, claims, citations, generated summaries, and user-approved knowledge.

## Output Paths

Use these target paths unless the codebase evolves before implementation:

```text
keprix/backend/data_architecture/
  __init__.py
  control_plane.py
  data_plane.py
  research_plane.py
  retrieval_plane.py
  schemas.py
  migrations.py
  backup.py
  integrity.py
  exports.py

keprix/backend/jobs/
  __init__.py
  queue.py
  claims.py
  workers.py
  leases.py
  retries.py
  heartbeats.py
  dead_letter.py
  audit.py
  schemas.py

keprix/backend/research_workspace/
  __init__.py
  projects.py
  sources.py
  citations.py
  claims.py
  literature_review.py
  notebooks.py
  obsidian.py
  datasets.py
  statistical_packages.py
  reports.py
  exports.py

keprix/backend/ml_workspace/
  __init__.py
  datasets.py
  features.py
  experiments.py
  model_registry.py
  evaluation.py
  pipelines.py
  notebooks.py
  artifacts.py
  governance.py

keprix/tests/data_architecture/
keprix/tests/jobs/
keprix/tests/research_workspace/
keprix/tests/ml_workspace/
```

## Database Selection Rules

Use the right database for the job:

| Need | Default |
| --- | --- |
| Hosted SaaS records | Postgres |
| Local-first runtime state | SQLite |
| Local analytical queries | DuckDB |
| Hosted vector memory | Postgres with pgvector |
| Local vector memory | SQLite vector extension or LanceDB |
| Large analytical datasets | Parquet |
| Streaming analytics | Append-only events with rollups |
| Temporary computation | Arrow, Polars, pandas |
| Full-text search | Postgres FTS or SQLite FTS5 depending on plane |
| Research graph | Relational edges first, graph export optional |

Do not force every workload into one database. The platform should present one coherent API while using the right storage engine underneath.

## Control Plane Contract

The control plane must expose canonical IDs for:

- `tenant_id`
- `workspace_id`
- `app_id`
- `agent_id`
- `user_id`
- `session_id`
- `dataset_id`
- `research_project_id`
- `job_id`
- `artifact_id`
- `source_id`
- `claim_id`
- `citation_id`

All data-plane and research-plane records must be traceable back to these IDs where applicable.

## Data Plane Contract

Each workspace or agent data plane must include:

- `sessions`
- `transcript_events`
- `workspace_files`
- `artifacts`
- `cache_entries`
- `local_jobs`
- `local_job_events`
- `notebooks`
- `research_sources`
- `research_claims`
- `research_citations`
- `dataset_catalog`
- `dataset_versions`
- `ml_experiments`
- `ml_runs`
- `ml_artifacts`

Data-plane files must be portable. A self-hosted user should be able to back up one workspace and restore it elsewhere.

## Hermes-Style Job Concurrency

Build job queues using Hermes concurrency lessons:

- Use explicit claim tokens.
- Use compare-and-swap updates when claiming jobs.
- Use `BEGIN IMMEDIATE` for SQLite write transactions.
- Use Postgres row locks or advisory locks for hosted queues.
- Use worker heartbeats.
- Reclaim stale jobs safely.
- Track retry counts.
- Track consecutive failures.
- Send exhausted jobs to a dead-letter state.
- Keep bounded job context so long task histories do not flood prompts.
- Store job events append-only.
- Record worker identity, model, toolset, environment, and cost.
- Never run destructive jobs without authorization and confirmation.

Job types must include:

- Agent task.
- Deep research task.
- Data import.
- Data cleaning.
- Statistical analysis.
- ML training.
- Model evaluation.
- Report generation.
- Obsidian vault sync.
- Embedding refresh.
- SaaS billing rollup.
- Analytics rollup.
- Scout governance check.

## Odysseus-Style Workspace Breadth

The data model must support the full user workspace:

- Chat sessions and messages.
- Documents and immutable document versions.
- Notes and note links.
- Calendar events.
- Email accounts and message references.
- Attachments.
- Media gallery.
- Model providers and endpoints.
- API tokens.
- Webhooks.
- User-created tools.
- Tool data.
- Scheduled tasks.
- Task runs.
- Memory records.
- Integrations.
- Signatures and forms where relevant.
- Research projects.
- Datasets.
- Reports.

Keep user-owned content separate from generated summaries and agent cache.

## OpenClaw-Style Database-First Runtime

Runtime must use database identity, not file paths, as the active source of truth:

- Sessions use `{workspace_id, agent_id, session_id}`.
- Transcripts are database event rows.
- Runtime cache is database-backed.
- Active tasks are database rows.
- Legacy files are import sources only.
- Exported files are artifacts, not runtime identity.
- Doctor/import tools handle old file formats.

Do not pass pseudo-locators through runtime protocols. If a file is exported for Obsidian, Jupyter, PSPP, jamovi, or a report, it remains an export artifact, not the canonical runtime record.

## Deep Research Workspace

Research must be structured around provenance:

- Research project.
- Research question.
- Source.
- Extract.
- Claim.
- Evidence.
- Citation.
- Confidence.
- Contradiction.
- Research note.
- Dataset.
- Analysis output.
- Final report.

The deep research engine must store:

- Original source URL or file reference.
- Retrieval timestamp.
- Extracted quote spans where legally allowed.
- Paraphrased notes.
- Citation metadata.
- Model-generated claims.
- Human-approved claims.
- Conflicting evidence.
- Research gaps.
- Reproducibility metadata.

Every final answer should be traceable back to sources and intermediate reasoning artifacts without exposing private chain-of-thought.

## Obsidian Integration

Build an Obsidian-compatible knowledge workspace:

- Import Markdown vaults.
- Export research projects as Markdown vaults.
- Preserve wikilinks.
- Preserve tags.
- Preserve frontmatter.
- Generate literature notes.
- Generate evergreen notes.
- Generate source notes.
- Generate claim notes.
- Generate dataset notes.
- Generate daily notes where configured.
- Sync without overwriting user edits.
- Detect conflicts.
- Store backlinks in the retrieval plane.

Obsidian files are user-facing knowledge artifacts. Canonical runtime state remains in the database.

## Statistical Package Integration

Support workflows for SPSS, PSPP, jamovi, JASP, R, Python, and spreadsheet users.

Implement:

- CSV import/export.
- Excel import/export.
- Parquet import/export.
- JSON and JSONL import/export.
- SPSS `.sav` import where supported by installed optional libraries.
- SPSS `.sav` export where supported and legally safe.
- PSPP-compatible syntax export.
- R script export.
- Python notebook export.
- jamovi-compatible data export through supported formats.
- Variable labels.
- Value labels.
- Missing value metadata.
- Measurement levels.
- Weights.
- Filters.
- Derived variables.
- Recode rules.
- Analysis log.

The agent should be able to say:

- "Import this SPSS file and summarize the variables."
- "Run descriptive statistics on this dataset."
- "Create a codebook."
- "Compare these groups."
- "Run a regression and explain the result."
- "Export this to PSPP syntax."
- "Prepare this dataset for jamovi."
- "Create an Obsidian research vault from this analysis."

Regulated or high-stakes analysis must include warnings, assumptions, and human review gates.

## Machine Learning Workspace

Add an ML workspace that supports:

- Dataset catalog.
- Dataset versions.
- Feature definitions.
- Train, validation, and test splits.
- Experiment tracking.
- Model registry.
- Evaluation metrics.
- Bias and drift checks.
- Cost tracking.
- Reproducibility metadata.
- Artifact storage.
- Notebook export.
- Pipeline runs.
- Human approval before deployment.
- Scout governance hooks for risky models.

The ML layer must support common task types:

- Classification.
- Regression.
- Clustering.
- Forecasting.
- Ranking.
- Text classification.
- Embedding generation.
- Retrieval evaluation.
- Fine-tuning preparation where safe and legally allowed.

Do not train on private or customer data without explicit workspace policy and audit records.

## Data Analytics Workspace

Add analytics workflows for:

- Data profiling.
- Data cleaning.
- Deduplication.
- Missing value analysis.
- Outlier detection.
- Data joins.
- Pivot tables.
- Charts.
- Cohort analysis.
- Funnel analysis.
- Retention analysis.
- Revenue analysis.
- Survey analysis.
- Field research analysis.
- Operational reporting.

The agent should generate:

- Reproducible analysis plans.
- SQL queries.
- Python notebooks.
- R scripts.
- Plain-language findings.
- Charts.
- Data dictionaries.
- Reports.
- Export packages.

Every analysis result must carry input dataset version, transformation steps, and generated artifact IDs.

## API Surface

Expose:

```text
GET  /api/data/planes/status
GET  /api/data/catalog
POST /api/data/import
POST /api/data/export
GET  /api/data/datasets
POST /api/data/datasets
GET  /api/data/datasets/{dataset_id}/versions
POST /api/jobs
GET  /api/jobs
POST /api/jobs/{job_id}/claim
POST /api/jobs/{job_id}/heartbeat
POST /api/jobs/{job_id}/complete
POST /api/jobs/{job_id}/fail
GET  /api/research/projects
POST /api/research/projects
POST /api/research/projects/{project_id}/sources
POST /api/research/projects/{project_id}/claims
GET  /api/research/projects/{project_id}/citations
POST /api/research/projects/{project_id}/export/obsidian
POST /api/stats/import
POST /api/stats/analyze
POST /api/stats/export
GET  /api/ml/datasets
POST /api/ml/experiments
GET  /api/ml/experiments
POST /api/ml/runs
GET  /api/ml/model-registry
```

All APIs require authentication. Dataset import, external research, ML training, and destructive data operations require explicit permission checks and audit.

## Agent-Operated Workflows

The agent must support instructions like:

- "Create a research project for this topic and build an Obsidian vault."
- "Import this CSV, profile it, and tell me what is wrong with the data."
- "Convert this SPSS file to a PSPP-compatible workflow."
- "Prepare this survey dataset for jamovi."
- "Run descriptive statistics and export a codebook."
- "Run a deep research review and link every claim to citations."
- "Train a baseline classifier and compare it with logistic regression."
- "Create a DuckDB analysis database for these Parquet files."
- "Schedule a nightly data quality check."
- "Show all failed jobs and why they failed."
- "Export this research project as Markdown, PDF, and CSV appendices."

The agent may perform setup, analysis, and export, but must ask for confirmation before:

- Deleting data.
- Overwriting user notes.
- Publishing reports.
- Sending data to cloud providers.
- Training on private data.
- Charging external APIs.
- Running expensive jobs.
- Sharing data with collaborators.

## Slash Commands

Prompt 23 owns the slash command registry. Add these commands:

| Command | Purpose |
| --- | --- |
| `/data import` | Start guided data import. |
| `/data profile <dataset>` | Profile a dataset. |
| `/data export <dataset>` | Export a dataset. |
| `/jobs` | Show active and failed jobs. |
| `/jobs retry <job>` | Retry a failed job after confirmation. |
| `/research project` | Create or show a research project. |
| `/research export obsidian <project>` | Export a project to an Obsidian vault. |
| `/stats describe <dataset>` | Run descriptive statistics. |
| `/stats codebook <dataset>` | Generate a codebook. |
| `/ml experiment <dataset>` | Start an ML experiment. |
| `/ml runs` | Show ML experiment runs. |

Sensitive outputs must be private or ephemeral in shared channels.

## Tests

Add tests for:

- Control-plane IDs link correctly to data-plane records.
- SQLite data plane can be backed up and restored.
- Postgres control-plane records can locate a workspace data plane.
- Job claiming allows only one worker to claim a job.
- Stale job claims are reclaimed safely.
- Failed jobs move to dead-letter after retry limit.
- Job context is bounded.
- Data import creates dataset version records.
- CSV, Excel, JSONL, and Parquet import work.
- SPSS or PSPP import is skipped cleanly when optional dependencies are missing.
- Variable labels and value labels survive supported statistical imports.
- Obsidian export preserves frontmatter, tags, wikilinks, and backlinks.
- Deep research claims link to sources and citations.
- Analytics outputs include dataset version and transformation lineage.
- ML experiment runs store metrics, artifacts, and parameters.
- Private data cannot be sent to a cloud provider when policy blocks it.
- Destructive data operations require confirmation.
- Audit records exist for imports, exports, ML training, external research, and destructive actions.

## Acceptance Criteria

- keprix has a documented four-plane data architecture.
- Hosted SaaS state uses a control-plane database.
- Local-first agent state uses a portable data-plane database.
- Analytics and research workloads use analytical formats and engines instead of forcing everything into one OLTP schema.
- Retrieval and memory are separated from source material and generated summaries.
- Job concurrency follows Hermes-style claim, heartbeat, retry, and recovery patterns.
- Workspace breadth follows Odysseus-style documents, sessions, email, calendar, tools, tasks, integrations, and memory.
- Runtime identity follows OpenClaw-style database-first contracts, not active file paths.
- Deep research is provenance-first and citation-aware.
- Obsidian vault import and export are supported as knowledge artifacts.
- SPSS, PSPP, jamovi, R, Python, spreadsheet, and Parquet workflows are supported through safe optional adapters.
- Machine learning workflows support datasets, experiments, model registry, evaluation, artifacts, and governance.
- All risky data, finance, external API, and ML operations obey the seven engineering pillars.
