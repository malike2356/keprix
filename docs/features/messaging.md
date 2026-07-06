# Messaging channels

Keprix connects to chat platforms so you can interact with your agent without opening the web UI. Each channel delivers messages to the same agent runtime: same tools, same memory, same mutation engine.

## Supported channels

| Channel | Transport | Status |
| --- | --- | --- |
| Telegram | Bot API + webhook | Supported |
| Discord | Bot gateway | Supported |
| WhatsApp | WhatsApp Business API | Supported |
| Slack | Socket Mode / Events API | Supported |
| Matrix | Client-Server API | Supported |
| Signal | Signal CLI gateway | Supported |
| REST API | HTTP | Always available |
| Web UI | WebSocket | Always available |

## Architecture

All channels share a single **gateway subsystem**. Each channel adapter normalises incoming messages into a standard format and dispatches them to the agent runtime. Replies are formatted back into the channel's native format.

```
Telegram message -> TelegramAdapter -> Gateway -> Agent runtime -> reply -> TelegramAdapter -> Telegram
```

The gateway tracks channel sessions mapped to workspace user accounts. Each incoming chat ID is bound to a user on first contact.

## Gateway status

```bash
python3 -m keprix.keprix_cli.main status
```

Or in the web UI: **Admin > Settings > Messaging**.

## Telegram

### Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Add to `.env`:

```bash
TELEGRAM_BOT_TOKEN=7123456789:AAF...
TELEGRAM_WEBHOOK_URL=https://your-domain.com/api/gateway/telegram/webhook
```

For local development without a public URL, use polling mode:

```bash
TELEGRAM_USE_POLLING=true
```

3. Restart the backend. The bot goes online automatically.

### Usage

Send any message to your bot. The agent replies in the same thread. Mutation approval requests arrive as formatted messages with inline Accept/Reject buttons.

### CLI

```bash
python3 -m keprix.keprix_cli.main gateway telegram
```

## Discord

### Setup

1. Create an application and bot at [discord.com/developers](https://discord.com/developers/applications).
2. Enable **Message Content Intent** under Bot > Privileged Gateway Intents.
3. Invite the bot to your server with `bot` and `applications.commands` scopes.
4. Add to `.env`:

```bash
DISCORD_BOT_TOKEN=MTI...
DISCORD_APPLICATION_ID=1234567890
DISCORD_GUILD_ID=9876543210     # optional: restrict to one server
```

5. Restart the backend.

### Usage

Mention the bot or DM it directly. Slash commands are registered automatically on startup.

### CLI

```bash
python3 -m keprix.keprix_cli.main gateway discord
```

## WhatsApp

### Setup

Keprix uses the WhatsApp Business API (cloud or on-premise). You need a Meta Business account with an approved phone number.

```bash
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_ACCESS_TOKEN=EAAa...
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your-random-string
```

Point the Meta webhook to `https://your-domain.com/api/gateway/whatsapp/webhook`.

### CLI

```bash
python3 -m keprix.keprix_cli.main whatsapp
```

## Slack

### Setup

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps).
2. Enable **Socket Mode** for local deployments or configure **Event Subscriptions** for webhooks.
3. Add OAuth scopes: `chat:write`, `channels:read`, `app_mentions:read`, `im:read`, `im:write`.
4. Add to `.env`:

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...          # for Socket Mode
SLACK_SIGNING_SECRET=abc123...
```

### CLI

```bash
python3 -m keprix.keprix_cli.main slack
```

## Matrix

```bash
MATRIX_HOMESERVER_URL=https://matrix.example.com
MATRIX_ACCESS_TOKEN=syt_...
MATRIX_BOT_USER_ID=@keprix:example.com
```

### CLI

```bash
python3 -m keprix.keprix_cli.main matrix
```

## Signal

Signal CLI must be installed and registered to a phone number on the host.

```bash
SIGNAL_CLI_PATH=/usr/local/bin/signal-cli
SIGNAL_PHONE_NUMBER=+447700900123
```

### CLI

```bash
python3 -m keprix.keprix_cli.main signal
```

## User binding

The first message from a chat ID that cannot be matched to a workspace user triggers a binding prompt. The user must either reply with a one-time code shown in the web UI or an admin must bind the account manually via **Admin > Users**.

```http
POST /api/gateway/bind
{
  "channel": "telegram",
  "chat_id": "123456",
  "user_id": "workspace-user-uuid"
}
```

## Sending notifications out

Channels are not only for inbound messages. Keprix can push notifications through any connected channel:

- Mutation approval requests
- Cron job failure alerts
- Research completion notices
- Custom playbook steps

Configure notification targets in **Settings > Notifications > External**.

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| Gateway status | GET | `/api/gateway/status` |
| List connected channels | GET | `/api/gateway/channels` |
| Send test message | POST | `/api/gateway/test` |
| Bind user to channel | POST | `/api/gateway/bind` |
| List bindings | GET | `/api/gateway/bindings` |

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Bot does not respond | Token wrong or webhook unreachable | Check env vars; verify webhook URL is public and HTTPS |
| Messages duplicate | Webhook registered twice | Delete old webhook registration from provider dashboard |
| Agent replies go missing | Message too long for channel | Keprix auto-splits; check `KEPRIX_MSG_MAX_LENGTH` |
| Wrong user gets replies | Multiple users share a chat ID | Check bindings in Admin > Users |

## Related

- [Notifications](notifications.md)
- [Agent runtime](agent.md)
- [Review gateway](../security/review-gateway.md)
- [Cron jobs](cron-jobs.md)
