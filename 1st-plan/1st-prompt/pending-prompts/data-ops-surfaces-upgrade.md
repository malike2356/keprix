# DATA ops surfaces: full upgrade prompt

**Status: COMPLETED 2026-08-07** (Must P0-P4 + `/data` tabs shipped; P5 Nice / P6 Ultimate deferred: not in this close; follow-up only with owner ask)  
Owner prompt for agents: upgrade these six keprix DATA nav items end-to-end.  
Nav source: `frontend/src/lib/navigation.ts` Data group.  
Do not ask clarifying questions unless blocked by missing credentials or destructive ops. Prefer defaults: keprix theme, real APIs, Docker deploy when UI ships, writing style (ASCII only: no em/en dashes, no emoji).


## What was built

- P0 Observability Must + Usage export/filters + nav icons (2026-08-02)
- P1 Local models Must (2026-08-02)
- P2 Video ingest Must (2026-08-02)
- P4 Analytics Must (2026-08-02)
- Data chrome unified on `/data?tab=` (2026-08-02)
- P3 RAG Must MUI shell, step timeline, file/vault sources (2026-08-07)
- Deferred: P5 Nice / P6 Ultimate (owner ask only)

## Surfaces in scope

| Nav label | Route | Baseline quality |
| --- | --- | --- |
| RAG Pipelines | `/rag-pipeline` | Real, thin operator form UI |
| Local models | `/playbook` | Real; naming confused with `/playbooks` |
| Video ingest | `/ingest/video` | Real; sparse job board |
| Analytics workspace | `/analytics` | Strongest DATA surface |
| LLM usage | `/usage` | Polished usage dashboard |
| Observability | `/observability` | Thin overview; overlaps Usage |

Related out of scope unless needed for deep links: Brain graph/health/Graphiti, Agent Runtime traces, Settings modules, admin `/dashboard/usage`.

---

## Cross-cutting must-haves (all six)

1. One visual system: MUI + keprix theme; kill Tailwind-only islands on these pages; match calm Brain chrome density.
2. Distinct icons per nav item (Observability must not reuse LLM usage bar-chart icon).
3. Page shells: short title, one-line purpose, primary actions, empty/error/loading states, deep-link refresh that survives hard reload.
4. Live job/status: polling or SSE for long-running work (model pull, video jobs, RAG runs).
5. Auth + workspace scoping: never use `"default"` user when JWT is present.
6. CSV/JSON export where the API already supports it; wire buttons in workspace UI, not only admin.
7. Accessibility: keyboard focus, contrast, no unlabeled icon-only controls.
8. Tests: Feature or Vitest smoke for API client + one happy-path UI test per surface when changing behavior.
9. Docs honesty: no claiming graph builders, OTEL full stack, or NL analytics beyond what ships.

---

## Cross-cutting nice-to-haves

1. Shared `DataSectionTabs` or breadcrumb group ("Data") so RAG / Models / Video / Analytics / Usage / Observability feel one product family.
2. Unified activity toast + notification for completed jobs.
3. Command palette entries for each surface.
4. Budget-aware warnings shared between Usage and Observability.
5. Dark/light contrast audit (same bar as Brain graph brightening).

---

## Cross-cutting ultimate best

1. Single **Ops home** (`/data` or `/ops`) with health cards that deep-link into each surface.
2. End-to-end provenance: video frame → RAG chunk → chat citation → usage event → trace span in one click chain.
3. Tenant-grade retention, export packs, and audit log for ingest + model serve + analytics artifacts.
4. On-call grade Observability: alerts, burn rates, SLO panels wired to real OTEL.

---

# 1. RAG Pipelines (`/rag-pipeline`)

## Baseline

Real API-backed UI: manual + Notion ingest, store pick, query, runs, eval chip, deployment-ready. Form-only builder; hardcoded `production-default`; mixed Tailwind/MUI; no file/folder ingest; traces are counts only.

Key files: `frontend/.../rag-pipeline/page.tsx`, `components/rag/*`, `lib/rag-pipeline-api.ts`, backend `/api/rag-pipeline/*`.

## Must-haves

1. MUI redesign: Pipeline list, open pipeline, Run panel, History.
2. CRUD or clear config for pipeline ids (drop silent hardcode or surface it as named env default).
3. Sources: manual, Notion, **local files / vault paths**, URL where backend allows.
4. Run viewer: step timeline (ingest → chunk → embed → retrieve → generate) with timings and errors.
5. Citations clickable to source preview.
6. Recent runs filter + replay last query.
7. Stores management: list, create/select store, show counts.
8. Empty/error states and deploy status explanation in plain language.

## Nice-to-haves

1. Visual DAG/pipeline builder (react-flow or canvas) instead of forms only.
2. Eval suite UI: golden questions, pass/fail @k, regression vs prior run.
3. Scheduled ingest + webhook Notion sync status.
4. A/B retrieve strategies (hybrid vs vector) side-by-side.
5. Export run transcript JSON.

## Ultimate best

1. Production RAG console: multi-pipeline, versioned prompts, canary deploys, rollback.
2. Chunk browser + re-index surgically.
3. Groundedness/hallucination scoring per answer.
4. Tie citations into Memory hub and Brain graph entities.

---

# 2. Local models (`/playbook`)

## Baseline

Hardware scan, fit scores, Pull/Serve, serving chips. No auto-scan, no pull progress, weak link to chat provider picker. Route `/playbook` vs automations `/playbooks` confuses operators.

## Must-haves

1. Rename product clarity: page title + nav already say Local models; add subtitle "hardware fit + Ollama/local serve" and banner link "Looking for Playbooks (automations)? → `/playbooks`".
2. Auto-scan on first visit (cached); refresh control.
3. Pull progress: job list with %, cancel if API allows, poll until done.
4. Serve/stop with health ping and copyable base URL.
5. "Use in chat" CTA that sets/selects the local provider/model in settings or chat model picker.
6. Failure reasons: VRAM short, disk short, daemon down, actionable fix steps.
7. Serving inventory always visible (even when scan empty).

## Nice-to-haves

1. Quantization picker (Q4/Q5/Q8) with RAM impact.
2. Benchmark smoke: latency tokens/sec after serve.
3. Multi-host / remote Ollama endpoint config.
4. Favorites / pin recommended models.
5. Route alias `/models/local` redirecting to `/playbook` (keep old path).

## Ultimate best

1. Model garden: catalog, license, tool-calling capability tags, GGUF provenance.
2. Auto-throttle under memory pressure; graceful unload.
3. Side-by-side local vs cloud quality + cost simulator for the same prompt.
4. One-click local offline mode for the whole workspace.

---

# 3. Video ingest (`/ingest/video`)

## Baseline

POST URL/path + frame mode + optional vault copy; job table; analyze-in-chat link. No upload widget, no polling, no preview, no retry/cancel.

## Must-haves

1. Poll jobs while status is queued/running; auto-refresh table.
2. Job detail drawer: status, frames count, manifest path, errors, created/updated.
3. Retry failed + cancel in-progress when backend supports; hide otherwise.
4. File picker / drag-drop for local files where API accepts upload or path.
5. Frame strip preview (thumbnails) when artifacts exist.
6. Transcript or caption panel if produced.
7. Clear "Open in chat" with prefilled analyze prompt and job id.
8. Mode explanations (caption-only → dense) in help text.

## Nice-to-haves

1. Playlist / batch URL queue.
2. Vault destination folder picker.
3. Progress percent and ETA.
4. OCR/gallery handoff (reuse Gallery OCR → Documents / Memory).
5. Webhook or notify when job completes.

## Ultimate best

1. Full media studio: seekable player synced to transcript + frame embeddings searchable in RAG.
2. Speakers/diarization, chapters, clip export.
3. Auto entity extraction into Temporal KG / Memory hub.
4. Cost/time estimator before submit.

---

# 4. Analytics workspace (`/analytics`)

## Baseline

Strongest DATA page: upload/paste, NL-ish questions, server Python, charts, sessions, jamovi export, research handoff. Intent is still template/regex limited; session labels are opaque; datasets not first-class.

## Must-haves

1. Human session titles (auto from filename + rename).
2. Dataset library: save named dataset, reopen, delete; not only anonymous session ids.
3. Broader question parsing or LLM planner with safe allowlisted pandas ops (still sandboxed).
4. Chart polish: theme-aware ApexCharts, export PNG/SVG, empty chart state.
5. Robust CSV (quoted commas) and clearer parse errors.
6. Sticky run history per session with re-run.
7. Workspace `/usage` style loading/error consistency.

## Nice-to-haves

1. SQL cell mode against the session frame.
2. Notebook export (ipynb) beside jamovi.
3. Collaborative share link (read-only) for a session.
4. Suggested next questions from column types.
5. Join two uploaded tables.

## Ultimate best

1. Full governed analytics: semantic layer, metric definitions, schedule refresh, alert on metric drift.
2. Agent that proposes analysis plans and executes with approval gates.
3. Direct write-back to Research workspace papers with figure captions.
4. PII detection before upload; redaction modes.

---

# 5. LLM usage (`/usage`)

## Baseline

Polished: period cards, timeseries, model/agent breakdowns, events, budget banner. Workspace CSV export missing; filters incomplete; budget edit elsewhere.

## Must-haves

1. Wire CSV/JSON export on workspace `/usage` (API already exists).
2. Filters: provider, model, agent/channel, user (admin only for user).
3. Clickable chart → filtered events table.
4. Budget panel: show limit, spend, soft/hard status; link to edit in settings; inline edit if permissioned.
5. Empty state when metering disabled explaining how to enable.
6. Fix any duplicate settings entry confusion with a single canonical "Usage" deep link.

## Nice-to-haves

1. Cost forecast to end of period.
2. Anomaly markers on timeseries.
3. Per-conversation cost from chat session page.
4. Saved views (e.g. "local only", "cloud only").
5. Compare two date ranges.

## Ultimate best

1. Chargeback by workspace/team with quotas and enforcement hooks.
2. Real-time stream of usage events.
3. Model router recommendations ("switch to X saves Y%").
4. Finance export packs (Stripe/accounting CSV).

---

# 6. Observability (`/observability`)

## Baseline

Dashboard cards + meter keys + recent traces linking to Agent Runtime. Thin, overlaps Usage, no inline spans, weak filters, breadcrumbs skewed to Settings.

## Must-haves

1. Reposition as **runtime health** (not spend): latency, error rate, trace volume, OTEL connected/disconnected with setup CTA.
2. Trace list: search, status filter, agent filter, time range; export button using existing API.
3. Inline span timeline drawer (waterfall) without forcing full Agent Runtime navigation; keep "Open full runtime" link.
4. Distinct nav icon (pulse/activity), not bar chart.
5. Breadcrumbs under Data, not Settings Modules.
6. Clear separation: Usage = money/tokens; Observability = reliability/traces.
7. Live refresh toggle (5s/15s/off).

## Nice-to-haves

1. Heatmap of errors by agent/tool.
2. Trace compare (two run ids).
3. Log tail correlated to trace id.
4. SLO widgets (availability, p95 latency) even if synthetic at first.
5. Alert rule stubs (email/webhook) persisted locally.

## Ultimate best

1. Full OTEL: traces + metrics + logs in one UI; Tempo/Prometheus-compatible export.
2. Incident mode: cluster failures, suspected root span, suggested rerun.
3. Continuous eval of agent quality tied to traces.
4. Multi-workspace ops console for admins.

---

## Suggested delivery order

| Phase | Focus | Why |
| --- | --- | --- |
| P0 | Observability Must + Usage export/filters + nav icons | Fast trust; stop confusion with Usage |
| P1 | Local models Must (progress, chat CTA, naming) | Unblocks offline story |
| P2 | Video ingest Must (poll, drawer, preview) | Jobs feel broken without polling |
| P3 | RAG Must (MUI shell, steps, file/vault source) | Core retrieval story |
| P4 | Analytics Must (datasets, titles, chart theme) | Raise already-good surface |
| P5 | Nice-to-haves across all | Depth |
| P6 | Ultimate best picks by ROI | Only with explicit go-ahead |

---

## Acceptance checklist (per surface when claimed done)

1. Hard-refresh works logged-in; no `"default"` data bleed.
2. Empty, loading, error, success paths verified manually.
3. At least one automated test or scripted API smoke for new behavior.
4. Docker frontend rebuild (and backend image commit if API changed) for local keprix.
5. Writing-style scan on touched first-party files.
6. Update this file status line when a phase ships (move bullets to "Done" with date).

---

## Implementation notes for agents

- Prefer extending existing `*-api.ts` clients over new ad-hoc `fetch`.
- Do not create Stripe prices or commit secrets.
- Do not nest Carina trees; keprix only under `/opt/lampp/htdocs/verlox/keprix`.
- When UI and API diverge, fix API if the contract is wrong; do not fake dashboards.
- For Observability span UI, reuse Agent Runtime trace payloads if present (`/api/observability/traces/{id}`).
- For Local models, inspect backend playbook routes before inventing progress endpoints; add progress if missing.
- Icon pass: update `navigation.ts` (and any icon map) so LLM usage ≠ Observability.

---

## Done log

- **P3 shipped 2026-08-07**: RAG Must (MUI `RagPipelinePanel` on `/data?tab=rag` with Known pipelines list + Run/History split, `PipelineBuilder` sources manual/Notion/file/vault/URL without silent `production-default` hardcode, stores list with run count labels, `PipelineRunViewer` step timeline + citation preview + filter/replay). Backend: file upload + vault/path ingest, store `count_label` runs. Tests: `tests/frontend/test_data_ops_p3.py` (5 passed).
- **Close note 2026-08-07**: P5 Nice-to-haves and P6 Ultimate are deferred (not in this close). Follow-up only with explicit owner ask.
- **P0 shipped 2026-08-02**: Observability Must (runtime health cards, filtered traces, span waterfall drawer, refresh 5s/15s/off, Data breadcrumbs, activity nav icon) + Usage Must (workspace CSV/JSON export with scoped auth, provider/model/channel/user filters, chart-click day filter, budget panel/banner, metering-disabled empty state, canonical Settings → `/usage`) + shared `DataSectionTabs` + `video` nav icon. Tests: `tests/frontend/test_data_ops_p0.py`, `tests/api/test_observability_dashboard.py`, extended usage export tests.
- **P1 shipped 2026-08-02**: Local models Must (rename + Playbooks banner, auto-scan cache, pull SSE progress jobs, serve/stop, health ping + copyable `/v1` URL, Use in chat via `keprix_selected_model`, failure hints, serving inventory always visible, Data tabs). Backend: `/api/playbook/serving/health`, JWT-aware user id.
- **P2 shipped 2026-08-02**: Video ingest Must (poll while active, job detail drawer, upload/drag-drop, frame strip via authenticated blob URLs, transcript panel, Open in chat with job id, mode help). Backend: `POST /api/ingest/video/upload`, `GET /api/ingest/video/{id}/frames/{index}`. Retry/cancel hidden (no API).
- **P4 shipped 2026-08-02**: Analytics Must (human session titles + rename, dataset library CRUD, broader question parsing, theme-aware ApexCharts with PNG/SVG export + empty chart state, quoted-comma CSV parse errors, sticky run history with re-run, Data tabs + `/usage`-style alerts). Backend: session title/rename, in-memory datasets, auto_repair run returns stdout/stderr, local executor captures print stdout. Tests: `tests/frontend/test_data_ops_p4.py`, `tests/analytics/test_code_interpreter_stdout.py`, `tests/analytics/test_session_titles_and_datasets.py`.
- **Data chrome unified 2026-08-02**: RAG / Local models / Video / Analytics / Usage / Observability live on one `/data?tab=` workspace with in-page tab switching (no full page hops). Legacy routes redirect into `/data`.
