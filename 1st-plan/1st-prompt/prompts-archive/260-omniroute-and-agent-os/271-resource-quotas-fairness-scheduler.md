# Keprix - Prompt 258: Resource Quotas and Fairness Scheduler

## Context

An OS that cannot prevent one process from starving others is not an OS -- it is a
free-for-all. A heavy ABBIS playbook running a batch research job should not be able
to exhaust all LLM token capacity, leaving Aiva's real-time customer call waiting
for 30 seconds. An autonomous task loop should not be able to consume unlimited tokens
without budget enforcement.

This prompt adds three things keprix needs to behave like a real multi-tenant OS:

1. **Per-product resource quotas** -- LLM tokens, tool calls, concurrent sessions, and
   storage per billing period.
2. **Fairness scheduler** -- when multiple products compete for the LLM provider, a
   fair-share scheduler ensures no single product monopolises throughput.
3. **Budget enforcement** -- agents know their remaining budget mid-session and can
   gracefully surface quota exhaustion to the user rather than failing silently.

## What already exists (do not rebuild)

- `security/product_context.py` -- `get_product_context()` from Prompt 255
- OmniRoute quota system (Prompt 80) -- per-provider, per-account quota tracking at
  the provider layer. THIS PROMPT is per-product quotas at the application layer.
  They are complementary, not duplicates. OmniRoute enforces what providers will accept;
  this prompt enforces what keprix allocates to each product.
- `agent/conversation_loop.py` -- intercept here to check/deduct token quota
- `api/stats_routes.py` -- extend for quota dashboard

## Resource types tracked

```python
class ResourceType(StrEnum):
    LLM_TOKENS_IN     = "llm_tokens_in"       # input tokens consumed
    LLM_TOKENS_OUT    = "llm_tokens_out"       # output tokens consumed
    TOOL_CALLS        = "tool_calls"           # tool invocations
    CONCURRENT_SESSIONS = "concurrent_sessions" # active sessions right now
    STORAGE_BYTES     = "storage_bytes"        # memories + documents stored
    VOICE_MINUTES     = "voice_minutes"        # phone call minutes (Prompt 245)
```

## What to build

### 1. Quota definitions per product

`src/keprix/quotas/quota_config.py`:

Defined in `keprix.yaml` per product (or in the admin UI):

```yaml
# aiva/keprix.yaml
quotas:
  period: monthly                    # reset cadence: hourly | daily | weekly | monthly
  llm_tokens_in:   5_000_000        # 5M input tokens/month
  llm_tokens_out:  1_000_000        # 1M output tokens/month
  tool_calls:      50_000
  concurrent_sessions: 10           # max parallel active sessions
  storage_bytes:   524_288_000      # 500MB
  voice_minutes:   300              # 5 hours/month

  on_exhaustion:
    llm_tokens:     graceful         # graceful | block | alert_only
    tool_calls:     block
    storage:        block
    voice_minutes:  block

  burst_allowance: 0.10             # allow 10% over quota before hard block
```

```python
@dataclass
class ProductQuota:
    product_id: str
    period: str                          # "monthly" | "daily" | "hourly"
    limits: dict[ResourceType, int]
    on_exhaustion: dict[ResourceType, str]
    burst_allowance: float = 0.0

@dataclass
class QuotaUsage:
    product_id: str
    period_start: datetime
    period_end: datetime
    usage: dict[ResourceType, int]
    limits: dict[ResourceType, int]

    def remaining(self, resource: ResourceType) -> int:
        limit = self.limits.get(resource, 0)
        used = self.usage.get(resource, 0)
        burst = int(limit * self._quota.burst_allowance)
        return max(0, limit + burst - used)

    def is_exhausted(self, resource: ResourceType) -> bool:
        return self.remaining(resource) <= 0
```

### 2. Quota store

`src/keprix/quotas/quota_store.py`:

```python
class QuotaStore:
    """
    Tracks per-product resource usage. Written on every LLM response and tool call.
    Backed by Postgres (shared across instances) or SQLite (single-node).
    Uses atomic increment to prevent race conditions under concurrent writes.
    """

    async def increment(
        self,
        product_id: str,
        resource: ResourceType,
        amount: int,
        session_id: str | None = None,
    ) -> QuotaUsage:
        """Atomically increment usage and return updated QuotaUsage."""

    async def get_usage(self, product_id: str) -> QuotaUsage:
        """Return current period usage for a product."""

    async def reset_period(self, product_id: str):
        """Called by the period reset scheduler (cron). Resets usage to 0."""

    async def set_concurrent_sessions(self, product_id: str, count: int):
        """Update the live concurrent session count (not period-based)."""
```

Table: `quota_usage`
```
product_id, resource_type, period_start, period_end, amount, updated_at
```

### 3. Quota enforcer

`src/keprix/quotas/quota_enforcer.py`:

```python
class QuotaEnforcer:
    """Called before and after every LLM call and tool invocation."""

    async def check_before_llm_call(
        self, product_id: str, estimated_tokens: int
    ) -> QuotaCheckResult:
        usage = await self.store.get_usage(product_id)
        quota = await self.config.get_quota(product_id)

        if usage.is_exhausted(ResourceType.LLM_TOKENS_IN):
            action = quota.on_exhaustion.get(ResourceType.LLM_TOKENS_IN, "block")
            return QuotaCheckResult(
                allowed=(action != "block"),
                reason="llm_tokens_exhausted",
                remaining=0,
                action=action,
            )

        return QuotaCheckResult(allowed=True, remaining=usage.remaining(ResourceType.LLM_TOKENS_IN))

    async def record_llm_usage(
        self, product_id: str, tokens_in: int, tokens_out: int, session_id: str
    ):
        await self.store.increment(product_id, ResourceType.LLM_TOKENS_IN, tokens_in, session_id)
        await self.store.increment(product_id, ResourceType.LLM_TOKENS_OUT, tokens_out, session_id)

    async def check_concurrent_sessions(self, product_id: str) -> QuotaCheckResult:
        usage = await self.store.get_usage(product_id)
        quota = await self.config.get_quota(product_id)
        limit = quota.limits.get(ResourceType.CONCURRENT_SESSIONS, 999)
        current = usage.usage.get(ResourceType.CONCURRENT_SESSIONS, 0)
        return QuotaCheckResult(allowed=current < limit, remaining=limit - current)
```

Integration points:
- `agent/conversation_loop.py`: call `check_before_llm_call` before every LLM request;
  call `record_llm_usage` after every response (token counts from LLM response metadata)
- `agent/tool_executor.py`: call `store.increment(tool_calls, 1)` after each tool call
- `gateway/` session open/close: update `concurrent_sessions` count

### 4. Graceful exhaustion behaviour

When `on_exhaustion: graceful` is set for LLM tokens, the agent is not blocked hard.
Instead, the enforcer injects a system message into the conversation:

```python
QUOTA_WARNING_MESSAGE = """
[System: You are approaching your token limit for this billing period.
Remaining: {remaining} tokens. Please wrap up this conversation efficiently.
The user can upgrade their plan at /billing to increase the limit.]
"""

QUOTA_EXHAUSTED_MESSAGE = """
[System: Token quota exhausted for this billing period.
You may not make further LLM calls. Tell the user clearly and suggest
they upgrade at /billing or wait for the next billing period reset on {reset_date}.]
"""
```

The agent receives this as a system message and should communicate the situation to the
user naturally.

### 5. Fairness scheduler

`src/keprix/quotas/fairness_scheduler.py`:

When multiple products submit LLM requests simultaneously, the fairness scheduler
determines which proceeds first. The goal: each product gets a fair share of throughput
proportional to its quota, not first-come-first-served.

```python
class FairnessScheduler:
    """
    Weighted fair-share scheduler for concurrent LLM requests.
    Weight = (product quota limit) / (current period usage ratio).
    Products that have used less of their quota get higher priority.
    """

    async def acquire_slot(self, product_id: str) -> SchedulerToken:
        """
        Wait for a slot to become available. Returns a token that must be
        released after the LLM call completes.
        Priority = remaining_quota_pct * base_weight
        Products at 10% of their quota are deprioritised vs products at 90%.
        """

    async def release_slot(self, token: SchedulerToken):
        """Release the slot after the LLM call completes."""
```

Max concurrent LLM calls across all products: configurable via `config.yaml`:
```yaml
scheduler:
  max_concurrent_llm_calls: 8   # global cap
  max_per_product: 3            # per-product cap within the global cap
  priority_mode: fair_share     # fair_share | fifo | round_robin
```

The scheduler is only active when `max_concurrent_llm_calls` is under pressure.
When slots are available, requests proceed immediately with no queuing overhead.

### 6. Quota dashboard

Route: `/admin/quotas`

```
┌──────────────────────────────────────────────────────────┐
│  Resource Quotas           Period: July 2026  [Reset ▾]  │
├──────────────────────────────────────────────────────────┤
│  Product: Aiva                                            │
│  LLM Tokens In:   ██████████████░░░░  3.2M / 5M (64%)   │
│  LLM Tokens Out:  ████████░░░░░░░░░░  420K / 1M (42%)   │
│  Tool Calls:      ██████░░░░░░░░░░░░  12K / 50K (24%)   │
│  Concurrent:      ████░░░░░░░░░░░░░░  4 / 10 active     │
│  Storage:         ██░░░░░░░░░░░░░░░░  84MB / 500MB       │
├──────────────────────────────────────────────────────────┤
│  Product: ABBIS                                           │
│  LLM Tokens In:   ██████████████████  4.9M / 5M (98%)   │
│  [!] Near limit -- on_exhaustion: graceful               │
├──────────────────────────────────────────────────────────┤
│  Fairness Scheduler                                       │
│  Current load: 6 / 8 slots occupied                      │
│  aiva: 3 slots  abbis: 2 slots  keprix: 1 slot           │
└──────────────────────────────────────────────────────────┘
```

Period reset notification: when a product's period resets (monthly), emit a
`quota.reset` event that can trigger a webhook or notification.

### 7. CLI commands

```
keprix quotas status [product_id]   - show current usage
keprix quotas reset [product_id]    - manually reset a product's period usage
keprix quotas set [product_id] [resource] [limit]  - update a limit
keprix quotas history [product_id]  - historical usage over past N periods
```

## Files to create

```
src/keprix/quotas/
  __init__.py
  quota_config.py            - ProductQuota, QuotaUsage, ResourceType
  quota_store.py             - QuotaStore (atomic increment, period reset)
  quota_enforcer.py          - QuotaEnforcer (check + record)
  fairness_scheduler.py      - FairnessScheduler (weighted fair-share)
  quota_reset_cron.py        - period reset scheduler (run at period boundary)

src/keprix/api/
  quota_routes.py            - GET /api/admin/quotas, PATCH /api/admin/quotas/{product_id}
  quota_cli.py               - keprix quotas subcommands

frontend/src/app/(admin)/dashboard/
  quotas/
    page.tsx                 - quota dashboard with progress bars

migrations/
  add_quota_usage_table.py

tests/quotas/
  test_quota_store.py
  test_quota_enforcer.py
  test_fairness_scheduler.py
  test_quota_reset.py
```

Modifications to existing files:
- `agent/conversation_loop.py` -- `check_before_llm_call` before request,
  `record_llm_usage` after response
- `agent/tool_executor.py` -- increment `tool_calls` after each tool dispatch
- `gateway/` session management -- update `concurrent_sessions` on open/close

## Acceptance criteria

- A product that exhausts its `llm_tokens_in` quota with `on_exhaustion: block` cannot
  make further LLM calls until the period resets. The agent receives a clear message.
- A product with `on_exhaustion: graceful` receives the quota warning message injected
  into the conversation at 90% and 100% of limit.
- `record_llm_usage` correctly deducts tokens matching the LLM response's usage metadata.
- The fairness scheduler ensures a product consuming 98% of its quota does not take all
  available slots when another product has low utilisation.
- Period reset runs automatically at the configured cadence (monthly = first of month
  00:00 UTC). Usage resets to 0 atomically.
- The quota dashboard shows live usage with < 5 second staleness.
- `keprix quotas status` prints usage and remaining for all resource types.
- Concurrent session enforcement correctly blocks a new session when the product is
  at its `concurrent_sessions` limit.
- The burst allowance (10%) allows the product to slightly exceed its limit before hard
  blocking, then blocks until usage drops below the limit.
