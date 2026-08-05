# Keprix - Prompt 81: Adopt OmniRoute; A2A Protocol, Compliance & Observability

## Context

OmniRoute's A2A (Agent-to-Agent) protocol, compliance layer, and observability dashboard round out the gateway capabilities. This prompt adopts the remaining features that make OmniRoute production-grade: agent-to-agent communication, compliance audit trails, and real-time monitoring.

## Reference Clone

`planning/competitor-research/agents-to-adopt/omniroute/`

Key source files:
```
src/lib/a2a/; taskExecution.ts, taskManager.ts, streaming.ts, routingLogger.ts
src/lib/compliance/; noLog.ts, providerAudit.ts
src/lib/usage/; routeExplain.ts, comboHealth.ts, comboForecast.ts
src/lib/monitoring/; Real-time metrics and health dashboards
src/lib/evals/; Provider evaluation framework
src/lib/memory/; Agent memory integration (Obsidian)
```

## What to Adopt

### Layer 1: A2A Protocol (Agent-to-Agent)

OmniRoute's A2A protocol allows agents to discover, communicate with, and delegate to other agents through the gateway. This complements Keprix's multi-agent messaging (already adopted from AutoGen in a prior prompt).

```
A2A FLOW:

  Agent A (NEXUS)
       │  "I need a security audit of 10.0.0.0/24"
       ▼
  ┌──────────────────────────────────────────┐
  │  KEPRIX A2A GATEWAY                     │
  │  ─────────────────────────────────────── │
  │  Task Manager (adopt from taskManager)    │
  │  ┌────────────────────────────────────┐  │
  │  │ 1. Parse task intent              │  │
  │  │ 2. Discover capable agents        │  │
  │  │ 3. Route to best agent(s)         │  │
  │  │ 4. Stream progress back           │  │
  │  │ 5. Aggregate results              │  │
  │  └────────────────────────────────────┘  │
  └──────────┬───────────────────────────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
  WARDEN   FORGE    SAGE
  (scan)  (exploit) (research)
```

### Layer 2: Compliance & Audit Trail

Every routing decision, every provider call, every guardrail trigger; logged with full context for compliance.

```
COMPLIANCE AUDIT TRAIL:

  Request ID: req_abc123
  ┌──────────────────────────────────────────────┐
  │ TIMELINE                                     │
  │ ──────────────────────────────────────────── │
  │ 22:15:00.001  Request received               │
  │ 22:15:00.002  PII check: 1 email masked      │
  │ 22:15:00.003  Prompt injection: CLEAN        │
  │ 22:15:00.005  Combo: "default" selected      │
  │ 22:15:00.006  Tier 1: kiro → try            │
  │ 22:15:00.450  Tier 1: kiro → quota exhausted │
  │ 22:15:00.451  Tier 1: qoder → try           │
  │ 22:15:01.200  Tier 1: qoder → SUCCESS       │
  │ 22:15:01.201  Compression: saved 42% tokens  │
  │ 22:15:03.500  Response received (234 tokens)  │
  │ 22:15:03.501  PII unmask: 1 email restored   │
  │ 22:15:03.502  Request complete (3.5s)        │
  └──────────────────────────────────────────────┘
```

### Layer 3: Observability Dashboard

Real-time visibility into provider health, combo performance, quota status, and cost.

```
OBSERVABILITY METRICS:

  PROVIDER HEALTH:
  ┌──────────────────────────────────────────────┐
  │ Provider  │ Status  │ Success │ Latency │ Qta│
  │───────────│─────────│─────────│─────────│────│
  │ kiro      │  OK   │ 99.2%   │ 1.2s    │ 67%│
  │ qoder     │  OK   │ 98.7%   │ 0.9s    │ 45%│
  │ deepseek  │  Warn │ 94.1%   │ 2.8s    │ 22%│
  │ groq      │  Down │ 45.0%   │ 8.2s    │ 0% │ ← Circuit open
  │ ollama    │  OK   │ 100%    │ 0.3s    │ ∞  │
  └──────────────────────────────────────────────┘
  
  COMBO PERFORMANCE:
  ┌──────────────────────────────────────────────┐
  │ Default combo (last 24h):                    │
  │   Requests: 14,230                           │
  │   Tier 1 success: 78% (free)                 │
  │   Tier 2 success: 18% (api keys)             │
  │   Tier 3 fallback: 4% (local)                │
  │   Avg latency: 1.4s                          │
  │   Tokens saved (compression): 2.1M (47%)     │
  │   Estimated cost saved: $8.40                │
  └──────────────────────────────────────────────┘
```

## Files To Create

```text
src/keprix/providers/a2a/
  __init__.py
  task_manager.py        # Agent task lifecycle management (adopt from taskManager.ts)
  task_execution.py      # Task execution and monitoring (adopt from taskExecution.ts)
  streaming.py           # Real-time task progress streaming (adopt from streaming.ts)
  agent_discovery.py     # Agent capability discovery and matching
  routing_logger.py      # A2A routing audit log (adopt from routingLogger.ts)

src/keprix/providers/observability/
  __init__.py
  metrics.py             # Provider and combo metrics collection
  dashboard_api.py       # API endpoints for dashboard data
  health_endpoint.py     # /health endpoint with provider status
  combo_forecast.py      # Predict combo performance and cost (adopt from comboForecast.ts)
  route_explain.py       # Explain routing decisions (adopt from routeExplain.ts)
  alerts.py              # Alert thresholds and notification triggers

src/keprix/providers/evals/
  __init__.py
  provider_eval.py       # Evaluate provider quality over time
  benchmark_runner.py    # Run benchmarks against providers
  quality_gates.py       # Minimum quality thresholds for promotion

src/keprix/providers/memory/
  __init__.py
  agent_memory.py        # Cross-session agent memory (adopt memory integration pattern)
  context_store.py       # Persistent context storage
  knowledge_graph.py     # Relationship mapping between sessions

api/observability/
  routes.py              # /api/observability/* endpoints
  websocket.py           # Real-time WebSocket metrics stream

tests/providers/a2a/
  test_task_manager.py
  test_task_execution.py
  test_streaming.py

tests/providers/observability/
  test_metrics.py
  test_dashboard_api.py
  test_alerts.py

tests/providers/evals/
  test_provider_eval.py
```

## Implementation Details

### A2A Task Manager (adopt from `taskManager.ts`)

```python
class A2ATaskManager:
    """Manages agent-to-agent task delegation through the gateway."""
    
    async def create_task(
        self,
        from_agent: str,
        intent: str,
        context: dict,
        required_capabilities: list[str] | None = None,
    ) -> Task:
        """Create a new task and route to capable agents."""
        
        task = Task(
            id=generate_id(),
            from_agent=from_agent,
            intent=intent,
            context=context,
            status="pending",
            created_at=datetime.utcnow(),
        )
        
        # Discover capable agents
        agents = await self.discovery.find_agents(
            capabilities=required_capabilities,
            intent=intent,
        )
        
        # Route to best agent(s)
        task.assignments = await self._route_to_agents(task, agents)
        
        # Start execution monitoring
        asyncio.create_task(self._monitor_task(task))
        
        return task
    
    async def _route_to_agents(self, task: Task, agents: list[Agent]) -> list[Assignment]:
        """Route task to the best agent(s) based on capability match and load."""
        assignments = []
        
        for agent in agents[:3]:  # Max 3 parallel agents
            match_score = self._score_capability_match(task.intent, agent.capabilities)
            if match_score > 0.7:  # 70% match threshold
                assignments.append(Assignment(
                    agent=agent.id,
                    task=task.id,
                    status="assigned",
                    match_score=match_score,
                ))
        
        return assignments
    
    async def get_task_progress(self, task_id: str) -> TaskProgress:
        """Get real-time progress for a task."""
        task = await self.store.get(task_id)
        return TaskProgress(
            task_id=task.id,
            status=task.status,
            assignments=[
                AssignmentProgress(
                    agent=a.agent,
                    status=a.status,
                    progress_pct=a.progress_pct,
                    current_step=a.current_step,
                )
                for a in task.assignments
            ],
            started_at=task.created_at,
            estimated_completion=task.estimated_completion,
        )
```

### Streaming Progress (adopt from `streaming.ts`)

```python
class TaskStreamer:
    """Streams real-time task progress to connected clients via WebSocket."""
    
    async def stream_task(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        
        async for event in self.task_manager.watch(task_id):
            await websocket.send_json({
                "type": event.type,        # "step_started", "step_completed", "finding", "error"
                "task_id": task_id,
                "agent": event.agent,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
            })
            
            if event.type == "task_completed":
                await websocket.send_json({
                    "type": "task_completed",
                    "task_id": task_id,
                    "result": event.result,
                    "duration_ms": event.duration_ms,
                })
                break
```

### Observability API

```python
# GET /api/observability/health
{
    "status": "healthy",
    "providers": [
        {"name": "kiro", "status": "ok", "success_rate": 0.992, "latency_ms": 1200},
        {"name": "qoder", "status": "ok", "success_rate": 0.987, "latency_ms": 900},
        {"name": "groq", "status": "down", "success_rate": 0.450, "latency_ms": 8200, "circuit": "open"},
    ],
    "combos": [
        {"name": "default", "tier1_hit_rate": 0.78, "avg_latency_ms": 1400, "tokens_saved_24h": 2100000},
    ],
    "uptime_seconds": 864000,
    "total_requests_24h": 14230,
    "compression_savings_24h": "47%",
}

# GET /api/observability/providers
# GET /api/observability/combos
# GET /api/observability/quota
# GET /api/observability/cost
# GET /api/observability/route-explain?request_id=abc123
```

### Route Explain

```python
# GET /api/observability/route-explain?request_id=abc123
{
    "request_id": "abc123",
    "combo": "default",
    "strategy": "auto/coding",
    "timeline": [
        {"step": 1, "action": "try", "provider": "kiro", "result": "quota_exhausted", "latency_ms": 450},
        {"step": 2, "action": "try", "provider": "qoder", "result": "success", "latency_ms": 750},
    ],
    "decision": "qoder selected (reason: kiro quota exhausted, qoder best remaining latency 900ms)",
    "compression": {"saved_tokens": 2150, "savings_pct": 42},
    "total_latency_ms": 3500,
}
```

### Provider Evals (adopt from `evals/`)

```python
class ProviderEvaluator:
    """Continuously evaluates provider quality for promotion/demotion decisions."""
    
    async def evaluate(self, provider: str) -> EvalResult:
        """Run standard benchmarks against provider and score quality."""
        
        benchmarks = [
            "code_generation",
            "reasoning",
            "tool_calling",
            "instruction_following",
            "latency_baseline",
        ]
        
        scores = {}
        for benchmark in benchmarks:
            result = await self.benchmark_runner.run(provider, benchmark)
            scores[benchmark] = result.score
        
        overall = sum(scores.values()) / len(scores)
        
        return EvalResult(
            provider=provider,
            overall_score=overall,
            benchmark_scores=scores,
            meets_quality_gate=overall >= self.quality_gates.min_score,
        )
```

## Safety; Non-Breaking

1. A2A protocol is opt-in; existing agent communication continues to work
2. Observability endpoints are read-only; no impact on request processing
3. Compliance audit is append-only; logs cannot be modified
4. Provider evals run on a schedule, not on every request; no latency impact
5. All features disabled by default; enable via `KEPRIX_OBSERVABILITY_ENABLED=true`

## Verification

- [ ] A2A task manager creates and routes tasks to capable agents
- [ ] Task progress streams in real-time via WebSocket
- [ ] Agent discovery matches intent to capabilities with >70% accuracy
- [ ] Observability dashboard API returns accurate provider health data
- [ ] Route explain shows complete timeline per request
- [ ] Provider evals run benchmarks and produce quality scores
- [ ] Quality gates prevent low-scoring providers from auto-promotion
- [ ] Compliance audit trail is complete and append-only
- [ ] Health endpoint returns correct status for all providers
- [ ] Alerts fire when provider health drops below threshold
- [ ] Combo forecast predicts cost and performance within 10% accuracy
- [ ] All endpoints work with observability disabled (return 404)
- [ ] Tests pass for all new modules
