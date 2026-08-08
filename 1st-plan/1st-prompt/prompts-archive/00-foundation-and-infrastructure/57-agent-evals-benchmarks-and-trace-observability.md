# keprix - Prompt 57: Agent Evals, Benchmarks, and Trace Observability

## Context

Adopt evaluation and observability ideas from AutoGen Bench, CrewAI tracing, LangGraph execution traces, SWE-agent benchmark runs, and TaskWeaver transparent logs.

keprix needs measurable quality. Every important agent workflow should produce traces, metrics, eval results, and failure reports.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/evals/
  __init__.py
  benchmark.py
  datasets.py
  graders.py
  trace.py
  metrics.py
  reports.py
  regression.py
backend/observability/
  agent_trace.py
  otel.py
  cost_meter.py
  token_meter.py
tests/evals/test_benchmark_runner.py
tests/evals/test_graders.py
tests/observability/test_agent_trace.py
```

## Trace Model

Every run should capture:

- Run ID.
- Workspace ID.
- User request.
- Agent roles.
- Playbook graph.
- Node transitions.
- Tool calls.
- Model calls.
- Tokens.
- Cost estimate.
- Artifacts.
- Approvals.
- Errors.
- Final outcome.

Redact secrets and sensitive data before persistence.

## Benchmark Suites

Add local benchmark suites:

```text
evals/suites/
  research/
  coding/
  browser/
  analytics/
  opportunity/
  security-safe/
```

Each suite has:

- Task input.
- Expected artifacts.
- Grading rubric.
- Required citations.
- Safety expectations.
- Max cost.
- Max runtime.

## Graders

Implement graders:

- Exact match.
- JSON schema match.
- Citation coverage.
- Artifact completeness.
- Safety violation.
- Tool success.
- Human rubric.
- LLM judge with strict prompt.

LLM judge must never be the only grading method for safety-critical tests.

## Reports

Generate:

- Markdown report.
- JSON report.
- Trend history.
- Failure summary.

## Observability

Support:

- Local trace viewer API.
- OpenTelemetry export if configured.
- Scout bridge event export if configured.
- Cost and token dashboard data.

## Acceptance Criteria

- Benchmarks run locally without external services by default.
- Traces are redacted.
- Reports show pass/fail, cost, runtime, and safety warnings.
- Regression runner can compare current run to previous baseline.
- Opportunity Engine, browser, analytics, and coding workflows have starter eval suites.
- Tests cover graders, redaction, report generation, and baseline comparison.

