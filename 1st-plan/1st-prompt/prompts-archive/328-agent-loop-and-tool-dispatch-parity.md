# Keprix Prompt 328: Agent Loop and Tool Dispatch Parity

## Purpose

Bring Keprix core agent loop and tool dispatch behavior to Hermes parity while preserving Keprix tool policy, Scout signals, Channel Shield guards, and Agent OS hooks.

## Preconditions

Complete Prompt 327 inventory first.

## Tasks

1. Compare Hermes agent loop implementation with Keprix:
   - turn lifecycle
   - max turn handling
   - tool call batching
   - tool result normalization
   - final response handling
   - interruption handling
   - background review or subagent behavior
2. Compare tool dispatch:
   - schema normalization
   - tool names and aliases
   - tool result formatting
   - tool error handling
   - permission checks
   - audit logging
3. Port missing Hermes behavior into core only where it improves stability.
4. Preserve Keprix extensions through hooks:
   - Scout telemetry
   - Channel Shield safe content
   - product ACL
   - Agent OS run ledger
   - mutation hooks
5. Add or update tests for parity cases.

## Design rule

The agent loop should call generic hook points, not import product modules directly.

Good:

```python
product_hooks.before_tool_call(...)
product_hooks.after_turn(...)
```

Bad:

```python
from keprix.channel_shield import ...
```

## Acceptance criteria

- Hermes loop behavior is matched or explicitly marked Keprix-better.
- Keprix product hooks still fire.
- Tool dispatch tests cover success, failure, retry, blocked tool, and malformed tool call.
- Core product import boundary tests pass.

## Verification

```bash
python -m pytest tests/agent tests/tools tests/security -q
python -m pytest tests/architecture -q
python -m pytest tests/channel_shield tests/agent_os -q
```
