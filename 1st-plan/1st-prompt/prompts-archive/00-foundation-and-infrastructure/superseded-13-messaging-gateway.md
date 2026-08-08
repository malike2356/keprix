# keprix - Prompt 13: Messaging Gateway and Channel Adapters

## Context

Sources:
- `hermes-agent/gateway/` - gateway runner, platform adapters, built-in hooks
- `hermes-agent/gateway/platforms/` - 20+ platform adapters
- `openclaw/src/` - OpenClaw's channel infrastructure (TypeScript)
- `openclaw/extensions/` - OpenClaw channel extensions
- `core.carinaai.uk/src/gateway/` - Aiva (commercial) channel adapters (18 adapters)
Output: `keprix/backend/gateway/`

## Gateway Core Port (from Hermes)

Port the gateway runner and infrastructure verbatim:
```
gateway/                 -> backend/gateway/
  run.py (or equivalent) -> backend/gateway/run.py
  builtin_hooks/         -> backend/gateway/builtin_hooks/
  assets/                -> backend/gateway/assets/
  platforms/             -> backend/gateway/platforms/
tui_gateway/             -> backend/tui_gateway/
```

Apply standard Hermes -> keprix renames.

## Messaging Channels (Target: 20+)

The following channels must work. Source preference shown in brackets.
For any channel in both Hermes and OpenClaw, take Hermes (already Python);
use OpenClaw as a feature reference to check for anything Hermes is missing.

### Primary Channels (must ship in v1.0)

1. **Telegram** [Hermes `gateway/platforms/telegram`]
   - Bot API long polling + webhook mode
   - Photo, voice, document, sticker handling
   - Inline keyboard buttons
   - Port `scripts/whatsapp-bridge/` for Telegram WABA bridge if present

2. **Discord** [Hermes + OpenClaw reference]
   - Bot token + slash commands
   - Thread support
   - Voice channel transcription (STT)
   - Port OpenClaw `extensions/discord/` for any features not in Hermes

3. **Slack** [Hermes `gateway/platforms/slack`]
   - Socket mode + Events API
   - Slash commands, shortcuts
   - Block Kit message formatting

4. **WhatsApp** [Hermes `scripts/whatsapp-bridge/`]
   - Baileys bridge (self-hosted, no official API required)
   - Media: image, audio, video, document
   - Group and DM support

5. **Signal** [Hermes `gateway/platforms/`]
   - signal-cli bridge
   - Group support

6. **iMessage** [OpenClaw `extensions/imessage/` if present, else stub]
   - macOS only via AppleScript bridge
   - Mark as macOS-only in config

7. **Google Chat** [Hermes `gateway/platforms/google_chat`]
   - Cloud Pub/Sub pull subscription
   - Space and DM support

8. **Microsoft Teams** [Hermes `gateway/platforms/teams` + `plugins/teams_pipeline/`]
   - Bot Framework
   - Azure AD auth

9. **IRC** [Hermes `gateway/platforms/irc` if present]
   - IRC client (nick, channels, private messages)

10. **Matrix** [Hermes `gateway/platforms/matrix`]
    - matrix-nio client
    - E2E encryption support

11. **Email (IMAP/SMTP)** [Hermes `optional-skills/email/` + Odysseus `routes/email_routes.py`]
    - Receives messages via IMAP polling
    - Sends replies via SMTP
    - Full email integration detailed in Prompt 11

### Additional Channels (build after primary channel scaffolding)

12. **Feishu / Lark** [Hermes `gateway/platforms/feishu`]
13. **LINE** [OpenClaw `extensions/line/` reference]
14. **Mattermost** [OpenClaw reference]
15. **Nextcloud Talk** [OpenClaw reference]
16. **Nostr** [OpenClaw reference - decentralized]
17. **Synology Chat** [OpenClaw reference]
18. **Twitch** [OpenClaw reference]
19. **Zalo / Zalo Personal** [OpenClaw reference]
20. **WeChat** [OpenClaw reference]
21. **QQ** [OpenClaw reference]
22. **WebChat** [Hermes web dashboard chat]

For each additional channel, create `backend/gateway/platforms/{channel}/` with
the adapter, setup validator, credential requirements, tests, and a user-friendly
setup message. If a provider requires credentials that are not present, the
adapter must fail closed with a clear configuration error.

## Gateway Web Dashboard

From Hermes `web/` and `web/src/`:
```
web/                  -> backend/web/
web/public/           -> backend/web/public/
web/src/              -> backend/web/src/
```

This is the Hermes built-in web UI for the gateway (separate from the main
Next.js frontend). Keep it as-is but rename "Hermes" to "keprix" in all
HTML/JS strings.

## Built-in Hooks System

Port `gateway/builtin_hooks/` verbatim. Hooks fire on message events and let
skills intercept messages before they reach the agent. Rename `hermes_*` to
`keprix_*` in hook identifiers.

## Session Reset Policy

From Hermes config, the gateway supports:
- `session_reset: none` - sessions persist indefinitely
- `session_reset: daily` - reset at configurable daily time
- `session_reset: idle` - reset after N minutes of inactivity

All three modes must be supported. Config in `config.yaml` under `gateway.session_reset`.

## Multi-User Gateway

The gateway must support multiple users per channel:
- Each Telegram user ID = separate conversation context
- Configurable allowlist (`TELEGRAM_ALLOWED_USERS`, etc.) from `.env`
- `GATEWAY_ALLOW_ALL_USERS=true` to open access (default: false)
- Per-user memory isolation (all memory queries scoped by user_id)

## Human-like Delay Mode

Port Hermes human delay feature:
- `keprix_HUMAN_DELAY_MODE=off|natural|custom`
- `natural` mode: chunk output with typing simulation
- `custom` mode: use `keprix_HUMAN_DELAY_MIN_MS` and `MAX_MS`

## Gateway State Persistence

Port from `hermes-agent/hermes_state.py` (now `backend/agent/state.py`):
- Gateway state is written to `~/.keprix/gateway_state.json`
- Includes: active channels, session map, PID
- Read on startup for recovery

## Process Management

Port from Hermes:
- `gateway.pid` file written to `~/.keprix/`
- `python -m keprix gateway start` - start in background
- `python -m keprix gateway stop` - graceful stop
- `python -m keprix gateway status` - show running channels and uptime
- `python -m keprix gateway restart` - stop + start

## TUI Gateway

Port `hermes-agent/tui_gateway/` verbatim to `keprix/backend/tui_gateway/`.
This provides a terminal UI for monitoring gateway activity in real time.

## OpenClaw Canvas Feature

OpenClaw has a "Canvas" live rendering UI (mentioned in README). Implement this
in `backend/gateway/canvas/` as a real-time rendered surface the agent can write
structured content to, visible in the Keprix mobile and desktop app.

## Acceptance Criteria

- `python -m keprix gateway start` starts without error when TELEGRAM_BOT_TOKEN is set
- `python -m keprix gateway status` prints channel list and PIDs
- Telegram: sending "hello" to the bot results in a response within 5 seconds
- Discord: slash command `/carina hello` receives a response
- `python -m keprix gateway stop` terminates cleanly (exit 0)

## Slash Command Follow-Up

Build the shared slash-command registry, built-in commands, permissions, confirmations, and audit log in Prompt 23. This gateway prompt only wires channel transport.
- Each primary channel adapter has a `test_connect()` method that validates credentials
- 12 primary channel stubs import without error even when not configured
