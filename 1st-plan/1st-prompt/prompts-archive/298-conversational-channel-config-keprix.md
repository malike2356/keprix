# Conversational channel configuration (Keprix Wave 1)

**Status:** Wave 1 complete on Keprix; Carina port complete 2026-07-11
**Source:** adapted from `carina/01-devends/prompts-library/archived/core-carina--conversational-config.md`
**Product rule:** anything configurable must also be configurable by talk/text; Wave 1 = channels/mail.

## Shipped

| Piece | Path |
|-------|------|
| Requirements registry | `src/keprix/channels/channel_requirements.py` |
| Encrypted store + `.env` upsert | `src/keprix/channels/channel_config_store.py` |
| Probes (all Wave 1 channels) | `src/keprix/channels/channel_probes.py` |
| Collect session (BotFather) | `src/keprix/channels/channel_setup_session.py` |
| Activation / env reload | `src/keprix/channels/channel_activation.py` |
| Service | `src/keprix/channels/channel_config_service.py` |
| Internal API | `/api/internal/channels` (+ `/collect`, `/test`) |
| Agent tool | `channel_config` (`list\|requirements\|collect\|configure\|test\|remove`) in core toolsets |
| Skills | `configure-channel`, `list-channels` |
| Voice scrub | `sensitive_scrub.py` + `voice/pipeline.py` |
| Dashboard sync | admin overview reads the store |

## Carina port

Carina uses `channel_config` + unified `configure` + Cloud `/api/channels/overview` merge.
Canonical archive: `carina/01-devends/prompts-library/archived/core-carina--conversational-config.md`.

## Validation

```bash
cd keprix
PYTHONPATH=src .venv/bin/python -m pytest tests/channels/ -q
```

## Remaining (not blocking try-in-chat)

- True adapter hot-start without gateway restart (reload marker + dotenv reload ship; restart/`/platform resume` still needed when gateway is already up)
- Dashboard deep forms still Telegram/Discord/REST; other channels use conversational path + overview status

## Operator flow

1. `channel_config` action `collect` channel_id=telegram → asks bot_token only
2. User answers → `collect` with that field → save + test; secret never echoed
3. Email/SMTP via collect one field at a time
4. `list` matches store / overview
