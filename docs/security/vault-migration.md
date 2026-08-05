# Vault migration

Keprix keeps the old encrypted vault working for existing installs, but new credential work should use Cordon or the built-in credential proxy. The proxy model fetches real secrets from an external vault per request, so the agent process does not keep API keys in memory.

## Migrate

```bash
keprix proxy migrate-vault
keprix proxy migrate anthropic-api-key
keprix proxy verify
```

`migrate-vault` copies supported provider keys from `~/.keprix/.env` into the proxy local vault and creates proxy routes. It then writes dummy keys back to `.env` via the proxy env writer.

## Purge

After verifying all routes:

```bash
keprix proxy vault-purge --confirm
```

The command creates a timestamped backup before deleting the legacy local vault file.

## Emergency fallback

```bash
keprix proxy fallback enable
keprix proxy fallback status
keprix proxy fallback disable
```

Fallback is temporary and expires after 24 hours by default. `keprix status` shows a warning while fallback is active.

## Timeline

| Version | Behavior |
| --- | --- |
| v2.2 | Migration wizard available; old vault works with warnings |
| v2.3 | Old vault read-only for new credentials |
| v3.0 | Old vault removed after backup and migration |
