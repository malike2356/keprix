# keprix - Prompt 16: Self-Configuration

**Output directory:** `/opt/lampp/htdocs/verlox/keprix/keprix/`
**Depends on:** Prompt 00 (architecture), Prompt 03 (core agent engine), Prompt 02 (Security Foundation)
**Related to but distinct from:** Prompt 28 (keprix Agent / self-coding)

---

## Distinction: Self-Coding vs Self-Configuration

**Self-Coding (Prompt 28 - The keprix Agent):**
The agent encounters a capability gap (e.g., cannot parse .avif images) and writes
new Python code to fill the gap. Operates on tools and capabilities.

**Self-Configuration (this prompt):**
The agent encounters a runtime problem (e.g., DeepSeek API is returning 503, Redis
connection dropped, a channel adapter went offline) and adjusts its own operational
settings, routing, and environment to restore normal function. Operates on config and
infrastructure. No new code is written; existing components are reconfigured.

The two features are complementary. When the agent hits a gap:
- If the gap is a missing capability: keprix Agent writes a new tool.
- If the gap is a misconfiguration or runtime fault: Self-Configuration fixes the config.

---

## Objective

Build the self-configuration capability as four cooperating subsystems:

1. **Config Health Monitor** - continuously observes component health
2. **Auto-Repair Engine** - applies safe automatic fixes when health degrades
3. **Config Optimizer** - analyzes telemetry and proposes configuration improvements
4. **Environment Discovery** - runs on first install and generates a working config
   from scratch by probing available resources and credentials

---

## 1. Config Health Monitor

### File: `keprix/config/health_monitor.py`

```python
import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Awaitable, Any
import httpx

@dataclass
class ComponentHealth:
    name: str
    status: str          # "healthy" | "degraded" | "down"
    latency_ms: float
    error: str
    checked_at: float

class ConfigHealthMonitor:
    def __init__(self, check_interval_seconds: int = 60):
        self.interval = check_interval_seconds
        self._results: dict[str, ComponentHealth] = {}
        self._callbacks: list[Callable[[ComponentHealth], Awaitable[None]]] = []

    def on_status_change(self, cb: Callable[[ComponentHealth], Awaitable[None]]) -> None:
        self._callbacks.append(cb)

    async def run(self) -> None:
        while True:
            await self._run_all_checks()
            await asyncio.sleep(self.interval)

    async def _run_all_checks(self) -> None:
        checks = [
            self._check_llm_providers(),
            self._check_redis(),
            self._check_postgres(),
            self._check_egress(),
            self._check_channel_adapters(),
        ]
        results = await asyncio.gather(*checks, return_exceptions=True)
        for batch in results:
            if isinstance(batch, list):
                for h in batch:
                    prev = self._results.get(h.name)
                    self._results[h.name] = h
                    if prev and prev.status != h.status:
                        for cb in self._callbacks:
                            asyncio.create_task(cb(h))

    async def _check_llm_providers(self) -> list[ComponentHealth]:
        from keprix.brain.provider_registry import PROVIDER_REGISTRY
        results = []
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, provider in PROVIDER_REGISTRY.items():
                t0 = time.monotonic()
                try:
                    # Minimal probe: a single-token completion
                    await provider.health_check(client)
                    latency = (time.monotonic() - t0) * 1000
                    results.append(ComponentHealth(
                        name=f"llm:{name}", status="healthy",
                        latency_ms=latency, error="", checked_at=time.time()
                    ))
                except Exception as e:
                    results.append(ComponentHealth(
                        name=f"llm:{name}", status="down",
                        latency_ms=0, error=str(e)[:200], checked_at=time.time()
                    ))
        return results

    async def _check_redis(self) -> list[ComponentHealth]:
        from keprix.db.redis_client import get_redis
        t0 = time.monotonic()
        try:
            r = await get_redis()
            await r.ping()
            return [ComponentHealth(
                name="redis", status="healthy",
                latency_ms=(time.monotonic() - t0) * 1000,
                error="", checked_at=time.time()
            )]
        except Exception as e:
            return [ComponentHealth(
                name="redis", status="down",
                latency_ms=0, error=str(e)[:200], checked_at=time.time()
            )]

    async def _check_postgres(self) -> list[ComponentHealth]:
        from keprix.db.postgres import get_pool
        t0 = time.monotonic()
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return [ComponentHealth(
                name="postgres", status="healthy",
                latency_ms=(time.monotonic() - t0) * 1000,
                error="", checked_at=time.time()
            )]
        except Exception as e:
            return [ComponentHealth(
                name="postgres", status="down",
                latency_ms=0, error=str(e)[:200], checked_at=time.time()
            )]

    async def _check_egress(self) -> list[ComponentHealth]:
        probes = [
            ("egress:api.openai.com", "https://api.openai.com/"),
            ("egress:api.anthropic.com", "https://api.anthropic.com/"),
            ("egress:api.deepseek.com", "https://api.deepseek.com/"),
        ]
        results = []
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in probes:
                t0 = time.monotonic()
                try:
                    r = await client.head(url)
                    # Any response (even 401/403) means the host is reachable
                    results.append(ComponentHealth(
                        name=name, status="healthy",
                        latency_ms=(time.monotonic() - t0) * 1000,
                        error="", checked_at=time.time()
                    ))
                except Exception as e:
                    results.append(ComponentHealth(
                        name=name, status="down",
                        latency_ms=0, error=str(e)[:200], checked_at=time.time()
                    ))
        return results

    async def _check_channel_adapters(self) -> list[ComponentHealth]:
        from keprix.gateway.adapter_registry import get_active_adapters
        results = []
        for adapter in get_active_adapters():
            t0 = time.monotonic()
            try:
                await adapter.health_check()
                results.append(ComponentHealth(
                    name=f"channel:{adapter.name}", status="healthy",
                    latency_ms=(time.monotonic() - t0) * 1000,
                    error="", checked_at=time.time()
                ))
            except Exception as e:
                results.append(ComponentHealth(
                    name=f"channel:{adapter.name}", status="down",
                    latency_ms=0, error=str(e)[:200], checked_at=time.time()
                ))
        return results

    def get_all(self) -> dict[str, ComponentHealth]:
        return dict(self._results)
```

---

## 2. Auto-Repair Engine

The auto-repair engine is triggered by health status changes. It applies safe,
pre-approved repairs without human confirmation. Destructive repairs (changing
a provider key, disabling a channel) require explicit confirmation.

### File: `keprix/config/auto_repair.py`

```python
import asyncio
import time
from keprix.config.health_monitor import ComponentHealth
from keprix.security.event_reporter import report_security_event

# Maximum time to attempt repair before giving up and alerting the admin
REPAIR_TIMEOUT_SECONDS = 120

async def handle_health_change(health: ComponentHealth) -> None:
    if health.status in ("healthy",):
        return  # recovery - nothing to do

    name = health.name

    if name.startswith("llm:"):
        await _repair_llm_provider(name.removeprefix("llm:"), health.error)
    elif name == "redis":
        await _repair_redis(health.error)
    elif name.startswith("channel:"):
        await _repair_channel_adapter(name.removeprefix("channel:"), health.error)
    elif name.startswith("egress:"):
        await _alert_egress_failure(name, health.error)

async def _repair_llm_provider(provider_name: str, error: str) -> None:
    from keprix.brain.llm_router import LLMRouter
    router = LLMRouter.get_instance()

    # Demote the failing provider - bump it down the fallback chain
    router.demote_provider(provider_name, reason=error)

    await report_security_event("config_auto_repair", "warning", {
        "action": "llm_provider_demoted",
        "provider": provider_name,
        "reason": error[:200],
        "new_primary": router.current_primary(),
    })

async def _repair_redis(error: str) -> None:
    from keprix.db.redis_client import reconnect_redis
    for attempt in range(5):
        await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
        try:
            await reconnect_redis()
            await report_security_event("config_auto_repair", "info", {
                "action": "redis_reconnected",
                "attempt": attempt + 1,
            })
            return
        except Exception:
            continue

    # Failed to reconnect - switch to in-memory fallback and alert admin
    from keprix.db.memory_fallback import activate_memory_fallback
    activate_memory_fallback()
    await report_security_event("config_auto_repair", "critical", {
        "action": "redis_fallback_activated",
        "note": "Redis unreachable after 5 attempts. Running on in-memory cache. Data will be lost on restart.",
    })

async def _repair_channel_adapter(adapter_name: str, error: str) -> None:
    from keprix.gateway.adapter_registry import get_adapter
    adapter = get_adapter(adapter_name)
    if not adapter:
        return
    for attempt in range(3):
        await asyncio.sleep(5 * (attempt + 1))
        try:
            await adapter.reconnect()
            await report_security_event("config_auto_repair", "info", {
                "action": "channel_reconnected",
                "adapter": adapter_name,
                "attempt": attempt + 1,
            })
            return
        except Exception:
            continue
    await report_security_event("config_auto_repair", "warning", {
        "action": "channel_repair_failed",
        "adapter": adapter_name,
        "note": "Manual reconnection required. Check adapter credentials.",
    })

async def _alert_egress_failure(name: str, error: str) -> None:
    await report_security_event("config_auto_repair", "warning", {
        "action": "egress_host_unreachable",
        "host": name,
        "error": error[:200],
        "note": "Check network connectivity and DNS. If persistent, verify the allowlist.",
    })
```

---

## 3. Config Optimizer

The optimizer analyzes 7 days of telemetry and proposes configuration changes.
All proposals are written to a proposals file and presented to the user for approval.
Nothing is applied automatically.

### File: `keprix/config/optimizer.py`

```python
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any

DATA_DIR = Path("/data/keprix")
PROPOSALS_FILE = DATA_DIR / "config_proposals.jsonl"

@dataclass
class ConfigProposal:
    proposal_id: str
    category: str
    description: str
    current_value: Any
    proposed_value: Any
    rationale: str
    env_key: str
    risk: str  # "low" | "medium" | "high"
    created_at: float

async def run_optimizer(telemetry_db) -> list[ConfigProposal]:
    proposals: list[ConfigProposal] = []

    # Proposal: switch default LLM if error rate > 15% over 7 days
    provider_stats = await telemetry_db.fetch_provider_stats(days=7)
    for provider, stats in provider_stats.items():
        if stats["error_rate"] > 0.15 and stats["call_count"] > 100:
            proposals.append(ConfigProposal(
                proposal_id=f"llm-swap-{int(time.time())}",
                category="llm_routing",
                description=f"Demote {provider} - {stats['error_rate']*100:.0f}% error rate over 7 days",
                current_value=provider,
                proposed_value=stats["next_best_provider"],
                rationale=f"{stats['call_count']} calls, {stats['error_count']} failures.",
                env_key="keprix_DEFAULT_LLM_PROVIDER",
                risk="low",
                created_at=time.time(),
            ))

    # Proposal: increase memory write rate limit if legitimate writes are being dropped
    memory_stats = await telemetry_db.fetch_memory_stats(days=7)
    if memory_stats["legitimate_drop_rate"] > 0.05:
        proposals.append(ConfigProposal(
            proposal_id=f"mem-ratelimit-{int(time.time())}",
            category="memory",
            description="Increase memory write rate limit - legitimate writes being dropped",
            current_value=memory_stats["current_limit"],
            proposed_value=min(memory_stats["current_limit"] * 2, 200),
            rationale=f"{memory_stats['legitimate_drop_rate']*100:.1f}% of non-injection writes dropped.",
            env_key="keprix_MEMORY_WRITE_LIMIT_PER_HOUR",
            risk="medium",
            created_at=time.time(),
        ))

    # Proposal: disable unused channel adapters
    channel_stats = await telemetry_db.fetch_channel_stats(days=7)
    for channel, stats in channel_stats.items():
        if stats["message_count"] == 0 and stats["enabled"]:
            proposals.append(ConfigProposal(
                proposal_id=f"channel-disable-{channel}-{int(time.time())}",
                category="channels",
                description=f"Disable {channel} adapter - zero messages in 7 days",
                current_value="enabled",
                proposed_value="disabled",
                rationale="Unused adapters are attack surface. Disable until needed.",
                env_key=f"keprix_{channel.upper()}_ENABLED",
                risk="low",
                created_at=time.time(),
            ))

    # Write proposals to file for user review
    PROPOSALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PROPOSALS_FILE.open("a") as f:
        for p in proposals:
            f.write(json.dumps(p.__dict__) + "\n")

    return proposals

async def apply_proposal(proposal_id: str, approved_by: str) -> bool:
    """Apply a proposal after user confirmation. Returns True on success."""
    proposals = _load_pending_proposals()
    p = next((p for p in proposals if p["proposal_id"] == proposal_id), None)
    if not p:
        return False

    env_key = p["env_key"]
    proposed_value = p["proposed_value"]

    # Write to .env file (in the data dir, not source)
    env_file = DATA_DIR / "overrides.env"
    _set_env_var(env_file, env_key, str(proposed_value))

    from keprix.security.event_reporter import report_security_event
    await report_security_event("config_proposal_applied", "info", {
        "proposal_id": proposal_id,
        "approved_by": approved_by,
        "env_key": env_key,
        "new_value": str(proposed_value),
    })
    return True

def _load_pending_proposals() -> list[dict]:
    if not PROPOSALS_FILE.exists():
        return []
    with PROPOSALS_FILE.open() as f:
        return [json.loads(line) for line in f if line.strip()]

def _set_env_var(env_file: Path, key: str, value: str) -> None:
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    updated = False
    result = []
    for line in lines:
        if line.startswith(f"{key}="):
            result.append(f"{key}={value}")
            updated = True
        else:
            result.append(line)
    if not updated:
        result.append(f"{key}={value}")
    env_file.write_text("\n".join(result) + "\n")
```

---

## 4. Environment Discovery (First-Run Wizard)

On first install, before starting the agent, run environment discovery to generate
a working `.env` from scratch. The wizard probes available resources and asks
minimal questions.

### File: `keprix/config/env_discovery.py`

```python
import asyncio
import os
import socket
import subprocess
from pathlib import Path
import httpx

ENV_OUT = Path("/data/keprix/generated.env")

PROVIDER_ENDPOINTS: list[tuple[str, str, str]] = [
    ("DEEPSEEK", "keprix_DEEPSEEK_API_KEY", "https://api.deepseek.com/"),
    ("GROQ", "keprix_GROQ_API_KEY", "https://api.groq.com/"),
    ("OPENAI", "keprix_OPENAI_API_KEY", "https://api.openai.com/"),
    ("ANTHROPIC", "keprix_ANTHROPIC_API_KEY", "https://api.anthropic.com/"),
    ("OPENROUTER", "keprix_OPENROUTER_API_KEY", "https://openrouter.ai/"),
]

async def discover_environment() -> dict[str, str]:
    """
    Probes the environment and returns a dict of env vars that should be set.
    Call this on first run, before starting the agent.
    """
    config: dict[str, str] = {}

    print("keprix - Environment Discovery")
    print("This wizard runs once to configure keprix for your system.")
    print("")

    # 1. Detect available memory and set appropriate limits
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                    total_mb = total_kb // 1024
                    # Recommend Redis limit at 25% of available RAM
                    redis_limit = max(128, total_mb // 4)
                    config["keprix_REDIS_MAXMEMORY"] = f"{redis_limit}mb"
                    print(f"System RAM: {total_mb}MB - Redis will use up to {redis_limit}MB")
                    break
    except Exception:
        config["keprix_REDIS_MAXMEMORY"] = "512mb"

    # 2. Find a free port for the API server
    for port in range(8000, 8100):
        with socket.socket() as s:
            if s.connect_ex(("localhost", port)) != 0:
                config["keprix_API_PORT"] = str(port)
                print(f"API server will use port {port}")
                break

    # 3. Probe reachable LLM providers (based on what keys are in the environment)
    reachable: list[str] = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, env_key, url in PROVIDER_ENDPOINTS:
            key = os.environ.get(env_key, "")
            if not key:
                print(f"  {name}: no key set (skipping)")
                continue
            try:
                r = await client.head(url)
                print(f"  {name}: reachable (HTTP {r.status_code})")
                reachable.append(name.lower())
            except Exception:
                print(f"  {name}: unreachable (network error)")

    # Set provider priority based on what's reachable
    if reachable:
        config["keprix_LLM_PROVIDER_PRIORITY"] = ",".join(reachable)
        config["keprix_DEFAULT_LLM_PROVIDER"] = reachable[0]
        print(f"LLM provider priority: {', '.join(reachable)}")
    else:
        print("WARNING: No LLM providers reachable. Add at least one API key.")

    # 4. Check Docker availability (needed for keprix Agent sandbox)
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=10)
        config["keprix_SANDBOX_ENABLED"] = "true"
        config["keprix_SANDBOX_DRIVER"] = "docker"
        print("Docker: available - keprix Agent sandbox enabled")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        config["keprix_SANDBOX_ENABLED"] = "false"
        print("Docker: not available - keprix Agent sandbox disabled")
        print("  To enable: install Docker and re-run: keprix configure")

    # 5. Generate a secure Redis password if not already set
    if not os.environ.get("keprix_REDIS_PASSWORD"):
        import secrets
        pw = secrets.token_urlsafe(32)
        config["keprix_REDIS_PASSWORD"] = pw
        config["keprix_REDIS_URL"] = f"redis://:{pw}@redis:6379"
        print("Redis: generated secure password")

    # 6. Write generated config
    ENV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with ENV_OUT.open("w") as f:
        f.write("# Auto-generated by keprix environment discovery\n")
        f.write("# Edit this file or run: keprix configure\n\n")
        for k, v in sorted(config.items()):
            f.write(f"{k}={v}\n")

    print(f"\nConfiguration written to: {ENV_OUT}")
    print("Start the agent with: keprix start")
    return config
```

---

## 5. CLI Commands for Self-Configuration

Add these CLI commands to the keprix CLI (alongside `start`, `stop`, etc.):

```
keprix configure        Run environment discovery (first-run wizard)
keprix health           Show current component health status
keprix proposals        List pending config optimization proposals
keprix approve <id>     Apply a config proposal after review
keprix reject <id>      Dismiss a proposal
keprix repair           Manually trigger auto-repair for all components
keprix rollback <key>   Roll back a specific env var to its previous value
```

### File: `keprix/cli/config_commands.py`

```python
import asyncio
import json
import click
from keprix.config.env_discovery import discover_environment
from keprix.config.health_monitor import ConfigHealthMonitor
from keprix.config.optimizer import _load_pending_proposals, apply_proposal

@click.command()
def configure():
    """Run environment discovery and generate a configuration file."""
    asyncio.run(discover_environment())

@click.command()
def health():
    """Show current health status of all components."""
    monitor = ConfigHealthMonitor()
    asyncio.run(monitor._run_all_checks())
    results = monitor.get_all()
    if not results:
        click.echo("No health data yet. Is the agent running?")
        return
    click.echo(f"{'Component':<35} {'Status':<12} {'Latency':>10}")
    click.echo("-" * 60)
    for name, h in sorted(results.items()):
        status_color = "green" if h.status == "healthy" else "red" if h.status == "down" else "yellow"
        latency = f"{h.latency_ms:.0f}ms" if h.latency_ms > 0 else "-"
        click.echo(f"{name:<35} {click.style(h.status, fg=status_color):<12} {latency:>10}")
        if h.error:
            click.echo(f"  Error: {h.error[:80]}")

@click.command()
def proposals():
    """List pending configuration optimization proposals."""
    pending = _load_pending_proposals()
    if not pending:
        click.echo("No pending proposals.")
        return
    for p in pending:
        risk_color = "red" if p["risk"] == "high" else "yellow" if p["risk"] == "medium" else "green"
        click.echo(f"[{p['proposal_id']}] {click.style(p['risk'].upper(), fg=risk_color)} - {p['category']}")
        click.echo(f"  {p['description']}")
        click.echo(f"  Current: {p['current_value']}  ->  Proposed: {p['proposed_value']}")
        click.echo(f"  Rationale: {p['rationale']}")
        click.echo(f"  Env var: {p['env_key']}")
        click.echo("")

@click.command()
@click.argument("proposal_id")
def approve(proposal_id: str):
    """Apply a config proposal."""
    import getpass
    approved_by = getpass.getuser()
    success = asyncio.run(apply_proposal(proposal_id, approved_by))
    if success:
        click.echo(f"Applied proposal {proposal_id}. Restart the agent to pick up the change.")
    else:
        click.echo(f"Proposal {proposal_id} not found.")
```

---

## 6. Self-Configuration via Natural Language

The agent can also receive self-configuration instructions in natural language
through any channel. These are handled as a special intent class that routes
to the Config Manager rather than the general tool executor.

```
User: "Carina, switch to using Groq as your primary LLM for the next week"
User: "Turn off the Telegram channel, we're not using it"
User: "Your Redis memory is getting full, clear old memories older than 30 days"
User: "Can you check your own health and tell me what's wrong?"
User: "Configure yourself for a low-memory environment - we only have 2GB"
```

### File: `keprix/agents/self_config_agent.py`

```python
from keprix.config.health_monitor import ConfigHealthMonitor
from keprix.config.optimizer import _load_pending_proposals
from keprix.security.event_reporter import report_security_event

SELF_CONFIG_KEYWORDS = frozenset({
    "configure yourself",
    "configure carina",
    "switch provider",
    "change provider",
    "use groq",
    "use deepseek",
    "use openai",
    "turn off",
    "disable channel",
    "enable channel",
    "clear old memories",
    "check your health",
    "health check",
    "what's wrong with you",
    "low memory mode",
    "optimize yourself",
})

def is_self_config_request(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in SELF_CONFIG_KEYWORDS)

async def handle_self_config_request(
    text: str,
    session_id: str,
    authorized_by: str,
) -> str:
    """
    Route natural language self-config requests to the appropriate subsystem.
    All config changes require the session to have admin privilege level.
    Returns a response string.
    """
    t = text.lower()

    if "health" in t or "what's wrong" in t:
        monitor = ConfigHealthMonitor()
        await monitor._run_all_checks()
        results = monitor.get_all()
        down = [h for h in results.values() if h.status != "healthy"]
        if not down:
            return "All components are healthy."
        lines = ["The following components have issues:"]
        for h in down:
            lines.append(f"- {h.name}: {h.status} ({h.error[:100]})")
        return "\n".join(lines)

    if "proposals" in t or "optimize" in t:
        pending = _load_pending_proposals()
        if not pending:
            return "No pending optimization proposals."
        lines = [f"{len(pending)} proposal(s) pending:"]
        for p in pending[:5]:
            lines.append(f"- [{p['proposal_id']}] {p['description']}")
        return "\n".join(lines)

    await report_security_event("self_config_request", "info", {
        "text_preview": text[:200],
        "authorized_by": authorized_by,
        "session_id": session_id,
        "note": "Self-config request routed to natural language handler",
    })

    return (
        "I can help reconfigure myself. For safety, complex configuration changes "
        "require using the CLI: `keprix configure` or `keprix proposals`. "
        "For quick changes like switching providers, please confirm: "
        f"did you want me to {text[:80]}? Reply 'yes' to confirm."
    )
```

---

## Acceptance Criteria

- `keprix configure` runs without error on a fresh system with no `.env`.
- After discovery, `generated.env` contains at minimum `keprix_API_PORT`,
  `keprix_REDIS_PASSWORD`, and `keprix_DEFAULT_LLM_PROVIDER`.
- `keprix health` shows at least one component after 60 seconds of uptime.
- When DeepSeek returns 503 in tests, the LLM router automatically falls back to
  the next configured provider within 5 seconds.
- When Redis drops, the agent logs a `config_auto_repair` event and activates the
  in-memory fallback without crashing.
- `keprix proposals` lists proposals generated by the optimizer after
  injecting a simulated 20% error rate on one provider over 7 days of fake telemetry.
- `keprix approve <id>` writes the new value to `overrides.env` and logs the
  change with the approver's username.
- Natural language health query ("check your health") returns a formatted status summary.
- All self-config actions (auto-repair, proposal application, manual override) are
  logged as `config_auto_repair` or `config_proposal_applied` security events.
- Self-configuration changes are independent of the keprix Agent: no Python code is
  generated during self-configuration; existing code paths are reconfigured, not rewritten.
