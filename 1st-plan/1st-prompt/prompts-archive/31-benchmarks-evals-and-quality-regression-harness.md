# keprix - Prompt 31: Benchmarks, Evals, And Quality Regression Harness

## Purpose

Build a benchmark and evaluation system so keprix can measure model quality, tool reliability, cost, latency, safety, research quality, and regression risk over time.

keprix should know when a change makes the agent worse.

## Scope

Implement:

- Benchmark definitions.
- Eval datasets.
- Golden task suites.
- Agent trajectory scoring.
- Tool success scoring.
- Research quality scoring.
- Safety regression checks.
- Cost regression checks.
- Latency regression checks.
- Provider comparison.
- Local model benchmark.
- Release gate reports.

## Output Paths

```text
keprix/backend/evals/
  __init__.py
  registry.py
  runner.py
  scorers.py
  datasets.py
  reports.py
  provider_compare.py
  safety.py
  cost.py
  latency.py

keprix/evals/
  golden_tasks/
  research/
  tools/
  safety/
  data_analysis/

keprix/ui/web/evals/
keprix/tests/evals/
```

## Eval Categories

Support:

- Chat helpfulness.
- Tool routing.
- Tool execution.
- Research source quality.
- Citation correctness.
- Data analysis correctness.
- Code generation correctness.
- Cyber safety gating.
- Localization quality.
- Voice transcription quality.
- Billing and entitlement correctness.
- UI contract consistency.

## Metrics

Track:

- Pass rate.
- Human review score.
- Cost per task.
- Latency.
- Token usage.
- Tool failure rate.
- Retry rate.
- Safety block correctness.
- Citation validity.
- Regression compared with prior release.

## Tests

Add tests for:

- Eval runner executes golden tasks.
- Failed task records reason.
- Provider comparison produces ranking.
- Cost regression is detected.
- Safety eval blocks unsafe task.
- Release gate fails when score drops below threshold.

## Acceptance Criteria

- keprix has repeatable benchmarks.
- Model and provider changes can be evaluated.
- Tool regressions are visible.
- Research quality can be scored.
- Release gates prevent obvious quality drops.
