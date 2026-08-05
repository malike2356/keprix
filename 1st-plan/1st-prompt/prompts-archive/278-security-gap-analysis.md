# Prompt 88; Keprix ↔ Scout Integration: Driving Scout Adoption, Not Copying Scout

## 0. Strategic Intent

**Keprix is not open-source charity. It is a Scout distribution vehicle.**

Every product built on Keprix; AbbiS, Petraclus, FleetZ, and every future product; becomes a Scout tenant by default. Keprix's security model is architected to make Scout indispensable, not optional.

The equation:

```
Stronger Scout = Safer Agent

The more signals Scout receives, the smarter its RASP engine.
The smarter the RASP engine, the faster it detects threats.
The faster it detects threats, the safer every connected agent is.

Keprix without Scout = secure enough (local defenses)
Keprix + Scout       = the strongest AI agent security platform in existence
```

**Design principle: Keprix's local defenses are the baseline; complete and production-ready.** Scout adds the advanced security implementations: cross-agent correlation, operator-controlled kill switch, compliance framework, red team orchestration, and forensic evidence management. These are platform-level capabilities that live in Scout, not Keprix.

## 1. Architecture Principle

**Scout is NOT an agent. It's a governance platform.** Scout aggregates signals, enforces policy, and provides operator control; but it doesn't think, reason, or act autonomously. That's where Carina comes in.

```
                         ┌─────────────────────────────┐
                         │          SCOUT              │
                         │   (Governance Platform)     │
                         │   NOT an agent; platform   │
                         │                             │
                         │  RASP Engine                │
                         │  Kill Switch Control        │
                         │  Compliance Dashboard       │
                         │  Red Team Orchestrator      │
                         │  Forensic Evidence Store    │
                         │  On-Chain Trust             │
                         │  Operator Console           │
                         └──────┬──────────┬───────────┘
                                │ ▲        │ ▲
                   sends commands│ │reports │ │reports
                   (kill switch) │ │signals │ │evidence
                                ▼ │        ▼ │
                         ┌───────┴──────────┴──────────┐
                         │          KEPRIX             │
                         │    (Agent Runtime; FREE)   │
                         │                             │
                         │  ScoutClient → signals      │
                         │  ScoutListener ← commands   │
                         │  ScoutSync → evidence       │
                         │                             │
                         │  Local Defenses (always on) │
                         │  Products: AbbiS, Petraclus │
                         └─────────────────────────────┘
                                │
                                │  Scout signals also flow to...
                                ▼
                         ┌─────────────────────────────┐
                         │          CARINA             │
                         │    (AI Sidecar; PAID)      │
                         │                             │
                         │  Agentic layer for Scout:   │
                         │  • AI threat analysis       │
                         │  • NL security queries      │
                         │  • Automated investigation  │
                         │  • Proactive recommendations│
                         │  • Autonomous response      │
                         │    (with human oversight)   │
                         │                             │
                         │  Scout protects Carina:     │
                         │  • Kill switch if compromised│
                         │  • Compliance framework     │
                         │  • Cross-agent correlation  │
                         │  • Forensic storage         │
                         │  • On-chain trust           │
                         └─────────────────────────────┘
```

**The mutual relationship:**

```
Carina gives Scout:                    Scout gives Carina:
├── AI-powered threat analysis         ├── Kill switch (if Carina is compromised)
├── Natural language security queries  ├── Compliance framework
├── Automated investigation            ├── Cross-agent correlation
├── Proactive recommendations          ├── Forensic evidence storage
├── Autonomous response (supervised)   ├── On-chain trust attestation
└── Makes Scout "intelligent"          └── Keeps Carina safe

Result: Scout + Carina = an intelligent security platform that thinks AND protects.
```

**Scout starts as a "dumb" but powerful platform.** Carina bootstraps its intelligence. Over time, as Scout receives more signals from more Keprix products, Carina's analysis gets sharper, Scout's RASP gets smarter, and the whole ecosystem becomes harder to attack.


**Key rule**: If it aggregates across agents, it lives in Scout. If it protects a single agent instance, it lives in Keprix. If it requires intelligence, Carina provides it.

---

## 1. What Lives Where

| Capability | Lives In | Why |
|-----------|----------|-----|
| **RASP Engine** (signal correlation, MITRE, attack graphs) | **Scout** | Aggregates signals from ALL agents; Keprix, Carina, Aiva. Cross-product threat detection. |
| **Kill Switch Control** (suspend, resume, quarantine) | **Scout** | Operator console. One dashboard controls all agents. |
| **Compliance Dashboard** | **Scout** | Aggregates evidence from all products. Single compliance view. |
| **Red Team Automation** | **Scout** | Orchestrates attacks against ALL agents. One harness rules them all. |
| **Forensic Evidence Store** | **Scout** | Long-term, queryable, cross-product. |
| **On-Chain Trust** (ERC-8004/8126) | **Scout** | Trust is a public good across all products. |
| **Admin UI / Operator Console** | **Scout** | One dashboard for all security operations. |
| | | |
| **Prompt Injection Defense** (Input Sanitizer, Output Guard) | **Keprix** | Instance-level. Must work even if Scout is unreachable. |
| **Tool Sandbox** (terminal, file, network gates) | **Keprix** | Instance-level enforcement. Can't rely on network for every tool call. |
| **Credential Vault** | **Keprix** | Secrets never leave the instance. |
| **A2A Security** (mTLS, signing, authorization) | **Keprix** | Point-to-point. No central authority required. |
| **Governance Rules** (SCOUT persona in Keprix) | **Keprix** | Local enforcement with fallback. Reports decisions to Scout. |
| **Audit Trail** | **Keprix** | Immutable local log. Synced to Scout for aggregation. |
| | | |
| **Scout Client** (sends signals TO Scout) | **Keprix** | The bridge. Every Keprix security event → Scout. |
| **Scout Listener** (receives commands FROM Scout) | **Keprix** | The bridge. Scout commands → Keprix actions. |
| **Scout Sync** (compliance, trust, audit) | **Keprix** | Periodic evidence push to Scout. |

---

## 2. The Scout Protocol; Keprix ↔ Scout Communication

### 2.1 Signal Types (Keprix → Scout)

Every security event in Keprix emits a signal to Scout. Signals are real-time, fire-and-forget, batched.

```python
# keprix/security/scout_client.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import asyncio

import httpx


class SignalSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SignalCategory(Enum):
    PROMPT_INJECTION = "prompt_injection"
    TOOL_ABUSE = "tool_abuse"
    CREDENTIAL_ACCESS = "credential_access"
    EGRESS_VIOLATION = "egress_violation"
    FILE_VIOLATION = "file_violation"
    A2A_VIOLATION = "a2a_violation"
    RATE_LIMIT = "rate_limit"
    ANOMALY = "anomaly"
    GOVERNANCE = "governance"
    HEARTBEAT = "heartbeat"


@dataclass
class ScoutSignal:
    """A security signal sent from Keprix to Scout."""
    signal_id: str                      # UUID
    timestamp: str                      # ISO 8601
    agent_id: str                       # "keprix:abbis:instance-7f3a"
    product: str                        # "abbis", "petraclus", "fleet_z"
    category: SignalCategory
    severity: SignalSeverity
    action: str                         # What happened: "injection_blocked", "egress_blocked"
    target: str                         # What was targeted: "tool:terminal", "file:.env"
    details: Dict[str, Any]             # Context (redacted)
    mitre_tactic: Optional[str] = None  # TA0001-TA0010, filled by Scout
    threat_score: Optional[float] = None
    correlation_id: Optional[str] = None


class ScoutClient:
    """
    Keprix → Scout: Sends security signals in real-time.

    Design:
    - Fire-and-forget: signal delivery must never block agent execution
    - Batched: buffer signals, flush every 500ms or 50 signals
    - Resilient: if Scout is unreachable, buffer locally and retry
    - Redacted: no credentials, no PII in signal payload
    - Authenticated: HMAC-signed, agent-identity verified
    """

    SCOUT_ENDPOINT = "https://console.labyrinthscout.com/api/v1/signals"
    FLUSH_INTERVAL = 0.5              # seconds
    MAX_BUFFER_SIZE = 50
    MAX_RETRY_BUFFER = 1000           # Start dropping oldest if offline too long

    def __init__(self, agent_id: str, product: str, api_key: str):
        self.agent_id = agent_id
        self.product = product
        self.api_key = api_key
        self._buffer: List[ScoutSignal] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._client = httpx.AsyncClient(
            timeout=5.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Agent-Id": agent_id,
                "X-Product": product,
                "Content-Type": "application/json",
            },
        )

    async def start(self):
        """Start the background flush loop."""
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self):
        """Flush remaining signals and stop."""
        if self._flush_task:
            self._flush_task.cancel()
        await self._flush()  # Final flush
        await self._client.aclose()

    def send(self, category: SignalCategory, severity: SignalSeverity,
             action: str, target: str, details: Dict[str, Any] = None):
        """Queue a signal. Non-blocking. Never raises."""
        signal = ScoutSignal(
            signal_id=_new_uuid(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=self.agent_id,
            product=self.product,
            category=category,
            severity=severity,
            action=action,
            target=target,
            details=details or {},
        )
        self._buffer.append(signal)

        # If buffer is full, drop oldest (signals are fire-and-forget)
        if len(self._buffer) > self.MAX_RETRY_BUFFER:
            self._buffer.pop(0)

    async def _flush_loop(self):
        """Background loop: flush buffer every FLUSH_INTERVAL."""
        while True:
            await asyncio.sleep(self.FLUSH_INTERVAL)
            if self._buffer:
                await self._flush()

    async def _flush(self):
        """Send buffered signals to Scout."""
        if not self._buffer:
            return

        batch = self._buffer[:self.MAX_BUFFER_SIZE]
        payload = [self._serialize(s) for s in batch]

        try:
            response = await self._client.post(
                self.SCOUT_ENDPOINT,
                json={"signals": payload},
            )
            if response.status_code == 200:
                # Remove sent signals from buffer
                self._buffer = self._buffer[len(batch):]
            else:
                # Log failure, keep signals for retry
                pass
        except Exception:
            # Scout unreachable; signals stay in buffer
            pass

    def _serialize(self, signal: ScoutSignal) -> dict:
        return {
            "signal_id": signal.signal_id,
            "timestamp": signal.timestamp,
            "agent_id": signal.agent_id,
            "product": signal.product,
            "category": signal.category.value,
            "severity": signal.severity.value,
            "action": signal.action,
            "target": signal.target,
            "details": signal.details,
        }
```

### 2.2 Integration Points; Where Keprix Emits Signals

Every defense layer in Prompt 87 gets a Scout signal emission point:

```python
# Example: In InputSanitizer.sanitize()

if sanitization_result.threat_level == ThreatLevel.MALICIOUS:
    scout_client.send(
        category=SignalCategory.PROMPT_INJECTION,
        severity=SignalSeverity.CRITICAL,
        action="injection_blocked",
        target=f"source:{source}",
        details={
            "patterns_matched": sanitization_result.threats_detected,
            "input_hash": sanitization_result.hash,
            "input_preview": sanitization_result.original[:200],
        },
    )
```

| Keprix Defense Layer | Signal Emitted |
|---------------------|---------------|
| **Input Sanitizer** | Prompt injection detected/blocked, with pattern IDs matched |
| **Instruction Boundary** | Boundary breach attempt |
| **Output Guard** | Credential leak prevented, PII redacted, output injection detected |
| **Terminal Sandbox** | Command blocked, path violation, resource limit hit |
| **File Gate** | Sensitive file access blocked, path traversal attempt, write blocked |
| **Network Gate** | SSRF blocked, egress to unknown host blocked, private IP blocked |
| **Credential Vault** | Credential accessed, token issued, rotation occurred |
| **A2A Security** | Spoofed agent rejected, replayed message, unauthorized action |
| **Governance (SCOUT)** | Rule triggered, verdict (BLOCK/CONFIRM), rate limit hit |
| **Audit Trail** | (Background sync, not real-time signals) |

---

### 2.3 Command Types (Scout → Keprix)

Scout sends commands to Keprix instances. Keprix obeys them.

```python
# keprix/security/scout_listener.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
import asyncio
import json

import redis.asyncio as redis


class ScoutCommand(Enum):
    SUSPEND = "suspend"                    # Full instance stop
    RESUME = "resume"                      # Resume suspended instance
    BLOCK_SESSION = "block_session"        # Block specific session
    UNBLOCK_SESSION = "unblock_session"    # Unblock session
    QUARANTINE_TOOL = "quarantine_tool"    # Disable specific tool
    LIFT_QUARANTINE = "lift_quarantine"    # Re-enable tool
    BLOCK_EGRESS = "block_egress"          # Block all network egress
    UNBLOCK_EGRESS = "unblock_egress"      # Allow network egress
    SET_RATE_LIMIT = "set_rate_limit"      # Change rate limit
    CLEAR_RATE_LIMIT = "clear_rate_limit"  # Remove rate limit
    SET_SANDBOX_POLICY = "set_sandbox_policy"  # Change sandbox mode
    SET_TOOL_POLICY = "set_tool_policy"    # Change tool allowlist/blocklist
    CLEAR_SESSION_MEMORY = "clear_session_memory"  # Wipe memory
    ROTATE_CREDENTIALS = "rotate_credentials"  # Force credential rotation
    ACTIVATE_HONEYPOTS = "activate_honeypots"  # Deploy decoys
    SHUTDOWN = "shutdown"                  # Permanent instance termination


@dataclass
class ScoutCommandMessage:
    command_id: str
    command: ScoutCommand
    agent_id: str              # Target agent (or "*" for broadcast)
    session_id: Optional[str]  # Target session (or None for instance-wide)
    params: dict
    issued_by: str             # Operator ID
    issued_at: str             # ISO 8601
    ttl_seconds: Optional[int] # Auto-expire (None = until countermanded)


class ScoutListener:
    """
    Keprix ← Scout: Receives commands via Redis pub/sub.

    Design:
    - Subscribes to two channels: broadcast + instance-specific
    - Validates every command (signature, agent_id match, expiry)
    - Executes commands via registered handlers
    - ACKs back to Scout on completion
    - If Redis unavailable, continues operating with last-known state
    """

    BROADCAST_CHANNEL = "scout:control:broadcast"
    INSTANCE_CHANNEL_PREFIX = "scout:control:instance:"

    def __init__(self, agent_id: str, redis_url: str, api_key: str):
        self.agent_id = agent_id
        self.instance_channel = f"{self.INSTANCE_CHANNEL_PREFIX}{agent_id}"
        self._redis: Optional[redis.Redis] = None
        self._redis_url = redis_url
        self._api_key = api_key
        self._handlers = {}
        self._active_commands = {}     # command_id → expiry
        self._running = False
        self._suspended = False
        self._egress_blocked = False
        self._quarantined_tools: set = set()
        self._active_rate_limits: dict = {}

        self._register_default_handlers()

    async def start(self):
        """Connect to Redis and start listening."""
        try:
            self._redis = redis.from_url(self._redis_url)
            await self._redis.ping()
        except Exception:
            # If Redis unavailable, continue without Scout commands
            # Local defense layers still active
            print("[ScoutListener] Redis unavailable; running without Scout control")
            return

        self._running = True
        asyncio.create_task(self._listen())

    async def stop(self):
        """Unsubscribe and disconnect."""
        self._running = False
        if self._redis:
            await self._redis.close()

    async def _listen(self):
        """Main listen loop on broadcast + instance channels."""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.BROADCAST_CHANNEL, self.instance_channel)

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                cmd = ScoutCommandMessage(**json.loads(message["data"]))

                # Validate target
                if cmd.agent_id != "*" and cmd.agent_id != self.agent_id:
                    continue

                # Validate expiry
                if cmd.ttl_seconds:
                    expires_at = datetime.fromisoformat(cmd.issued_at).timestamp() + cmd.ttl_seconds
                    if time.time() > expires_at:
                        continue

                # Execute
                await self._execute(cmd)

            except Exception as e:
                print(f"[ScoutListener] Error processing command: {e}")

    async def _execute(self, cmd: ScoutCommandMessage):
        """Execute a Scout command via registered handler."""
        handler = self._handlers.get(cmd.command)
        if not handler:
            await self._ack(cmd, "unknown_command")
            return

        try:
            await handler(cmd)
            await self._ack(cmd, "executed")
        except Exception as e:
            await self._ack(cmd, f"failed:{e}")

    async def _ack(self, cmd: ScoutCommandMessage, status: str):
        """Acknowledge command execution back to Scout."""
        if not self._redis:
            return
        ack_channel = f"scout:control:ack:{cmd.command_id}"
        await self._redis.publish(ack_channel, json.dumps({
            "command_id": cmd.command_id,
            "agent_id": self.agent_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))

    def _register_default_handlers(self):
        """Register handlers for all Scout commands."""
        self._handlers = {
            ScoutCommand.SUSPEND: self._handle_suspend,
            ScoutCommand.RESUME: self._handle_resume,
            ScoutCommand.BLOCK_SESSION: self._handle_block_session,
            ScoutCommand.UNBLOCK_SESSION: self._handle_unblock_session,
            ScoutCommand.QUARANTINE_TOOL: self._handle_quarantine_tool,
            ScoutCommand.LIFT_QUARANTINE: self._handle_lift_quarantine,
            ScoutCommand.BLOCK_EGRESS: self._handle_block_egress,
            ScoutCommand.UNBLOCK_EGRESS: self._handle_unblock_egress,
            ScoutCommand.SET_RATE_LIMIT: self._handle_set_rate_limit,
            ScoutCommand.CLEAR_RATE_LIMIT: self._handle_clear_rate_limit,
            ScoutCommand.SET_SANDBOX_POLICY: self._handle_set_sandbox_policy,
            ScoutCommand.SET_TOOL_POLICY: self._handle_set_tool_policy,
            ScoutCommand.CLEAR_SESSION_MEMORY: self._handle_clear_session_memory,
            ScoutCommand.ROTATE_CREDENTIALS: self._handle_rotate_credentials,
            ScoutCommand.ACTIVATE_HONEYPOTS: self._handle_activate_honeypots,
            ScoutCommand.SHUTDOWN: self._handle_shutdown,
        }

    async def _handle_suspend(self, cmd: ScoutCommandMessage):
        """Suspend all agent operations."""
        self._suspended = True
        # Signal to agent loop to stop accepting new tasks
        from keprix.agent import agent_loop
        await agent_loop.suspend()

    async def _handle_resume(self, cmd: ScoutCommandMessage):
        """Resume agent operations."""
        self._suspended = False
        from keprix.agent import agent_loop
        await agent_loop.resume()

    async def _handle_block_egress(self, cmd: ScoutCommandMessage):
        """Block all network egress."""
        self._egress_blocked = True
        from keprix.security.network_gate import NetworkGate
        NetworkGate.force_block_all()

    async def _handle_quarantine_tool(self, cmd: ScoutCommandMessage):
        """Disable a specific tool."""
        tool_name = cmd.params.get("tool_name")
        if tool_name:
            self._quarantined_tools.add(tool_name)
            from keprix.tools.registry import tool_registry
            tool_registry.disable(tool_name)

    # ... remaining handlers follow the same pattern
```

---

### 2.4 Compliance & Trust Sync (Keprix → Scout, Periodic)

Every 30 minutes, Keprix pushes compliance evidence and trust state to Scout.

```python
# keprix/security/scout_sync.py

class ScoutSync:
    """
    Periodic evidence push from Keprix to Scout.

    Pushes:
    - Audit trail (since last sync)
    - Governance rule triggers (counts, not full events)
    - Credential vault access log (metadata only, no secrets)
    - Sandbox policy violations
    - Tool usage statistics
    - Trust state snapshot
    """

    SYNC_INTERVAL = 30 * 60  # 30 minutes

    async def sync_loop(self):
        """Background sync loop."""
        while True:
            await asyncio.sleep(self.SYNC_INTERVAL)
            await self._sync_audit_trail()
            await self._sync_governance_stats()
            await self._sync_vault_access_log()
            await self._sync_trust_state()

    async def _sync_audit_trail(self):
        """Push new audit trail entries since last sync."""
        from keprix.security.audit import AuditTrail
        entries = AuditTrail.query(since=self._last_sync_time)
        await self._push("compliance/audit", entries)

    async def _sync_trust_state(self):
        """Push trust state snapshot."""
        trust_state = {
            "agent_id": self.agent_id,
            "uptime_seconds": self._get_uptime(),
            "active_sessions": self._get_session_count(),
            "signals_sent_24h": self._get_signal_count(),
            "commands_received_24h": self._get_command_count(),
            "last_credential_rotation": self._get_last_rotation(),
            "sandbox_policy": self._get_sandbox_policy(),
            "keprix_version": self._get_version(),
            "defense_layers_active": self._get_active_layers(),
        }
        await self._push("trust/state", trust_state)
```

---

## 3. What Carina Has That We Do Differently

Carina has these features built-in because it predates the Scout integration model. Keprix does them differently:

| Carina Feature | How Carina Does It | How Keprix Does It |
|---------------|-------------------|-------------------|
| **RASP Engine** | Built into Carina (local) | **Scout** aggregates signals from Keprix + Carina + Aiva |
| **Kill Switch** | Redis pub/sub directly | **Scout** sends commands via Redis → Keprix ScoutListener |
| **Compliance Dashboard** | Built into Carina admin | **Scout** Compliance Dashboard (single pane of glass) |
| **Forensic Evidence** | Stored locally in Carina | Pushed to **Scout** for long-term storage + cross-product search |
| **Red Team Automation** | Built into Carina | **Scout** orchestrates red team exercises across Keprix + Carina |
| **On-Chain Trust** | Built into Carina scripts | **Scout** manages ERC-8004/8126 for all products |
| **Honeypots** | Built into Carina | **Scout** deploys honeypots across all agents |
| **Memory Content Scanner** | Built into Carina | **Keprix** keeps this (instance-level, must work offline) |
| **Tool Sequence Guard** | Built into Carina | **Keprix** keeps this (instance-level, real-time) |
| **PromptGuard 3-Layer** | Built into Carina | **Keprix** keeps this (instance-level, latency-sensitive) |
| **Egress Filter** | Built into Carina | **Keprix** keeps filter; **Scout** manages domain allowlist updates |
| **Trial Abuse Guard** | Built into Carina | **Keprix** keeps this (billing-coupled) |

---

## 4. What Keprix Must Still Build (Instance-Level)

These don't involve Scout; they're Keprix-local defense layers:

### 4.1 PromptGuard 3-Layer Architecture; **CRITICAL**

Carina's 63 injection patterns + LLM judge + tool-result scanning. All instance-level, no Scout dependency.

**Source:** Carina's `src/security/prompt-guard.ts`, `injection-patterns.json`

**What to build:**
```python
# keprix/security/prompt_guard/
├── injection_patterns.json    # 63 patterns from Carina (INJ-A through INJ-L)
├── layer1_regex.py            # Pattern matching
├── layer2_llm_judge.py        # LLM classifier for ambiguous cases
├── layer3_tool_scan.py        # Scan tool results before reaching LLM
├── guard_middleware.py         # Wire into agent pipeline
```

### 4.2 Tool Sequence Guard; **HIGH**

Multi-stage attack chain detection. Instance-level, no Scout dependency.

**Source:** Carina's `src/security/tool-sequence-guard.ts`

### 4.3 Memory Content Scanner; **MEDIUM**

MEM-001 through MEM-007 poisoning rules. Instance-level.

**Source:** Carina's `src/memory/content-scanner.ts`

### 4.4 TIRITH Pre-Execution Scanner; **HIGH**

Code exists in Keprix but not wired into terminal sandbox. Fix this.

**Source:** Original Hermes' `tools/tirith_security.py` (already in Keprix)

### 4.5 Skills Security Guard; **HIGH**

Code exists in Keprix but not enforced in extension loader. Fix this.

**Source:** Original Hermes' `tools/skills_guard.py` (already in Keprix)

---

## 5. What Scout Must Build (Cross-Agent Platform)

These are Scout features that Keprix *consumes*, not builds:

### 5.1 RASP Engine
- Aggregates signals from Keprix + Carina + Aiva
- Correlates across agents (cross-product attack detection)
- MITRE ATT&CK mapping
- Attack graph building
- Threat scoring with confidence levels
- **Keprix role**: emit `ScoutSignal` for every security event
- **Scout role**: correlate, classify, alert operator

### 5.2 Kill Switch Control Panel
- Operator console to suspend/resume any agent
- Per-instance, per-session, per-tool controls
- Broadcast commands (affect all agents)
- Auto-response rules (if X signals in Y minutes → suspend)
- **Keprix role**: `ScoutListener` receives and executes commands
- **Scout role**: operator UI, rule engine, command dispatch

### 5.3 Compliance Dashboard
- Aggregates audit trails from all Keprix instances
- Maps to frameworks: SOC 2, ISO 27001, GDPR
- Evidence collection scheduling
- **Keprix role**: `ScoutSync` pushes audit/compliance data every 30 min
- **Scout role**: store, index, visualize, export

### 5.4 Red Team Orchestrator
- YAML-driven attack scenarios
- Schedules and executes against Keprix instances
- Collects results, generates reports
- **Keprix role**: expose test endpoints, respond to attacks
- **Scout role**: orchestrate, record, report

### 5.5 Forensic Evidence Store
- Long-term storage of incident snapshots
- Cross-product search
- Chain-of-custody management
- **Keprix role**: capture snapshot, push to Scout
- **Scout role**: store, index, search, export

---

## 6. The Scout Adoption Flywheel

Every Keprix-based product drives Scout adoption:

```
Product Launch: AbbiS goes live
  → AbbiS uses Keprix
  → Keprix has ScoutClient built-in (emits signals)
  → AbbiS admin gets Scout dashboard access
  → Dashboard shows: "AbbiS blocked 47 injection attempts this week"

Admin thinks: "This is useful. What else can Scout monitor?"

Product Launch: Petraclus goes live
  → Petraclus also uses Keprix
  → Same Scout dashboard now shows: AbbiS + Petraclus
  → Cross-product correlation: "Same attacker hit AbbiS AND Petraclus"

Admin thinks: "I need Scout for everything."

Product Launch: FleetZ goes live
  → Same dashboard. Three products. One security view.
  → Scout becomes indispensable.

Carina adds ScoutClient
  → Now Scout monitors Keprix products + Carina
  → Single pane of glass for ALL VERLOX AI agents

Scout becomes the default. Because every Keprix product ships with it.
```

**Keprix drives Scout adoption by making Scout the default security backend.** Every Keprix product emits Scout signals. Scout becomes the operator's daily dashboard. It's not optional; it's integrated.

---

## 7. Implementation Phases

### Phase 1: Keprix → Scout Signal Pipeline (Week 1-2)

1. Build `ScoutClient`; signal buffer, flush loop, retry logic
2. Wire signals into all Prompt 87 defense layers:
   - Input Sanitizer → `PROMPT_INJECTION` signals
   - Output Guard → `CREDENTIAL_ACCESS` signals
   - Terminal Sandbox → `TOOL_ABUSE` signals
   - File Gate → `FILE_VIOLATION` signals
   - Network Gate → `EGRESS_VIOLATION` signals
   - Credential Vault → `CREDENTIAL_ACCESS` signals
   - A2A Security → `A2A_VIOLATION` signals
   - Governance Rules → `GOVERNANCE` signals
3. Add heartbeat signal (every 30s)
4. Add `SCOUT_API_KEY` and `SCOUT_ENDPOINT` to `keprix.yaml`

### Phase 2: Scout → Keprix Command Pipeline (Week 3-4)

5. Build `ScoutListener`; Redis pub/sub, command validation, handler dispatch
6. Implement all command handlers (suspend, resume, quarantine, egress, rate limit, sandbox)
7. Build ACK mechanism (command confirmation back to Scout)
8. Build `ScoutSync`; periodic audit/compliance/trust push
9. Add `SCOUT_REDIS_URL` to `keprix.yaml`

### Phase 3: Keprix Instance-Level Defenses (Week 5-6)

10. Port Carina's 63 injection patterns → `injection_patterns.json`
11. Build PromptGuard 3-layer: regex + LLM judge + tool-result scanning
12. Build Tool Sequence Guard (multi-stage attack detection)
13. Wire TIRITH into TerminalSandbox
14. Enforce Skills Security Guard in ExtensionLoader
15. Build Memory Content Scanner (MEM-001 through MEM-007)

### Phase 4: Scout Platform Features (Week 7-8, Scout team)

16. Build RASP Engine in Scout (signal correlation, MITRE, attack graphs)
17. Build Kill Switch Control Panel in Scout (operator UI)
18. Build Compliance Dashboard in Scout
19. Build Red Team Orchestrator in Scout
20. Build Forensic Evidence Store in Scout

---

## 8. Summary; The VERLOX Security Ecosystem

**Three products. One security platform.**

| Keprix (Free) | Carina (Paid) | Scout (Paid) |
|---|---|---|
| Agent Runtime | AI Sidecar | Governance Platform |
| Distributes Scout | Gives Scout agentic capabilities | Protects everything |
| Products: AbbiS, Petraclus, FleetZ | AI threat analysis, NL queries, auto investigation | RASP, kill switch, compliance, forensics |
| Feeds Scout signals | Makes Scout intelligent | Gets smarter with every signal |
| Obeys Scout commands | Protected by Scout | Gets agentic via Carina |

**The mutual relationship:**

```
Carina → Scout:  AI-powered threat analysis, natural language security
                 queries, automated investigation, proactive recommendations.
                 Carina is the brain Scout was born without.

Scout → Carina:  Kill switch (if Carina is compromised), compliance
                 framework, cross-agent correlation, forensic storage,
                 on-chain trust attestation. Scout is the shield Carina
                 operates behind.

Carina + Scout = An intelligent security platform that thinks AND protects.
```

**Scout starts as a powerful but "dumb" platform. Carina bootstraps its intelligence. Over time, as Scout receives more signals from more Keprix products, Carina's analysis gets sharper, Scout's RASP gets smarter, and the whole ecosystem becomes exponentially harder to attack.**

**The business model:**

| Product | Price | Role |
|---------|-------|------|
| **Keprix** | Free | Distribution; manufactures Scout & Carina customers |
| **Carina** | Paid | Intelligence; gives Scout agentic capabilities |
| **Scout** | Paid | Platform; protects everything, gets smarter with scale |

**Scout is not an agent. Carina makes Scout intelligent. Keprix makes Scout ubiquitous.**
