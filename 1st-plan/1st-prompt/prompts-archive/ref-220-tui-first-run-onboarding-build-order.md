# TUI first-run onboarding build order

Reference for prompts **220-222**. Architecture reference:
`prompts-archive/ref-220-tui-first-run-onboarding-architecture-reference.md`.

## Sequence

```text
220 Setup status API + shared provider probe
221 TUI Setup Required panel + /setup handoff + CLI TUI gate tweak
222 First-message profile build + onboarding hints on TUI path
```

## Prompt summary

| # | Title | Delivers |
| --- | --- | --- |
| 220 | Setup status API | `GET /api/setup/status`, `keprix/setup/status.py`, tests |
| 221 | TUI setup handoff | Setup Required panel, `/setup`, subprocess handoff, docs |
| 222 | TUI first-message onboarding | `profile_build_directive` on conversation POST, hint wiring |

## Dependencies

| Prompt | Requires |
| --- | --- |
| 220 | Existing `_has_any_provider_configured`, `list_available_models` |
| 221 | 220, Textual TUI (`src/keprix/tui/`), `keprix setup` subprocess |
| 222 | 221 (TUI can send messages), `agent/onboarding.py`, gateway parity |

## Parallel work

- 220 can ship without TUI changes.
- Web UI may consume `/api/setup/status` later; not required for 221 AC.
