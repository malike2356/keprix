# First run

After [Install](install.md) (CLI) or [Quickstart Option B](quickstart.md) (Docker).

## CLI (the default)

Reload your shell, then:

```bash
keprix
```

If no provider key is configured, Keprix offers setup in that same terminal. Paste one BYOK key (any provider in the list), or skip and add one later with `keprix setup`. After a key is saved, `keprix` continues into chat.

There is no website account for the local agent. `keprix dashboard` is optional and is not required to talk to Keprix.

## Docker UI (optional)

Compose is the full web stack. Open `http://localhost:3000` and complete the wizard (instance name, admin password, provider). After **Finish setup**, use **Chat** in the sidebar.

API endpoint when enabled: `POST /api/setup/wizard`. Status: `GET /api/setup/status`.

## Optional Telegram / Discord

Configure channels in `keprix setup gateway`, the Docker wizard, or `.env` (see `.env.example`). Details: [Messaging](../features/messaging.md).

## Verify (when the API is running)

```bash
curl -s http://127.0.0.1:3333/api/health
```

Expect JSON with a status field. From a checkout you can also run:

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
