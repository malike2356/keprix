# Keprix Hermes Agent Parity Build Order

## Purpose

Reach full agent parity with Hermes without destroying Keprix extensions. This pack compares Hermes agent runtime behavior against Keprix, ports missing core behavior, and protects Keprix product capabilities through adapter boundaries and regression tests.

## Dependency

Run after or alongside the 317-326 core alignment pack. Do not begin invasive parity edits until boundary tests from Prompt 318 exist.

## Reference

Hermes reference tree:

```text
1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/
```

Keprix implementation:

```text
src/keprix/
```

## Prompt order

1. `327-hermes-agent-runtime-parity-inventory.md`
2. `328-agent-loop-and-tool-dispatch-parity.md`
3. `329-prompt-assembly-and-context-parity.md`
4. `330-sessions-memory-checkpoints-parity.md`
5. `331-provider-routing-streaming-retry-parity.md`
6. `332-file-terminal-approval-safety-parity.md`
7. `333-skills-plugins-mcp-parity.md`
8. `334-agent-parity-eval-suite.md`
9. `335-agent-parity-hardening-and-report.md`

## Principle

Hermes parity means Keprix keeps the same or better core agent behavior while preserving Keprix additions such as Agent OS, Channel Shield, billing, Scout, product packs, app builder, security policy, and admin APIs.

Do not remove Keprix features to match Hermes. When Hermes is cleaner, port the behavior into Keprix core and keep Keprix extensions behind adapters, feature flags, registries, or product modules.

## Definition of done

- Keprix can pass a parity matrix for core agent behavior.
- Keprix product extensions still pass their existing tests.
- No product module is imported directly by core runtime loops.
- Remaining non-parity decisions are documented as deliberate Keprix improvements.

## Global verification

```bash
python -m pytest tests/tui -q
python -m pytest tests/agent tests/tools tests/memory tests/cli -q
python -m pytest tests/channel_shield tests/agent_os tests/security -q
python -m pytest tests/architecture -q
```

Run full suite when feasible:

```bash
python -m pytest -q
```
