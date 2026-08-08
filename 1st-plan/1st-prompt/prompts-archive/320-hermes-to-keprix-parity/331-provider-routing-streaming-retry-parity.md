# Keprix Prompt 331: Provider Routing Streaming and Retry Parity

## Purpose

Match Hermes behavior for model providers, routing, streaming, retries, fallback, rate limits, and cost accounting while preserving Keprix BYOK, billing gates, usage analytics, and Scout governance.

## Preconditions

Complete Prompt 327 inventory first.

## Tasks

1. Compare provider abstractions:
   - provider selection
   - model aliases
   - fallback chains
   - streaming delta handling
   - thinking blocks
   - tool call parsing
   - retry conditions
   - rate limit handling
   - usage accounting
2. Port Hermes behavior where Keprix is weaker.
3. Preserve Keprix extensions:
   - BYOK enforcement
   - mini LLM fallback policy
   - subscription gates
   - usage dashboard data
   - Scout policy signals
4. Add tests with fake providers for:
   - stream success
   - stream interruption
   - malformed tool call
   - retry then success
   - fallback provider
   - rate limited provider
   - usage counted once

## Acceptance criteria

- Provider routing is deterministic.
- Streaming does not duplicate or lose deltas.
- Retry behavior matches Hermes unless Keprix deliberately improves it.
- Billing and BYOK gates still apply at the correct boundary.

## Verification

```bash
python -m pytest tests/agent tests/providers tests/billing tests/api -q
python -m pytest tests/architecture -q
```
