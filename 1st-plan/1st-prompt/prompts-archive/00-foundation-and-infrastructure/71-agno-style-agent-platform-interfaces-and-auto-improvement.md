# keprix - Prompt 71: Agno-Style Agent Platform Interfaces and Auto-Improvement

## Context

Adopt Agno's useful platform concepts: agent interfaces across channels, A2A and AG-UI exposure, team agents, knowledge tools, reasoning tools, monitoring, and auto-improvement loops.

This extends Prompts 11, 15, 39, 65, 70, and 71.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/agno/README.md
planning/agents-to-adopt/agno/libs
```

## Files To Create Or Extend

```text
backend/interfaces/
  __init__.py
  interface_registry.py
  slack_interface.py
  telegram_interface.py
  whatsapp_interface.py
  discord_interface.py
  ag_ui_adapter.py
  a2a_interface.py
backend/improvement/
  __init__.py
  feedback_collector.py
  run_analyzer.py
  prompt_improver.py
  tool_gap_detector.py
  eval_backfill.py
tests/interfaces/test_interface_registry.py
tests/interfaces/test_ag_ui_adapter.py
tests/improvement/test_tool_gap_detector.py
tests/improvement/test_prompt_improver.py
```

## Required Features

### Interface Registry

Expose agents through:

- Web UI.
- Slack.
- Telegram.
- WhatsApp.
- Discord.
- API.
- A2A.
- AG-UI.

Reuse Prompt 13 channel adapters. Do not build a second messaging gateway.

### Auto-Improvement Loop

Analyze completed runs for:

- Repeated failures.
- Missing tools.
- Slow steps.
- High cost.
- User corrections.
- Low eval score.

Then propose:

- Prompt improvements.
- Tool improvements.
- Playbook changes.
- New eval cases.

All changes require human approval before becoming active.

### Monitoring

Expose:

- Run success rate.
- Tool failure rate.
- User satisfaction.
- Cost by agent.
- Latency by tool.
- Improvement proposals.

## Acceptance Criteria

- One agent can be exposed through web UI and one channel adapter.
- A completed failed run creates an improvement proposal.
- Improvement proposals can become eval cases.
- A2A and AG-UI adapters use shared auth and tracing.
- No Agno branding appears in keprix UI.

