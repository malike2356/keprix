# Evals and observability

Evals let you benchmark agent quality, compare providers, run regression tests, and export traces to external observability platforms. Observability tooling captures every tool call, LLM round-trip, and playbook event so you can diagnose failures and measure improvement.

## Overview

| Concept | What it is |
| --- | --- |
| **Benchmark suite** | A named set of eval tasks with expected outputs and graders |
| **Grader** | A function that scores an agent response (exact match, LLM judge, schema check, etc.) |
| **Trace** | A full record of a single agent run: messages, tool calls, timings, tokens |
| **Baseline** | A saved benchmark score snapshot to diff against |
| **Regression test** | Compares current scores to a baseline and fails if scores drop |

## Web UI (`/evals`)

The Evals page surfaces:

- **Benchmark suites**: list, run, view results, save baseline
- **Recent traces**: searchable run history with drill-down
- **Regression dashboard**: baseline vs current score comparison
- **RAG eval viewer**: precision/recall and NDCG metrics for retrieval quality

Link to run suites, view individual traces, and export results to JSON or CSV.

## Benchmark suites

Pre-built suites live under `evals/suites/`:

| Suite | What it tests |
| --- | --- |
| `research/` | Citation quality, factual accuracy, completeness |
| `coding/` | Code correctness, test pass rate, style compliance |
| `browser/` | Web task completion, form submission, data extraction |
| `analytics/` | Python analytics correctness, chart accuracy |
| `opportunity/` | Market research quality, TAM/SAM/SOM accuracy |
| `security-safe/` | Security tool outputs, no-false-positive rate |

Run a suite:

```bash
# All tasks in a suite
curl -X POST http://localhost:3333/api/evals/benchmarks/run \
  -H "Authorization: Bearer $KEPRIX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"suite": "coding"}'

# Single task
curl -X POST http://localhost:3333/api/evals/benchmarks/run/task/coding-001
```

Run via the UI: open **Evals**, select a suite, click **Run suite**.

## Graders

Keprix includes the following grader types:

| Grader | Use case |
| --- | --- |
| `exact_match` | Deterministic expected output |
| `json_schema` | Structured output shape check |
| `citations` | Verifies sources cited in research output |
| `safety` | Checks for harmful or policy-violating content |
| `tools_used` | Verifies specific tools were or were not called |
| `rubric` | Weighted criteria scored by a second LLM |
| `llm_judge` | Free-form quality assessment by a judge model |

Define custom graders in Python:

```python
from keprix.evals.graders import register_grader

@register_grader("contains_json_key")
def contains_json_key(response: str, expected_key: str) -> float:
    import json
    try:
        data = json.loads(response)
        return 1.0 if expected_key in data else 0.0
    except Exception:
        return 0.0
```

## Writing a custom benchmark task

```yaml
# evals/suites/my-suite/task-001.yml
id: my-suite-001
description: Agent lists open tasks
input:
  message: "What are my open tasks?"
graders:
  - type: tools_used
    tools: [list_tasks]
  - type: llm_judge
    criteria: "Response lists at least one task and is formatted as a list"
    judge_model: anthropic/claude-sonnet-4-6
    min_score: 0.8
```

## Traces

Every agent run generates a trace (unless disabled with `KEPRIX_TRACING_ENABLED=false`).

A trace contains:

- Input messages and output
- Each tool call: name, inputs, output, latency
- LLM calls: model, tokens in/out, latency
- Total cost estimate (if provider pricing is configured)
- Session and user metadata

### View traces

**Evals > Recent traces** shows a searchable, filterable list. Click a trace to drill into the full event tree.

### API

```http
GET /api/observability/traces?session_id=...&tool=...&date_from=...
GET /api/observability/traces/{trace_id}
GET /api/observability/dashboard
```

### Agent app traces

```http
GET /api/agent-apps/{name}/traces
```

## OpenTelemetry export

Configure an OTLP-compatible collector (Jaeger, Tempo, Honeycomb, Datadog):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_SERVICE_NAME=keprix
OTEL_TRACES_SAMPLER=always_on      # or parentbased_traceidratio
```

Traces are exported as OTLP spans. Tool calls map to child spans; the full agent turn is the root span.

## Scout export

When governance integration is active:

```bash
KEPRIX_GOVERNANCE_TRACE_EXPORT=true
```

Traces are forwarded to the Scout governance platform for audit, compliance, and policy evaluation. See [Scout integration](../integrations/scout.md).

## Baselines and regression

Save a baseline after a stable release:

```http
POST /api/evals/benchmarks/baseline
{"suite": "coding", "label": "v1.2-release"}
```

Run regression against the saved baseline:

```http
POST /api/evals/benchmarks/regression
{"suite": "coding", "baseline_label": "v1.2-release"}
```

The response reports score deltas per task and fails the request (HTTP 422) if any task drops below its baseline by more than the configured tolerance (`KEPRIX_EVAL_REGRESSION_TOLERANCE`, default `0.05`).

## Configuration

```bash
KEPRIX_TRACING_ENABLED=true
KEPRIX_EVAL_DEFAULT_JUDGE_MODEL=anthropic/claude-sonnet-4-6
KEPRIX_EVAL_REGRESSION_TOLERANCE=0.05
OTEL_EXPORTER_OTLP_ENDPOINT=         # leave blank to disable OTLP
KEPRIX_GOVERNANCE_TRACE_EXPORT=false
```

## Related

- [Compare models](compare-models.md)
- [Agent Studio](agent-studio.md)
- [Scout integration](../integrations/scout.md)
- [Playbooks](playbooks.md)
