# keprix - Prompt: Vault Deprecation and Migration to External Secrets

## Purpose

keprix currently stores API keys and credentials in an encrypted vault (`security/vault_store.py`) using Fernet encryption. While this is more secure than plaintext .env files, it still means:

- Credentials are decrypted into agent process memory at startup.
- The vault encryption key is a single point of failure.
- Compromise of the agent process means compromise of all credentials.
- Credential rotation requires a keprix restart.

Prompt 239 (Credential Injection Proxy) and the Cordon integration (Prompt 242) move credential management to external vaults (1Password, Bitwarden, OS keychain) with per-request injection. This prompt handles the migration from the old vault to the new model.

The existing vault is preserved but deprecated. Existing users are guided through migration. New installs never create the old vault.

## Prerequisites

- Prompt 239 (Credential Injection Proxy) or Prompt 242 (Cordon Integration)
- Prompt 240 (Tool Credential Isolation)

## What to build

### 1. Migration wizard

```bash
keprix proxy migrate-vault
```

Step-by-step guided migration:

```
keprix Vault Migration
======================

This wizard moves your credentials from the keprix encrypted vault to an
external vault (Bitwarden, 1Password, or OS keychain). After migration,
credentials are injected per-request by the proxy. Your agent never holds
real API keys.

Found 7 credentials in the current vault:

  1. anthropic-api-key       (last used: 2h ago)
  2. openai-api-key          (last used: 3d ago)
  3. tavily-api-key          (last used: 1h ago)
  4. stripe-secret-key       (last used: 5d ago)
  5. sendgrid-api-key        (last used: never)
  6. google-api-key          (last used: 12h ago)
  7. github-token            (last used: 1d ago)

Which vault will you use?
  [1] Bitwarden (detected: bw CLI installed)
  [2] 1Password (detected: op CLI installed)
  [3] OS keychain
  [4] I will configure later

> 1

Migrating 'anthropic-api-key'...
  The current value will be displayed once. Copy it to your Bitwarden vault.
  Bitwarden item name: keprix/anthropic-api-key
  Value: sk-ant-***... (press Enter after copying)

  Verified: Bitwarden item 'keprix/anthropic-api-key' exists.

Migrating 'openai-api-key'...
  The current value will be displayed once. Copy it to your Bitwarden vault.
  Bitwarden item name: keprix/openai-api-key
  Value: sk-proj-***... (press Enter after copying)

  Verified: Bitwarden item 'keprix/openai-api-key' exists.

... (continues for all 7)

Migration complete: 7 credentials moved.
  7 verified in Bitwarden
  0 skipped

Proxy routes created for all 7 credentials.
Run 'keprix proxy verify' to test them.

The old vault is still intact at ~/.keprix/vault/. To delete it after
confirming everything works, run: keprix proxy vault-purge
```

### 2. Partial migration support

Operators can migrate credentials one at a time:

```bash
keprix proxy migrate anthropic-api-key
```

Credentials not yet migrated continue to work from the old vault. The credential pool checks: proxy first, then old vault. Once all credentials for a provider are migrated, the old vault entry can be purged.

### 3. Vault purge

```bash
keprix proxy vault-purge
```

- Lists all credentials still in the old vault.
- Shows which are migrated (green) and which are not (red).
- Requires explicit confirmation.
- Backs up the vault before deleting (to `~/.keprix/vault/vault.db.bak.{timestamp}`).
- After purge, the old vault module is unloaded from the agent.

### 4. New install default

`keprix setup` and the install wizard (Prompt 33) no longer create the encrypted vault by default:

```
Setup wizard (new install):

  How would you like to manage API credentials?
    [1] External vault (Bitwarden, 1Password, or OS keychain) -- recommended
    [2] Cordon proxy (auto-configured, uses your OS keychain)
    [3] keprix encrypted vault (legacy, not recommended for new installs)
    [4] Plain environment variables (legacy)
```

Options 1 and 2 are the new default paths. Options 3 and 4 are marked as legacy with a warning:

```
WARNING: Storing credentials in the keprix vault or environment variables is
deprecated. Credentials stored this way leak into logs, crash dumps, and
child processes. Consider using an external vault (option 1) instead.
```

### 5. Backward compatibility

The old vault continues to work for existing installs. It is not removed from the codebase. The deprecation timeline:

- **v2.2 (now):** Migration wizard available. Old vault works but shows deprecation notice on `keprix status`.
- **v2.3 (next):** Old vault is read-only. New credentials can only be added to the proxy.
- **v3.0 (future):** Old vault is removed. `keprix proxy vault-purge` runs automatically during upgrade if old vault detected.

### 6. Vault health monitoring

`keprix status` reports vault health:

```
Credentials:
  Proxy:       keprix-proxy running on :6790 (Bitwarden)
  Vault (old): 7 credentials stored, 7 migrated, 0 pending
  Status:      All credentials migrated. Run 'keprix proxy vault-purge' to remove old vault.
```

If any credentials are still in the old vault:

```
Credentials:
  Proxy:       keprix-proxy running on :6790 (Bitwarden)
  Vault (old): 7 credentials stored, 5 migrated, 2 pending
  Status:      2 credentials still in old vault. Run 'keprix proxy migrate-vault' to migrate.
```

### 7. Emergency fallback

If the proxy is unreachable or the external vault is down, keprix can fall back to the old vault:

```bash
keprix proxy fallback enable
```

This reads credentials from the old vault as a temporary measure. It logs a critical alert and shows a persistent warning in the dashboard. The fallback is automatically disabled after 24 hours (configurable).

## Files to modify

```
src/keprix/proxy/
  migrate.py               - migration wizard (NEW)
  vault_purge.py           - vault purge with backup (NEW)
  fallback.py              - emergency fallback to old vault (NEW)

src/keprix/security/
  vault_service.py         - add deprecation methods (MODIFY)
  vault_store.py           - add migration helpers (MODIFY)

src/keprix/setup/
  wizard.py                - add external vault option, deprecation warnings (MODIFY)

src/keprix/config/
  health_monitor.py        - add vault health to status output (MODIFY)

scripts/
  wizard.py                - external vault option in install wizard (MODIFY)

docs/
  security/vault-migration.md
  getting-started/credentials.md

tests/
  proxy/
    test_migrate.py
    test_vault_purge.py
    test_fallback.py
    test_wizard_options.py
```

## Acceptance criteria

- `keprix proxy migrate-vault` guides the user through moving each credential to an external vault.
- `keprix proxy vault-purge` backs up the old vault before deleting it.
- New installs default to external vault or Cordon. Old vault option is marked deprecated.
- Existing installs continue to work with the old vault. No forced migration.
- `keprix status` shows a clear deprecation warning if the old vault is still in use.
- Emergency fallback to old vault works when the proxy is unreachable and auto-disables after 24 hours.
- The migration wizard handles credentials that are in use by active agent sessions without interrupting them.
