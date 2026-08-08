# Keprix - Prompt 149: Mutation Engine Architecture Reference

## Purpose

This is the **reference and dependency map** for the full Keprix mutation engine.
Build through Prompts **150-155** in numeric order. **Do not archive this file.**
It is the source of truth for cross-prompt acceptance criteria and wiring decisions.

Prompt 149 is documentation only. It does not ship code. Update this file when
Prompts 150-155 land so later work does not re-discover the same gaps.

---

## Implementation status (2026-07-06)

| Area | Status | Location |
| --- | --- | --- |
| Tier 1 tool synthesis (core) | **Shipped** (Prompts 28, 139-143) | `src/keprix/agent/keprix/` |
| Tier 1 chat E2E + pause-until-approve | **Shipped** (Prompts 141-143) | `mutation_hook.py`, `mutation_wait.py`, `web_ui_stream.py` |
| Tier 1 admin + in-chat UI | **Shipped** (Prompts 136-137, 155) | `MutationCard`, `/dashboard/mutation` |
| Soft mutation (skills, run analysis) | **Shipped** (pre-149) | `improvement/`, `skill_manager_tool.py` |
| Canonical `mutation_events` DB | **Shipped** (Prompt 150) | `src/keprix/mutation/store.py`, migration 016 |
| Improvement-to-mutation wiring | **Shipped** (Prompt 151) | `mutation/hook.py`, `improvement/routes.py` |
| Tier 2 prompt/persona mutation | **Shipped** (Prompt 152) | `prompt_store.py`, migration 017 |
| Tier 3 scoped self-coding on Keprix | **Shipped** (Prompt 153) | `self_coding_*.py`, `/api/mutation/code/*` |
| Tier 4 quality / compounding / prune | **Shipped** (Prompt 154) | `quality.py`, `pruner.py`, `compounding.py` |
| Unified governance UI (all tiers) | **Shipped** (Prompt 155) | `/dashboard/mutation`, `components/mutation/` |

**Package note:** Tier 1 lives in `src/keprix/agent/keprix/`, not `src/keprix/mutation/`.
Prompts 150-155 should **extend** that package for tool concerns and add
`src/keprix/mutation/` only for cross-tier store, quality, compounding, and
unified REST (`/api/mutation/*`). Do not duplicate synthesiser, sandbox, or
approval logic under a second tree.

---

## What "Mutation" Means Here

Mutation is the ability of a running Keprix deployment to change its own
capabilities, instructions, and code in response to tasks it attempts, failures
it encounters, and feedback it receives; and for those changes to persist and
compound across sessions.

There are four distinct mutation tiers. Each has its own prompt.

| Tier | What mutates | Prompt | Status |
| --- | --- | --- | --- |
| 1 | Tools: synthesize new Python tools on capability gap | 150, 151 | Core shipped; DB, schema inference, improvement wiring remain |
| 2 | Prompts and personas: system instructions evolve from run analysis | 152 | Proposals only (`prompt_improver.py`) |
| 3 | Own codebase: coding agent modifies keprix source in governed scopes | 153 | External repos only today (`coding/`) |
| 4 | Quality and compounding: score, prune, accumulate per deployment | 154 | In-memory quarantine only (`tool_health.py`) |
| UI | Operator visibility and control over all four tiers | 155 | Tool queue shipped; full tier tabs not built |

---

## Dependencies (archived)

| Prompt | Capability |
| --- | --- |
| 28 | Mutation engine core: gap, synthesise, sandbox, approval, install |
| 51 | Durable playbook runtime |
| 55 | Self-coding patch trajectories: `coding/repo_map.py`, `coding/patcher.py`, `coding/issue_runner.py` |
| 57 | Evals and trace observability |
| 08 | Vault and credentials |
| 116 | UI foundation |
| 136 | Workspace shell, `MutationCard`, NDJSON stream consumer |
| 137 | Admin mutation queue (`/dashboard/mutations`) |
| 139 | Chat mutation bridge, `tool_inventory.py` (sidecar; off by default) |
| 140 | Gap detector LLM classifier + demo patterns (`track_time`) |
| 141 | Approve retry + chat follow-up (`KeprixRetry`, session message) |
| 142 | WEB_UI gateway NDJSON stream (`dispatch_stream`, `web_ui_stream.py`) |
| 143 | Agent loop mutation hook on tool miss (`mutation_hook.py`) |

See also: `138-chat-mutation-e2e-wiring-outline.md` for the `/chat` wiring map.

---

## Current State - What Exists

### Tier 1: Tool synthesis (`src/keprix/agent/keprix/`) - working

| File | What it does | Status |
| --- | --- | --- |
| `mutation.py` | `MutationEngine`: gap, synthesise, static scan, sandbox, audit, approval cycle | Working |
| `gap_detector.py` | Regex fast-paths + optional LLM classifier | Working (demo paths: stock, time) |
| `gap_classifier_prompt.py` | LLM messages/parser for gap classification | Working |
| `synthesiser.py` | LLM tool generation + offline fallbacks | Working |
| `synthesiser_prompt.py` | Synthesis prompts; emits `toolset="generated"` | Working |
| `static_analyser.py` / `ast_analyser.py` | AST and import safety scan | Working |
| `sandbox.py` | Docker if available, else local subprocess; seccomp profile | Working |
| `store.py` | `GeneratedToolStore` (JSON file, not Postgres `mutation_events`) | Working |
| `auditor.py` | Status: pending, approved, rejected, installed | Working |
| `approval.py` / `approval_gate.py` | Multi-channel approval + install + retry | Working |
| `installer.py` | Writes tool files; calls `registry.reload_generated_tools()` | Working |
| `tool_signer.py` | Ed25519 sign/verify for generated tools | Working |
| `namespace.py` | Blocks keprix-internal imports in generated code | Working |
| `tool_health.py` | In-memory error-rate quarantine for `toolset="generated"` | Partial |
| `tool_inventory.py` | Registry + installed records for gap detection | Working |
| `tool_dispatch.py` | Structured tool-miss results for agent loop | Working |
| `retry.py` | Re-run original task after install | Partial (demo tools well covered) |
| `mutation_hook.py` | Tool-miss hook, stream events, optional approval wait | Working |
| `mutation_wait.py` | Cooperative wait/signal during open chat streams | Working |
| `chat_mutation_bridge.py` | Legacy sidecar (opt-in: `KEPRIX_CHAT_MUTATION_SIDECAR`) | Working |
| `governance.py` | Kill switch, workspace lock, policy feature flag | Working |
| `config.py` / `schemas.py` | Env config and dataclasses | Working |
| `routes.py` | `/api/agent/tools/generated/*` | Working |
| `skill_registry.py` | Counts `.skill` files on install | Skeleton |

**Wiring (chat path, default):**

```
POST /api/conversations/{id}/messages
  -> _stream_assistant_reply (KEPRIX_CHAT_GATEWAY_STREAM=true)
  -> registry.dispatch_stream(WEB_UI)
  -> iter_web_ui_gateway_stream
  -> run_agent_loop_mutation_turn (mutation_hook)
       -> evaluate_turn_tool_miss
       -> handle_tool_miss_stream
            -> register_mutation_wait_now (if approval + stream wait)
            -> NDJSON event: mutation
            -> wait_for_mutation_resolution (if KEPRIX_MUTATION_STREAM_WAIT_APPROVAL=true)
            -> KeprixRetry in same stream turn
  -> map_gateway_event_to_ndjson -> client
User: Approve on MutationCard
  -> POST /api/mutations/{id}/approve?session_id=...
  -> has_active_mutation_wait before engine.approve
  -> stream_waiting: true, retry_message: null
  -> signal_mutation_resolved -> stream resumes
```

Live smoke: `scripts/smoke-chat-mutation-e2e.py`

### Soft mutation (working)

| File | What it does | Status |
| --- | --- | --- |
| `tools/skill_manager_tool.py` | Agent creates/edits/deletes SKILL.md procedural memory | Working |
| `improvement/run_analyzer.py` | Analyzes completed runs; `ImprovementProposal` | Working |
| `improvement/feedback_collector.py` | User correction signals | Working |
| `improvement/monitoring.py` | Improvement metrics | Working |

### Parallel / not wired to Tier 1 engine

| File | What it does | Gap |
| --- | --- | --- |
| `improvement/tool_gap_detector.py` | `ToolGapProposal` from runs | Detects only; does not call `MutationEngine.run_cycle` |
| `improvement/prompt_improver.py` | Prompt edit suggestions | String proposals; never persisted or applied |
| `improvement/routes.py` | `/api/improvement/*` | Returns tool gaps JSON; no synthesizer hook |
| `extensions/registry.py` | Runtime extension loading | Not used for mutation |

### Registry and hot-reload

| Item | Status |
| --- | --- |
| `tools/registry.py` `reload_generated_tools()` | **Called** from `installer.py` on install and remove |
| `toolset="generated"` | Synthesiser registers; dispatch tracks health/quarantine |
| Startup reload on API boot | **Not implemented** (Prompt 150) |
| Reload after staged synthesis (pre-approval) | **Not implemented** (by design; approval gates install) |

### Self-coding (`src/keprix/coding/`) - external repos only

`issue_runner.py`, `patcher.py`, `git_workflow.py`, `lint_test_runner.py`, and
`/api/coding/*` implement a full patch loop against an arbitrary `repo_path`.
There is no governed allowlist for Keprix source paths, no mutation branch model,
and no hard block on `security/`, `vault/`, `auth/`, `review_gateway/`, `billing/`.

### Frontend (Tier 1)

| Path | Role | Status |
| --- | --- | --- |
| `frontend/src/components/workspace/blocks/MutationCard.tsx` | In-chat approve/reject | Working |
| `frontend/src/app/(admin)/dashboard/mutations/` | Admin queue + detail | Working |
| `frontend/src/components/admin/RecentMutations.tsx` | Dashboard widget | Working |
| `frontend/src/app/(workspace)/admin/tools/page.tsx` | Generated tools table | Working |
| `frontend/src/lib/workspace-api.ts` | `/api/mutations/{id}/approve\|reject` | Working |
| `frontend/src/lib/admin-workspace-api.ts` | `/api/agent/tools/generated` | Working |

Prompt 155 target `/dashboard/mutation` (singular, all tiers) **does not exist**.
Extend rather than replace `/dashboard/mutations` unless 155 explicitly migrates routes.

### API surface (today)

| Route | Module | Notes |
| --- | --- | --- |
| `POST /api/mutations/{id}/approve` | `conversation_routes.py` | Chat approve + `stream_waiting` |
| `POST /api/mutations/{id}/reject` | `conversation_routes.py` | Chat reject + stream signal |
| `GET /api/mutations` | `dashboard_routes.py` | Recent list (JSON store) |
| `GET/POST /api/agent/tools/generated/*` | `agent/keprix/routes.py` | CRUD, cycle, approve/reject |
| `GET /api/stats/mutations/approved` | `stats_routes.py` | Counts by status |
| `POST /api/improvement/runs` | `improvement/routes.py` | Returns `tool_gaps` only |

Prompts 150-155 add unified `/api/mutation/*` (singular) for cross-tier governance.
Keep existing routes for backward compatibility until 155 migration is explicit.

### Tests (today)

```
tests/mutation/test_mutation_engine.py
tests/mutation/test_gap_detector.py
tests/mutation/test_synthesiser.py
tests/mutation/test_agent_loop_mutation.py
tests/mutation/test_retry.py
tests/mutation/test_hardening.py
tests/mutation/test_tool_inventory.py
tests/api/test_chat_mutation_stream.py
tests/api/test_chat_mutation_e2e_wait.py
tests/api/test_mutation_approve_retry.py
scripts/smoke-chat-mutation-e2e.py   # live integration smoke
```

### Database

| Artifact | Status |
| --- | --- |
| `migrations/versions/007_generated_tools.py` | Postgres `generated_tools` table; **not wired** to `GeneratedToolStore` (JSON file) |
| `015_mutation_store.py` (`mutation_events`, `mutation_quality_samples`) | **Not built** (Prompt 150) |

---

## Target Architecture

Annotations: **[S]** shipped, **[P]** partial, **[ ]** not built.

```
TIER 1: TOOL SYNTHESIS [S/P]
  task fails or tool gap detected
    -> agent/keprix/gap_detector.py [S]
    -> agent/keprix/synthesiser.py [S]
    -> agent/keprix/sandbox.py [S]
    -> agent/keprix/store.py (JSON) [S]  ->  mutation/store.py (DB) [ ]
    -> registry.reload_generated_tools() on install [S]; on startup [ ]
    -> operator approval gate [S]; stream wait [S]
    -> improvement/tool_gap_detector.py -> MutationEngine [ ]  (Prompt 151)

TIER 2: PROMPT AND PERSONA MUTATION [ ]
  run analysis -> prompt_improver.py [P: proposals only]
    -> mutation/prompt_store.py [ ]
    -> operator review or auto-apply [ ]
    -> next session loads mutated prompt [ ]

TIER 3: SCOPED SELF-CODING [ ]
  coding agent scoped to allowlist paths [ ]
    -> mutation branch (not main) [ ]
    -> test gate + operator approval [ ]
    -> mutation_events record [ ]

TIER 4: COMPOUNDING AND QUALITY [ ]
  mutation/quality.py, compounding.py, pruner.py [ ]
    -> mutation_quality_samples [ ]
    -> promote / quarantine / prune [ ]
    -> deployment divergence metrics [ ]
```

---

## Mutation Store Schema (canonical target)

Used by Prompts 150, 151, 152, 153, 154. **Not implemented yet.**

Today, tool records live in `{KEPRIX_GENERATED_TOOLS_DIR}/../mutation/generated_tools.json`
via `GeneratedToolStore`. Prompt 150 must migrate or dual-write into this schema.

```sql
CREATE TABLE mutation_events (
    id            TEXT PRIMARY KEY,
    recorded_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    workspace_id  TEXT NOT NULL,
    tier          TEXT NOT NULL,   -- tool | prompt | persona | code
    trigger       TEXT NOT NULL,   -- gap_detected | run_failure | user_correction | operator | eval_low
    status        TEXT NOT NULL,   -- staged | approved | rejected | rolled_back | pruned
    name          TEXT NOT NULL,   -- tool name, prompt key, persona id, file path
    description   TEXT,
    source_code   TEXT,            -- for tools and code mutations
    before_value  TEXT,            -- for prompt/persona mutations
    after_value   TEXT,            -- for prompt/persona mutations
    approved_by   TEXT,            -- null = auto-approved
    approved_at   TIMESTAMP,
    quality_score FLOAT,           -- updated after each use
    use_count     INT DEFAULT 0,
    last_used_at  TIMESTAMP,
    rollback_of   TEXT REFERENCES mutation_events(id),
    metadata      JSONB DEFAULT '{}'
);

CREATE TABLE mutation_quality_samples (
    id              TEXT PRIMARY KEY,
    mutation_id     TEXT NOT NULL REFERENCES mutation_events(id),
    sampled_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    task_id         TEXT,
    run_id          TEXT,
    outcome         TEXT NOT NULL,  -- success | failure | partial
    score           FLOAT,
    feedback        TEXT
);
```

**Migration file:** `migrations/versions/015_mutation_store.py`

**Bridge strategy (Prompt 150):** `MutationStore` wraps DB; `GeneratedToolStore`
becomes adapter or is retired after dual-write period. Do not break
`/api/agent/tools/generated` or `/api/mutations` until 155 documents migration.

---

## Configuration Flags

### Shipped (in `.env.example` and `config.py`)

```bash
KEPRIX_MUTATION_ENABLED=true
KEPRIX_GENERATED_TOOLS_DIR=~/.keprix/generated/tools
KEPRIX_GENERATED_SKILLS_DIR=~/.keprix/generated/skills
KEPRIX_SANDBOX_TIMEOUT=30
KEPRIX_GAP_CONFIDENCE=0.7
KEPRIX_MUTATION_ADMIN_CHANNEL=web
KEPRIX_MUTATION_MAX_RETRIES=2
KEPRIX_MUTATION_REQUIRED_CHANNELS=web_ui,telegram
KEPRIX_MUTATION_REQUIRE_APPROVAL=true
KEPRIX_TOOL_SIGNING_KEY=...
KEPRIX_TOOL_VERIFY_KEY=...
KEPRIX_CHAT_GATEWAY_STREAM=true
KEPRIX_CHAT_MUTATION_SIDECAR=false
KEPRIX_MUTATION_APPROVAL_TIMEOUT=3600
KEPRIX_MUTATION_STREAM_WAIT_APPROVAL=true
KEPRIX_MUTATION_LLM_TRIGGER=false
KEPRIX_WEB_UI_AGENT_LOOP=false
```

`KEPRIX_MUTATION_RATE_LIMIT` appears in `.env.example` but is **not enforced** in code.

### Planned (Prompts 150-154; add to `.env.example` when implemented)

```bash
KEPRIX_MUTATION_TOOL_SYNTHESIS=true
KEPRIX_MUTATION_PROMPT_EVOLUTION=true
KEPRIX_MUTATION_SELF_CODING=false
KEPRIX_MUTATION_AUTO_APPROVE_THRESHOLD=0.85
KEPRIX_MUTATION_REQUIRE_TESTS=true
KEPRIX_MUTATION_RETENTION_DAYS=365
KEPRIX_MUTATION_MAX_GENERATED_TOOLS=200
KEPRIX_MUTATION_PRUNE_AFTER_DAYS=90
KEPRIX_MUTATION_SYNTHESIS_MIN_CONFIDENCE=0.75   # Prompt 151
```

---

## Phase Map

| Phase | Prompt | Outcome | Status |
| --- | --- | --- | --- |
| 0 | 28, 139-143 | Tier 1 core + chat E2E | **Done** |
| 1 | 150 | Schema inference, DB store, startup reload, sandbox hardening | **Not started** |
| 2 | 151 | Improvement loop wired; unified gap pipeline; `/api/mutation/tools/*` | **Not started** |
| 3 | 152 | Prompt/persona DB store, write-back, operator control | **Not started** |
| 4 | 153 | Scoped self-coding on Keprix source, test gate, history | **Not started** |
| 5 | 154 | Quality scoring, pruning, compounding, divergence | **Not started** |
| 6 | 155 | Full governance UI (all tiers, rollback, quality trends) | **Partial** (tool queue only) |

---

## Governance Hard Rules

These rules apply across all four tiers. They are not configurable.

1. A mutation may be staged without approval. It may not run in production until
   status is `approved` (manually or by auto-approve if confidence exceeds threshold).
2. Every mutation that runs is recorded in `mutation_events` before it executes.
   (Tier 1 today: JSON store only; Prompt 150 adds DB record.)
3. Every mutation has a rollback path. The system records what existed before.
4. Code mutations NEVER touch: `security/`, `vault/`, `auth/`, `review_gateway/`,
   `billing/`. These paths are hardcoded in the mutation scope allowlist (Prompt 153).
5. A generated tool is sandboxed before approval. If the sandbox run produces an
   error, the tool is quarantined and the operator is notified.
6. Prompt mutations are staged, not live. The current production prompt is never
   overwritten in place.
7. Chat stream owns the retry turn when `KEPRIX_MUTATION_STREAM_WAIT_APPROVAL=true`:
   approve API must not append a duplicate assistant message (`stream_waiting: true`).

---

## Files Checklist

### Backend - exists today (`src/keprix/agent/keprix/`)

See **Current State** table above. Prompt 150 **must not** recreate these modules
under `src/keprix/mutation/` with different names.

### Backend - new or extend (Prompts 150-154)

```
src/keprix/mutation/
    __init__.py
    store.py                  # MutationStore: mutation_events DB (wraps / replaces JSON store)
    quality.py                # QualityScorer: mutation_quality_samples
    compounding.py            # divergence, accumulation stats
    routes.py                 # /api/mutation/* unified REST
    schema_inference.py       # JSON schema from Python signature (Prompt 150)
    prompt_store.py           # DB-backed system prompt management (Prompt 152)
    self_coding_scope.py      # allowed paths, branch model, test gate (Prompt 153)
    pruner.py                 # quality-based pruning (Prompt 154)
    hook.py                   # improvement + run-complete integration (Prompt 151)
```

```
src/keprix/agent/keprix/
    # Extend, do not duplicate:
    sandbox.py                # Prompt 150: startup-safe Docker fallback (done 2026-07-06)
    installer.py              # Prompt 150: optional startup reload caller
```

### Backend - modify (Prompts 151-153)

```
src/keprix/improvement/tool_gap_detector.py   # emit to MutationStore / run_cycle
src/keprix/improvement/prompt_improver.py     # write to prompt_store
src/keprix/improvement/routes.py              # wire synthesizer on gap
src/keprix/tools/registry.py                  # startup reload_generated_tools()
src/keprix/coding/issue_runner.py             # scoped_mutation mode
src/keprix/agent/conversation_loop.py         # optional _keprix_on_tool_miss (non-web paths)
```

### Database

```
migrations/versions/015_mutation_store.py
```

### Frontend - exists (Tier 1)

```
frontend/src/components/workspace/blocks/MutationCard.tsx
frontend/src/app/(admin)/dashboard/mutations/page.tsx
frontend/src/app/(admin)/dashboard/mutations/[id]/page.tsx
frontend/src/components/admin/RecentMutations.tsx
```

### Frontend - new or extend (Prompt 155)

```
frontend/src/app/(admin)/dashboard/mutation/page.tsx      # unified governance (or extend mutations/)
frontend/src/app/(admin)/dashboard/mutation/[id]/page.tsx
frontend/src/lib/mutation-api.ts
frontend/src/components/mutation/MutationHistoryTable.tsx
frontend/src/components/mutation/GeneratedToolCard.tsx
frontend/src/components/mutation/MutationApprovalPanel.tsx
frontend/src/components/mutation/MutationQualityBadge.tsx
```

### Tests - exists

See **Tests (today)** above.

### Tests - new (Prompts 150-154)

```
tests/mutation/test_schema_inference.py
tests/mutation/test_mutation_store.py      # DB store
tests/mutation/test_prompt_store.py
tests/mutation/test_quality_scorer.py
tests/mutation/test_self_coding_scope.py
tests/mutation/test_pruner.py
tests/integration/test_mutation_improvement_e2e.py
```

---

## Cross-Prompt Acceptance Criteria

### Prompt 150

- [ ] `schema_inference.py` infers JSON Schema from generated Python (no exec)
- [ ] `mutation_events` migration applied; `MutationStore` CRUD + rollback fields
- [ ] Dual-write or migrate from `GeneratedToolStore` JSON without breaking APIs
- [ ] `registry.reload_generated_tools()` on API startup from `KEPRIX_GENERATED_TOOLS_DIR`
- [ ] Existing `tests/mutation/*` still pass; new store tests green
- [ ] Sandbox: Docker CLI incompatibility falls back to local runner (shipped in `sandbox.py`)

### Prompt 151

- [ ] `improvement/tool_gap_detector` triggers `MutationEngine.run_cycle` (or `mutation/hook.py`)
- [ ] `on_tool_miss` and `on_run_complete` documented and wired for non-web agent paths
- [ ] `/api/mutation/tools/*` exposes queue without breaking `/api/agent/tools/generated`
- [ ] `scripts/smoke-chat-mutation-e2e.py` still passes

### Prompt 152

- [ ] `prompt_store.py` stages prompt changes; production prompt never overwritten in place
- [ ] `mutation_events` rows for tier `prompt` and `persona`

### Prompt 153

- [ ] `self_coding_scope.py` enforces path allowlist and hard deny list
- [ ] Mutation branch + test gate before merge; tier `code` events recorded

### Prompt 154

- [ ] `mutation_quality_samples` populated on tool use
- [ ] Pruner respects `KEPRIX_MUTATION_PRUNE_AFTER_DAYS`; compounding metrics API

### Prompt 155

- [ ] Single governance surface for pending tools, prompts, code, and history
- [ ] Approve, reject, rollback actions call unified `/api/mutation/*`
- [ ] Quality badge and divergence card visible per 155 spec

---

## Known Gaps (do not re-litigate in 150-155)

1. **Dual gap pipelines:** `improvement/*` and `agent/keprix/*` detect gaps independently.
2. **JSON vs Postgres:** runtime uses JSON; migration `007` is orphaned.
3. **Post-approve registry reload:** live retry may report tool not in registry if
   hot-reload fails; verify signing keys and `KEPRIX_GENERATED_TOOLS_DIR` on install.
4. **Demo bias:** gap fast-paths and `KeprixRetry` helpers tuned for `fetch_stock_price`
   and `track_time`; generalize in 150-151.
5. **`conversation_loop._keprix_on_tool_miss`:** hook point exists, unset; web uses
   `mutation_hook` via gateway stream only.

---

## References

- Chat wiring: `prompts-archive/ref-138-chat-mutation-e2e-wiring-outline.md`
- Product docs: `docs/features/agent.md`, `docs/reference/api.md`
- Live smoke: `scripts/smoke-chat-mutation-e2e.py`
- Archived implementation: `planning/prompts/prompts-archive/28-*.md` (see README),
  `139` through `143` in `prompts-archive/`
