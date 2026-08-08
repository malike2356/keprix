# Keprix - Prompt 79: Adopt OmniRoute Smart Routing; Combos, Quota & Auto-Fallback

## Context

OmniRoute's routing engine is the most advanced open-source provider gateway available. It manages 237 providers through a "combo" system with tiered fallback, quota-aware routing, and millisecond auto-failover. Keprix's current provider router (`providers/`) does basic model selection; OmniRoute's approach is a significant upgrade.

This prompt adopts OmniRoute's intellectual design into Keprix's Python/FastAPI architecture. It does NOT break the existing provider system; it extends it, wrapping existing providers into combo tiers while keeping the current router as the default tier.

## Reference Clone

`planning/competitor-research/agents-to-adopt/omniroute/`

Key source files to study:
```
src/lib/combos/; Combo engine (intelligentRouting, autoPromote, compositeTiers)
src/lib/quota/; Quota system (accountBuckets, fairShare, burnRate, saturationSignals)
src/lib/api/comboErrorResponse.ts; Error response with next-provider hints
src/shared/providers/; Provider registry pattern
```

## What Keprix Already Has

```
src/keprix/providers/; Base provider router
  - base.py; Provider base class
  - Reads from config
  - Single-provider-per-call
  - No fallback chain
  - No quota awareness
  - No tier system
```

## What OmniRoute Adds

```
COMBO-BASED ROUTING:
  A "combo" = an ordered list of provider tiers with fallback rules
  
  Tier 1: SUBSCRIPTION providers (free, best quality)
    → Claude Code, Codex, Gemini CLI
  Tier 2: API KEY providers (paid, good quality)  
    → DeepSeek, Groq, xAI, Mistral, OpenAI
  Tier 3: FREE providers (no signup, no key)
    → Kiro, Qoder, Pollinations, LongCat (11 free forever)
  Tier 4: FALLBACK (last resort)
    → Local Ollama/LM Studio

  Request comes in:
    → Try Tier 1
    → If quota exhausted or error → try Tier 2 (milliseconds)
    → If quota exhausted or error → try Tier 3
    → If all fail → Tier 4 (always available)

QUOTA SYSTEM:
  - Per-account quota tracking
  - Fair-share distribution across accounts
  - Burn rate monitoring to predict exhaustion
  - Saturation signals before quota runs out
  - Automatic account rotation within same provider

AUTO-PROMOTE:
  - Combo health scoring (success rate, latency, quota remaining)
  - Automatically promote healthy providers
  - Demote failing providers with circuit breaker
  - Route explain: why was this provider chosen?
```

## Files To Create

```text
src/keprix/providers/combo/
  __init__.py
  engine.py              # Combo routing engine (adopt from intelligentRouting.ts)
  tier.py                # Tier definition and management
  auto_promote.py        # Provider health scoring and auto-promotion (adopt from autoPromote.ts)
  composite.py           # Multi-tier composite routing (adopt from compositeTiers.ts)
  explain.py             # Route explanation; why this provider was chosen
  health.py              # Provider health monitoring (latency, success rate, quota)
  builder.py             # Combo builder from config (adopt from builderDraft.ts)

src/keprix/providers/quota/
  __init__.py
  tracker.py             # Per-account quota tracking (adopt from accountBuckets.ts)
  fair_share.py          # Fair-share distribution across accounts (adopt from fairShare.ts)
  burn_rate.py           # Burn rate monitoring and exhaustion prediction (adopt from burnRate.ts)
  saturation.py          # Saturation signals before quota runs out (adopt from saturationSignals.ts)
  plan_registry.py       # Free tier plan definitions (adopt from planRegistry.ts)
  store.py               # Quota persistence (adopt from sqliteQuotaStore.ts)
  enforcer.py            # Quota enforcement middleware (adopt from enforce.ts)

src/keprix/providers/fallback/
  __init__.py
  chain.py               # Fallback chain executor
  circuit_breaker.py     # Circuit breaker pattern
  error_handler.py       # Error classification and provider demotion

src/keprix/providers/config/
  combos.yaml            # Combo definitions (default: one combo with existing providers)
  tiers.yaml             # Tier definitions: subscription, api_key, free, fallback

tests/providers/combo/
  test_engine.py
  test_tier.py
  test_auto_promote.py
  test_quota_tracker.py
  test_fair_share.py
  test_burn_rate.py
  test_fallback_chain.py
  test_circuit_breaker.py
```

## Combo Configuration (YAML)

```yaml
# src/keprix/providers/config/combos.yaml
# Defines provider routing combos. Products can override or add their own.

combos:
  - id: "default"
    name: "Keprix Default"
    description: "Smart routing with free-first, fallback to paid"
    tiers:
      - id: "free_forever"
        name: "Free Forever"
        providers:
          - "kiro"          # Free Claude, no signup
          - "qoder"         # Free coding models
          - "pollinations"  # Free LLM access
        max_concurrent: 3
        cooldown_seconds: 5
        
      - id: "subscription"
        name: "Subscription Providers"
        providers:
          - "claude_code"   # Requires Claude subscription
          - "codex"         # Requires OpenAI subscription
        max_concurrent: 1
        
      - id: "api_keys"
        name: "API Key Providers"
        providers:
          - "deepseek"      # Requires DEEPSEEK_API_KEY
          - "groq"          # Requires GROQ_API_KEY
          - "xai"           # Requires XAI_API_KEY
          - "mistral"       # Requires MISTRAL_API_KEY
          - "openai"        # Requires OPENAI_API_KEY
        max_concurrent: 2
        
      - id: "fallback"
        name: "Local Fallback"
        providers:
          - "ollama"        # Local, always available
          - "lm_studio"     # Local, always available
        max_concurrent: 1

  - id: "petraclus_default"
    name: "Petraclus Default"
    extends: "default"
    tiers:
      - id: "api_keys"
        providers:
          - "deepseek"      # Preferred for security work
          - "openai"        # For complex analysis
          - "anthropic"     # For reasoning tasks
```

## Integration; Non-Breaking

The existing provider system remains untouched:

```python
# BEFORE (still works):
provider = ProviderRouter.get("openai")
response = await provider.chat(messages, model="gpt-4o")

# AFTER (new capability, opt-in):
combo = ComboEngine.get("default")
response = await combo.route(messages, strategy="auto/coding")
# → Tries: kiro → qoder → deepseek → groq → ollama
# → Each failure auto-falls to next in milliseconds
# → Route logged with explanation

# Specific model override:
response = await combo.route(messages, model="auto/fast")
# → Prioritises low-latency free providers
```

The combo engine wraps existing providers; they're still registered the same way, they still have the same interface. The combo engine just adds smart routing on top.

## Implementation Details

### Combo Engine (adopt from `intelligentRouting.ts`)

```python
class ComboEngine:
    """Routes requests through tiered provider combos with automatic fallback."""
    
    async def route(
        self,
        messages: list[Message],
        model: str = "auto",
        strategy: str | None = None,
    ) -> ChatResponse:
        combo = self._resolve_combo(model)
        tiers = self._order_tiers(combo, strategy)
        
        last_error = None
        for tier in tiers:
            providers = self._get_healthy_providers(tier)
            for provider in providers:
                if await self.quota.check(provider, estimated_tokens):
                    try:
                        response = await provider.chat(messages)
                        self.health.record_success(provider, response.latency)
                        self.quota.record_usage(provider, response.usage)
                        return response
                    except QuotaExhausted:
                        self.quota.mark_exhausted(provider)
                        continue
                    except ProviderError as e:
                        self.health.record_failure(provider, e)
                        if self.circuit_breaker.should_break(provider):
                            self.health.demote(provider, cooldown_seconds=30)
                        last_error = e
                        continue
        
        raise AllProvidersExhausted(last_error, tried=len(tried_providers))
```

### Quota Tracker (adopt from `accountBuckets.ts`)

```python
class QuotaTracker:
    """Tracks per-provider, per-account quota with burn rate prediction."""
    
    async def check(self, provider: str, estimated_tokens: int) -> bool:
        """Check if provider has enough quota for this request."""
        bucket = await self._get_bucket(provider)
        
        # Check current remaining
        if bucket.remaining < estimated_tokens:
            return False
        
        # Check burn rate; will we exhaust before this request completes?
        if bucket.burn_rate > 0:
            seconds_until_empty = bucket.remaining / bucket.burn_rate
            if seconds_until_empty < 30:  # Less than 30 seconds left
                await self._emit_saturation_signal(provider, seconds_until_empty)
        
        return True
    
    async def predict_exhaustion(self, provider: str) -> datetime | None:
        """Predict when this provider will run out of quota."""
        bucket = await self._get_bucket(provider)
        if bucket.burn_rate <= 0:
            return None
        seconds = bucket.remaining / bucket.burn_rate
        return datetime.utcnow() + timedelta(seconds=seconds)
```

### Auto-Promote (adopt from `autoPromote.ts`)

```python
class AutoPromote:
    """Automatically promotes and demotes providers based on health scoring."""
    
    def score(self, provider: str) -> HealthScore:
        metrics = self.health.get_metrics(provider)
        return HealthScore(
            success_rate=metrics.success_count / max(metrics.total_count, 1),
            avg_latency_ms=metrics.avg_latency_ms,
            quota_remaining_pct=metrics.quota_remaining / max(metrics.quota_total, 1),
            error_rate=metrics.error_count / max(metrics.total_count, 1),
            uptime_minutes=metrics.uptime_minutes,
        )
    
    def should_promote(self, provider: str) -> bool:
        score = self.score(provider)
        return (
            score.success_rate > 0.95 and
            score.avg_latency_ms < 5000 and
            score.quota_remaining_pct > 0.10 and
            score.error_rate < 0.02
        )
    
    def should_demote(self, provider: str) -> bool:
        score = self.score(provider)
        return (
            score.error_rate > 0.20 or
            score.success_rate < 0.50 or
            score.quota_remaining_pct < 0.01
        )
```

### Circuit Breaker

```python
class CircuitBreaker:
    """Prevents hammering a failing provider."""
    
    def should_break(self, provider: str) -> bool:
        failures = self.failure_window.get(provider, [])
        recent = [f for f in failures if f.time > datetime.utcnow() - timedelta(seconds=60)]
        return len(recent) >= 5  # 5 failures in 60 seconds → break
    
    def break_circuit(self, provider: str, cooldown_seconds: int = 30):
        self.broken[provider] = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
    
    def is_broken(self, provider: str) -> bool:
        return provider in self.broken and self.broken[provider] > datetime.utcnow()
```

## Safety; Don't Break Existing

1. **Existing `providers/` module is untouched.** New code lives in `providers/combo/`, `providers/quota/`, `providers/fallback/`.
2. **Combo routing is opt-in.** Existing code that calls `ProviderRouter.get("openai").chat()` continues working.
3. **Default combo wraps existing providers.** If no combos.yaml exists, the combo engine creates a single-tier combo from registered providers; same behaviour as today.
4. **All new dependencies are optional.** Quota tracking, auto-promote, circuit breaker can be disabled via config.
5. **Tests run against existing provider mocks.** No new external dependencies required for testing.

## Verification

- [ ] Existing provider tests pass unchanged
- [ ] Combo engine routes through Tier 1 → Tier 2 → Tier 3 → Fallback
- [ ] Fallback happens in < 50ms (not seconds)
- [ ] Quota tracker correctly predicts exhaustion within 30 seconds of actual
- [ ] Circuit breaker opens after 5 failures in 60 seconds
- [ ] Circuit breaker closes after cooldown period
- [ ] Auto-promote promotes a recovering provider after cooldown
- [ ] Auto-promote demotes a failing provider after threshold
- [ ] Route explain returns why a specific provider was chosen
- [ ] Configurable via combos.yaml; no code changes needed to add providers
- [ ] Works with `auto`, `auto/fast`, `auto/coding`, `offline` strategies
- [ ] Tests pass for all new modules
