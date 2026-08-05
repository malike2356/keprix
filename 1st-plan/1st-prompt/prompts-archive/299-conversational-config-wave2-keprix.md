# Conversational configuration Wave 2 (Keprix)

**Status:** Wave 2 complete on Keprix (a/b/c); Carina port complete 2026-07-11
**Depends on:** Wave 1 channels (`298-conversational-channel-config-keprix.md`)

## Domains

| Domain | Tool | Status |
|--------|------|--------|
| Provider BYOK + default model | `provider_config` | done |
| Scout pair / unpair | `scout_config` | done |
| Integrations (Notion, Trello, GWS/calendar, webhooks) | `integration_config` | done |
| Workspace prefs (durable JSON) | `workspace_config` | done |
| Companion / device pairing | `companion_config` | done |

## Durable workspace prefs

`~/.keprix/workspace_settings.json` (also backs `GET/PUT /api/settings`).

## Carina port

Carina unified `configure` covers the same domains via settings registry:
providers, workspace, scout, Notion, Trello, CalDAV, Resend, Google Workspace OAuth,
outbound webhooks, companion pairing. Archive:
`carina/01-devends/prompts-library/archived/core-carina--conversational-config.md`.

## Validation

```bash
cd keprix
PYTHONPATH=src .venv/bin/python -m pytest tests/configure/ tests/channels/ -q
```

## Product rule

Same BotFather rules. Dashboard is a status mirror, not the only door.
