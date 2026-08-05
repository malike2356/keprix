# Keprix - Prompt 145: LLM Usage Persistence and Instrumentation

## Context

Read `144-llm-usage-analytics-wiring-outline.md` first.

Prompt 57 shipped in-memory `TokenMeter` and `CostMeter` plus trace capture, but
usage is lost on restart and web chat does not record tokens at all. Prompt 18
shipped generic `metrics` rows without per-call LLM granularity.

This prompt adds **durable per-call LLM usage events** and wires recording into
every production LLM path.

Output: `src/keprix/usage/`, Alembic migration `014_llm_usage_events.py`, hooks in
agent and API modules, tests.

## Step 1: Package layout

```text
src/keprix/usage/
  __init__.py
  schemas.py          # LlmUsageEvent, LlmUsageRecord
  store.py            # LlmUsageStore (PostgreSQL + SQLite fallback)
  recorder.py         # LlmUsageRecorder.record()
  pricing_bridge.py   # wraps estimate_usage_cost from agent/usage_pricing.py
  retention.py        # prune job
```

Do not duplicate pricing tables; import from `keprix.agent.usage_pricing`.

## Step 2: Database schema

Migration `migrations/versions/014_llm_usage_events.py`:

Table `llm_usage_events`:

| Column | Type | Notes |
| --- | --- | --- |
| id | String(36) PK | uuid |
| recorded_at | timestamptz | indexed |
| workspace_id | Text | default `default` |
| user_id | Text nullable | indexed |
| session_id | Text nullable | indexed |
| run_id | Text nullable | |
| channel | Text | web_ui, telegram, api, eval, ... |
| provider | Text | |
| model | Text | indexed |
| input_tokens | Integer | |
| output_tokens | Integer | |
| cache_read_tokens | Integer | default 0 |
| cache_write_tokens | Integer | default 0 |
| reasoning_tokens | Integer | default 0 |
| total_tokens | Integer | |
| cost_usd | Numeric nullable | |
| cost_status | Text | |
| cost_source | Text | |
| duration_ms | Integer nullable | |
| metadata | JSON | |

Indexes:

- `(recorded_at)`
- `(workspace_id, recorded_at)`
- `(user_id, recorded_at)`
- `(model, recorded_at)`
- `(channel, recorded_at)`

SQLite fallback: when `get_session_factory()` is None and
`KEPRIX_LLM_USAGE_SQLITE_FALLBACK=true`, use a local SQLite file at
`{KEPRIX_DATA_DIR}/llm_usage.db` with the same columns.

## Step 3: LlmUsageRecorder

`recorder.py`:

```python
class LlmUsageRecorder:
    async def record(
        self,
        *,
        usage: CanonicalUsage,
        provider: str,
        model: str,
        channel: str,
        user_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        duration_ms: int | None = None,
        metadata: dict | None = None,
        workspace_id: str = "default",
    ) -> str:  # returns event id
```

Behavior:

1. Respect `KEPRIX_LLM_USAGE_ENABLED=false` (no-op, return empty id)
2. Compute cost via `pricing_bridge.estimate(usage, provider, model, ...)`
3. Persist via `LlmUsageStore.insert`
4. Also call existing `get_token_meter().record` and `record_cost` for backward
   compat with Prompt 57 dashboard until Prompt 146 supersedes it
5. Never block the LLM response on DB failure; log and continue

Provide sync wrapper `record_sync(...)` for conversation_loop thread contexts.

## Step 4: Instrument conversation loop

File: `src/keprix/agent/conversation_loop.py`

After `canonical_usage` and `cost_result` are computed (existing block around
`update_token_counts`), add:

```python
from keprix.usage.recorder import get_llm_usage_recorder
get_llm_usage_recorder().record_sync(
    usage=canonical_usage,
    provider=agent.provider,
    model=agent.model,
    channel=getattr(agent, "platform", None) or "agent",
    user_id=getattr(agent, "user_id", None),
    session_id=agent.session_id,
    run_id=task_id,
    duration_ms=int(api_duration * 1000) if api_duration else None,
)
```

Map platform values to stable channel names: `web_ui`, `telegram`, `discord`,
`cron`, `cli`, `gateway`.

## Step 5: Instrument web chat inference

File: `src/keprix/api/chat_inference.py`

Today `stream_chat_completion` yields text only. Extend to:

1. Accumulate stream metadata from provider client when available
2. On stream end, read `usage` from final chunk (OpenAI-compatible) or issue a
   lightweight non-stream completion count call only when provider omits usage
   (document which providers require this)
3. Call `LlmUsageRecorder.record` with `channel=web_ui`

Add `user_id` and `session_id` parameters to `stream_chat_completion` signature;
thread from `conversation_routes.py`.

For providers without usage in stream, record `cost_status=unknown` with token
counts 0 and metadata note rather than skipping the event.

## Step 6: Instrument public API

Files: `src/keprix/public_api/` chat and embeddings handlers.

After each completion, call recorder with `channel=api` and `metadata.api_key_id`.

Reuse or extend `public_api/usage.py` so it writes full `LlmUsageEvent` rows,
not only aggregate metrics.

## Step 7: Instrument mutation synthesiser and eval LLM judge

- `src/keprix/agent/keprix/synthesiser.py`: `channel=mutation`
- `src/keprix/backend/evals/graders.py` LLM judge path: `channel=eval`

## Step 8: Bridge agent trace

File: `src/keprix/backend/observability/agent_trace.py`

When `capture_trace` records tokens/cost, also persist `LlmUsageEvent` with
`run_id` matching trace id so trace viewer and usage dashboard agree.

## Step 9: Retention cron

`retention.py`:

- Delete rows older than `KEPRIX_LLM_USAGE_RETENTION_DAYS` (default 90)
- Register with existing cron runner or `keprix cron` job `llm_usage_prune`
- Mirror `MetricsStore.prune_old` pattern

## Step 10: Configuration

Add to `.env.example`:

```bash
KEPRIX_LLM_USAGE_ENABLED=true
KEPRIX_LLM_USAGE_RETENTION_DAYS=90
KEPRIX_LLM_USAGE_SQLITE_FALLBACK=true
```

## Step 11: Tests

`tests/usage/test_recorder.py`:

1. Record event persists to store (use test DB or temp SQLite)
2. Cost computed when model has known pricing
3. `KEPRIX_LLM_USAGE_ENABLED=false` skips insert
4. Recorder failure does not raise to caller (mock store raises)
5. `conversation_loop` integration mock: one LLM turn creates one event

`tests/usage/test_store.py`:

- Insert, query by date range, prune

Run: `pytest tests/usage/ -q`

## Acceptance Criteria

- Restarting the backend does not lose usage data (PostgreSQL or SQLite file)
- Web chat completion creates an `llm_usage_events` row
- Agent loop completion creates a row with correct channel
- Public API completion creates a row with `api_key_id` in metadata
- Token and cost fields match `CanonicalUsage` + `estimate_usage_cost`
- No stubs in recorder production path
- Migration applies cleanly: `alembic upgrade head`

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.
