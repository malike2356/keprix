# Keprix - Prompt 82: Adopt OmniRoute; Operational Excellence Layer

## Context

OmniRoute has several smaller but critical modules that make the gateway production-grade. These are not architectural changes; they're operational enhancements that reduce cost, prevent failures, and improve reliability. This prompt adopts them as a single operational excellence layer.

## Reference Clone

`planning/competitor-research/agents-to-adopt/omniroute/`

Key source files:
```
src/lib/promptCache/; prefixAnalyzer.ts (semantic prompt caching)
src/lib/spend/; batchWriter.ts (cost tracking)
src/lib/translator/; OpenAI ↔ Anthropic ↔ Google format translation
src/lib/headroom/; detect.ts, process.ts (capacity prediction)
src/lib/credentialHealth/; cache.ts, scheduler.ts (credential monitoring)
src/lib/freeProxyProviders/; Free HTTP proxy pool
src/lib/cliTools/; batchStatusCache.ts, tool config detection
src/lib/sync/; bundle.ts, tokens.ts (model bundle sync)
```

## What to Adopt

### 1. Semantic Prompt Cache

Cache LLM responses based on semantic similarity, not exact string match. If two requests are *semantically* the same (different phrasing, same intent), serve the cached response.

```
PROMPT CACHE FLOW:

  Request comes in
       │
  ┌────▼──────────────────────┐
  │  PREFIX ANALYZER           │
  │  ───────────────────────── │
  │  Hash first 500 tokens     │
  │  → Cache key               │
  └────┬──────────────────────┘
       │
  ┌────▼──────────────────────┐
  │  CACHE LOOKUP             │
  │  ───────────────────────── │
  │  Exact match?              │
  │    → Return cached         │
  │  Semantic match (>0.95)?   │
  │    → Return cached         │
  │  No match?                 │
  │    → Route to provider     │
  │    → Cache response        │
  └────────────────────────────┘
```

Benefits:
- Free for repeated tool-calling patterns (agent loops often repeat the same tool invocations)
- Free for repeated system prompts (same system prompt = same prefix hash)
- TTL-configurable: 60s for chat, 300s for tool calls, 3600s for system prompts

### 2. Spend Tracking

Track actual cost per provider, per agent, per session. Feed into billing and cost optimisation.

```python
class SpendTracker:
    """Tracks real-time spend across providers."""
    
    async def record(self, request: SpendRecord) -> None:
        """Record a single spend event."""
        await self.db.insert(SpendRecord(
            request_id=request.request_id,
            provider=request.provider,
            model=request.model,
            agent=request.agent,          # Which persona made the request
            session_id=request.session_id,
            tokens_in=request.tokens_in,
            tokens_out=request.tokens_out,
            cost_usd=request.cost_usd,     # Calculated from provider pricing
            latency_ms=request.latency_ms,
            timestamp=datetime.utcnow(),
        ))
    
    async def get_agent_spend(self, agent: str, period: str = "24h") -> SpendSummary:
        """Total spend per agent."""
        ...
    
    async def get_provider_spend(self, provider: str, period: str = "24h") -> SpendSummary:
        """Total spend per provider."""
        ...
    
    async def get_session_cost(self, session_id: str) -> float:
        """Total cost for a session."""
        ...
    
    async def forecast_daily_cost(self) -> float:
        """Predict today's total cost based on burn rate."""
        ...
```

API endpoints:
```
GET  /api/observability/spend/agent/{name}       → Per-agent spend
GET  /api/observability/spend/provider/{name}    → Per-provider spend
GET  /api/observability/spend/session/{id}       → Per-session cost
GET  /api/observability/spend/forecast            → Daily cost forecast
```

### 3. Format Translator

Translate between OpenAI, Anthropic, and Google API formats so any provider can understand any request format.

```python
class FormatTranslator:
    """Translates between API formats transparently."""
    
    FORMATS = ["openai", "anthropic", "google"]
    
    def translate_request(
        self,
        messages: list[Message],
        from_format: str = "openai",
        to_format: str = "anthropic",
    ) -> Any:
        """Translate request messages between formats."""
        
        if to_format == "anthropic":
            # OpenAI: [{"role": "user", "content": "hello"}]
            # Anthropic: {"system": "...", "messages": [{"role": "user", "content": "hello"}]}
            system_msg = next((m for m in messages if m.role == "system"), None)
            chat_msgs = [m for m in messages if m.role != "system"]
            result = {"messages": chat_msgs}
            if system_msg:
                result["system"] = system_msg.content
            return result
        
        if to_format == "google":
            # Convert to Gemini format
            ...
    
    def translate_response(
        self,
        response: Any,
        from_format: str,
        to_format: str = "openai",
    ) -> ChatResponse:
        """Translate response back to OpenAI format."""
        ...
    
    def auto_detect_and_translate(
        self,
        provider: str,
        request: Any,
    ) -> tuple[Any, str]:
        """Auto-detect provider format and translate."""
        provider_format = self._get_provider_format(provider)
        return self.translate_request(request, "openai", provider_format), provider_format
```

Format mapping:
| Provider | Native Format |
|----------|:---:|
| OpenAI, Groq, DeepSeek, Mistral, xAI | OpenAI |
| Anthropic, Claude | Anthropic Messages |
| Google, Gemini | Google Generative AI |
| Ollama, LM Studio | OpenAI-compatible |

### 4. Headroom Detection

Predict when provider quota will run out and pre-allocate capacity.

```python
class HeadroomDetector:
    """Predicts and manages provider capacity headroom."""
    
    async def detect(self, provider: str) -> HeadroomStatus:
        """Check current headroom status."""
        
        quota = await self.quota_tracker.get_bucket(provider)
        burn = await self.spend_tracker.get_burn_rate(provider)
        
        if burn.requests_per_minute == 0:
            return HeadroomStatus.UNLIMITED
        
        minutes_remaining = quota.remaining / burn.requests_per_minute
        
        if minutes_remaining < 5:
            return HeadroomStatus.CRITICAL  # Less than 5 min
        if minutes_remaining < 30:
            return HeadroomStatus.LOW        # Less than 30 min
        if minutes_remaining < 120:
            return HeadroomStatus.MODERATE   # Less than 2 hours
        return HeadroomStatus.HEALTHY
    
    async def pre_allocate(self, provider: str, tokens: int) -> AllocationResult:
        """Pre-allocate quota for an upcoming request."""
        status = await self.detect(provider)
        if status == HeadroomStatus.CRITICAL:
            # Don't route new requests here; promote fallback
            return AllocationResult(allocated=False, reason="critical_headroom")
        
        # Reserve tokens
        await self.quota_tracker.reserve(provider, tokens)
        return AllocationResult(allocated=True, reserved_tokens=tokens)
    
    async def get_estimated_remaining(self, provider: str) -> timedelta:
        """How long until this provider runs out?"""
        ...
```

### 5. Credential Health Monitor

Proactively check API keys, OAuth tokens, and rate limits to prevent surprise failures.

```python
class CredentialHealthMonitor:
    """Monitors API credentials and predicts failures before they happen."""
    
    async def check(self, provider: str) -> CredentialHealth:
        """Check credential health for a provider."""
        
        creds = await self.store.get(provider)
        
        checks = []
        
        # Check API key validity
        if creds.api_key:
            valid = await self._validate_api_key(provider, creds.api_key)
            checks.append(Check("api_key_valid", valid))
        
        # Check OAuth token expiry
        if creds.oauth_token:
            expires_in = (creds.oauth_expires_at - datetime.utcnow()).total_seconds()
            checks.append(Check("oauth_expiry", expires_in > 3600, detail=f"expires in {expires_in}s"))
        
        # Check rate limit headroom
        rate_limits = await self._check_rate_limits(provider)
        checks.append(Check("rate_limits", all(r.remaining > 0 for r in rate_limits)))
        
        # Check billing status (for paid providers)
        if creds.billing_required:
            billing_ok = await self._check_billing(provider)
            checks.append(Check("billing", billing_ok))
        
        overall = all(c.passed for c in checks)
        failing = [c for c in checks if not c.passed]
        
        return CredentialHealth(
            provider=provider,
            healthy=overall,
            checks=checks,
            failing=failing,
            checked_at=datetime.utcnow(),
        )
    
    async def schedule_checks(self) -> None:
        """Run health checks on a schedule."""
        while True:
            for provider in self.registry.get_all():
                health = await self.check(provider)
                if not health.healthy:
                    await self.alert_engine.send(
                        level="warning",
                        message=f"Provider {provider} credential health degraded",
                        detail=health.failing,
                    )
            await asyncio.sleep(300)  # Every 5 minutes
```

### 6. Free Proxy Provider Pool

Maintain a pool of free HTTP proxies for providers that require proxy access.

```python
class FreeProxyPool:
    """Manages a pool of free proxy providers for routing."""
    
    PROVIDERS = ["proxifly", "webshare", "oneproxy", "iplocate"]
    
    async def refresh(self) -> list[Proxy]:
        """Refresh the proxy pool from free providers."""
        proxies = []
        for provider_name in self.PROVIDERS:
            try:
                provider = self._get_proxy_provider(provider_name)
                new_proxies = await provider.fetch()
                proxies.extend(new_proxies)
            except Exception:
                continue
        
        # Validate proxies
        valid = await self._validate_all(proxies)
        
        # Update pool
        self.pool = valid
        return valid
    
    async def get_proxy(self) -> Proxy | None:
        """Get the best available proxy."""
        if not self.pool:
            await self.refresh()
        
        # Return proxy with lowest latency
        return min(self.pool, key=lambda p: p.latency_ms) if self.pool else None
```

### 7. CLI Tool Auto-Configuration

Auto-detect and configure CLI tools (Claude Code, Codex, Cursor) to use Keprix as their gateway.

```python
class CLIToolConfigurator:
    """Auto-detects and configures CLI tools to route through Keprix."""
    
    SUPPORTED_TOOLS = {
        "claude_code": {
            "config_file": "~/.claude.json",
            "config_key": "api_base_url",
            "value": "http://localhost:20128/v1",
        },
        "codex": {
            "env_var": "OPENAI_BASE_URL",
            "value": "http://localhost:20128/v1",
        },
        "cursor": {
            "config_key": "openaiBaseUrl",
            "value": "http://localhost:20128/v1",
        },
        "copilot": {
            "env_var": "COPILOT_API_BASE",
            "value": "http://localhost:20128/v1",
        },
    }
    
    async def detect_installed(self) -> list[str]:
        """Detect which CLI tools are installed."""
        installed = []
        for tool in self.SUPPORTED_TOOLS:
            if await self._is_installed(tool):
                installed.append(tool)
        return installed
    
    async def configure(self, tool: str) -> ConfigResult:
        """Configure a CLI tool to use Keprix."""
        config = self.SUPPORTED_TOOLS[tool]
        
        if "config_file" in config:
            await self._write_config(config["config_file"], config["config_key"], config["value"])
        if "env_var" in config:
            await self._set_env(config["env_var"], config["value"])
        
        return ConfigResult(tool=tool, configured=True)
    
    async def check_status(self, tool: str) -> ToolStatus:
        """Check if a tool is currently configured to use Keprix."""
        ...
```

### 8. Sync Bundle Manager

Sync provider model lists and keep them updated.

```python
class ModelSyncManager:
    """Keeps provider model lists up to date."""
    
    async def sync_all(self) -> SyncResult:
        """Sync model lists from all providers."""
        results = {}
        for provider in self.registry.get_all():
            try:
                models = await self._fetch_model_list(provider)
                self.catalog.update(provider, models)
                results[provider] = SyncResult(
                    provider=provider,
                    models_count=len(models),
                    status="success",
                )
            except Exception as e:
                results[provider] = SyncResult(
                    provider=provider,
                    status="failed",
                    error=str(e),
                )
        return results
    
    async def get_available_models(self, provider: str) -> list[ModelInfo]:
        """Get currently available models for a provider."""
        return self.catalog.get(provider, [])
```

## Files To Create

```text
src/keprix/providers/cache/
  __init__.py
  prompt_cache.py        # Semantic prompt caching (adopt from promptCache/)
  prefix_analyzer.py     # Cache key generation from first N tokens
  cache_store.py         # Redis/SQLite-backed cache storage

src/keprix/providers/spend/
  __init__.py
  tracker.py             # Spend tracking engine (adopt from spend/)
  batch_writer.py        # Batched DB writes for high-throughput
  forecast.py            # Cost prediction
  routes.py              # /api/observability/spend/* endpoints

src/keprix/providers/translator/
  __init__.py
  translator.py          # Format translation engine
  openai_format.py       # OpenAI format helpers
  anthropic_format.py    # Anthropic format helpers
  google_format.py       # Google format helpers

src/keprix/providers/headroom/
  __init__.py
  detector.py            # Headroom detection (adopt from headroom/detect.ts)
  processor.py           # Pre-allocation logic (adopt from headroom/process.ts)

src/keprix/providers/credentials/
  __init__.py
  monitor.py             # Credential health monitoring (adopt from credentialHealth/)
  scheduler.py            # Health check scheduler
  oauth_refresh.py        # OAuth token refresh logic

src/keprix/providers/proxy/
  __init__.py
  pool.py                # Free proxy pool management (adopt from freeProxyProviders/)
  validators.py          # Proxy validation (latency, anonymity check)

src/keprix/providers/cli/
  __init__.py
  detector.py            # CLI tool detection
  configurator.py        # Auto-configuration (adopt from cliTools/)
  status.py              # Configuration status check

src/keprix/providers/sync/
  __init__.py
  model_sync.py          # Provider model list sync (adopt from sync/)
  bundle.py              # Model bundle management

tests/providers/
  test_prompt_cache.py
  test_spend_tracker.py
  test_translator.py
  test_headroom.py
  test_credential_monitor.py
  test_proxy_pool.py
  test_cli_configurator.py
  test_model_sync.py
```

## Safety; Non-Breaking

1. **Prompt cache is read-through.** Cache miss → routes to provider normally. Zero impact on uncached requests.
2. **Spend tracking is write-only.** Reads happen only on dashboard API calls. No request-path impact.
3. **Format translator is transparent.** Providers continue to receive their native format. Translation happens only when a combo mixes provider types.
4. **Headroom detection is advisory.** It informs routing decisions but never blocks requests.
5. **Credential monitoring is background.** Runs on a 5-minute schedule, never in the request path.
6. **All features disabled by default.** Enable individually via config or environment.

## Verification

- [ ] Prompt cache serves cached response for semantically identical requests
- [ ] Prompt cache TTL respected (60s chat, 300s tool, 3600s system)
- [ ] Spend tracker records cost per request with <1% error margin
- [ ] Spend API returns accurate per-agent, per-provider, per-session costs
- [ ] Format translator converts OpenAI → Anthropic and back correctly
- [ ] Format translator handles system messages correctly across formats
- [ ] Headroom detector predicts quota exhaustion within 2 minutes of actual
- [ ] Pre-allocation prevents routing to critical-headroom providers
- [ ] Credential monitor detects expired OAuth tokens and triggers refresh
- [ ] Credential monitor alerts on API key validation failure
- [ ] Proxy pool refreshes and validates proxies automatically
- [ ] CLI configurator detects installed tools and configures them
- [ ] Model sync keeps provider catalogs current
- [ ] All existing tests pass (all features disabled by default)
- [ ] Tests pass for all new modules
