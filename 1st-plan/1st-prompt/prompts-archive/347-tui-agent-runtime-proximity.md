# Keprix Prompt 347: TUI Agent Runtime Proximity

## Goal

Make Keprix TUI closer to the agent runtime than the current HTTP-first boundary while preserving clean architecture and Keprix look and feel. The target is Hermes-level immediacy: streaming, tools, subagents, interrupts, queue, steer, session state, and model routing should feel live and native.

Do not collapse product modules into TUI. Use a narrow-waist runtime interface that can run in-process when available and fall back to HTTP or WebSocket when not.

## Required architecture

Create a runtime transport abstraction:

```text
src/keprix/tui/runtime_transport/
  __init__.py
  base.py
  in_process.py
  http.py
  websocket.py
  selector.py
  events.py
  errors.py
```

Transport modes:

- `in_process`: direct agent runtime adapter when TUI is launched in an environment where the agent runtime can be imported safely.
- `websocket`: persistent live event stream when gateway is available.
- `http`: current compatibility path.

Selection order:

1. Explicit config/env override
2. In-process if safe and available
3. WebSocket if available
4. HTTP fallback

## Runtime contract

All transports must expose the same interface:

```text
health()
ensure_ready_session()
list_sessions()
create_session()
get_messages()
list_models()
send_message_stream()
interrupt()
steer()
command_complete()
command_dispatch()
list_skills()
list_plugins()
get_tui_config()
```

Streaming events must be normalized to one typed event stream:

```text
text_delta
tool_call
tool_call_update
subagent_spawn
subagent_update
subagent_done
activity
clarify
approval
approval_resolved
message_done
error
heartbeat
runtime_status
```

## In-process safety

In-process mode must be safe:

- No import-time side effects that start servers.
- No product module imports from TUI core.
- Runtime adapter lives at a boundary where importing agent runtime is allowed.
- If import fails, fallback silently to WebSocket/HTTP.
- In-process mode must not mutate system prompt mid-conversation.
- Interrupt and queue semantics must match HTTP mode.

## Runtime immediacy

Improve:

- Tool event latency
- Subagent event latency
- Interrupt speed
- Queue updates
- Busy state updates
- Session switch updates
- Model switch feedback
- Error propagation

## Tests required

Add:

```text
tests/tui/test_runtime_transport_contract.py
tests/tui/test_runtime_transport_selector.py
tests/tui/test_runtime_transport_http.py
tests/tui/test_runtime_transport_websocket.py
tests/tui/test_runtime_transport_in_process.py
tests/tui/test_runtime_event_normalization.py
tests/tui/test_runtime_interrupt_latency.py
```

Use fakes and contract tests. Do not require a real provider key.

## Acceptance criteria

- TUI app talks to a transport interface, not directly to one HTTP client shape.
- HTTP behavior remains compatible.
- WebSocket transport normalizes gateway events.
- In-process transport exists and safely falls back when unavailable.
- Transport selector is tested.
- Interrupt, queue, steer, sessions, commands, models, skills, plugins, and config are covered by transport contract tests.
- Existing TUI tests pass.
- `bash scripts/check-tui-parity.sh` passes.

## Verification commands

```bash
python -m pytest tests/tui/test_runtime_transport_contract.py -q
python -m pytest tests/tui/test_runtime_event_normalization.py -q
python -m pytest tests/tui -q
bash scripts/check-tui-parity.sh
```

