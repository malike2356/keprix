# First run

After [Quickstart](quickstart.md), the web UI guides first-time setup.

## Wizard steps

1. **Instance name** and public URL (used in emails and Scout enrollment)
2. **Admin account** with password (shown once; store securely)
3. **LLM provider** selection and API key
4. **Optional channels** (Telegram, Discord) if configured in `.env`

CLI alternative:

```bash
python3 -m keprix.keprix_cli.main setup
```

API endpoint (when enabled): `POST /api/setup/wizard`

## Developer identity

If you are the machine owner, run:

```bash
keprix init
```

This enables developer mode locally. See [Developer identity](../configuration/developer-identity.md).

## Verify

```bash
curl -s http://127.0.0.1:3333/api/health
bash scripts/check-health.sh
```

Open the workspace at `/workspace` after signing in.

## TUI path (skipped CLI setup)

If you launch chat before running the full wizard:

```bash
keprix start
keprix tui
# or: keprix --tui   (opens Textual TUI in setup mode when unconfigured)
```

The TUI shows a minimal provider form. Use `/setup` or `/setup model` for the full CLI wizard.

Status API: `GET /api/setup/status` (shared with the web onboarding checklist).
