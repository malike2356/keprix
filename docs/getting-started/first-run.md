# First run

After [Install](install.md) (CLI / TUI) or [Quickstart Option B](quickstart.md) (Docker).

## 1. LLM key

Set at least one of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`:

- **Docker:** put the key in `.env` (copy from `.env.example`) before or after `docker compose ... up`
- **CLI:** enter a provider key during `keprix setup`, or set the same variables in the environment used by the API process

Leave unused provider keys empty. Do not paste real secrets into docs or tickets.

## 2. Admin / setup

**CLI (preferred):**

```bash
keprix setup
```

That wizard creates the admin account, confirms the LLM provider, and can configure optional channels. Fallback if the console entry is unavailable: `python3 -m keprix.keprix_cli.main setup`, or `python3 scripts/wizard.py` from a full checkout.

**Docker UI:** open `http://localhost:3000` and complete the wizard (instance name, admin password, provider, optional Telegram / Discord). After **Finish setup**, use **Chat** in the sidebar.

API endpoint when enabled: `POST /api/setup/wizard`. Status: `GET /api/setup/status` (shared with the web onboarding checklist).

## 3. Open the product

**TUI:**

```bash
keprix tui
```

If the API is not already running:

```bash
keprix start --host 127.0.0.1 --port 3333
keprix tui
```

Use `keprix tui --help` for session resume, model override, API URL, bearer token, and mouse capture. The TUI can show a minimal provider form when unconfigured; use `/setup` or `/setup model` for the full CLI wizard.

**Web UI:** after Compose is up, open `http://localhost:3000`. After sign-in, the workspace is at `/workspace`.

## 4. Optional Telegram / Discord

Configure channels in `keprix setup`, the Docker wizard, or `.env` (see `.env.example`). Details: [Messaging](../features/messaging.md).

## Verify

```bash
curl -s http://127.0.0.1:3333/api/health
```

Expect JSON with a status field when the API is up. From a checkout you can also run:

```bash
bash scripts/check-health.sh
```

## Developer identity (optional)

If you are the machine owner and want local developer mode:

```bash
keprix init
```

This is secondary to normal setup. See [Developer identity](../configuration/developer-identity.md).

## Related

- [Install](install.md)
- [Quickstart](quickstart.md)
- [Manual install (for developers)](manual-install.md)
