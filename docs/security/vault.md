# Credential vault

The vault encrypts stored credentials at rest using `KEPRIX_VAULT_KEY`.

The Keprix encrypted vault is now a legacy compatibility path for existing installs. New installs should use [Credential proxy](credential-proxy.md), [Cordon integration](cordon-integration.md), or another external vault. Migration steps are in [Vault migration](vault-migration.md).

## Generate a key

```bash
openssl rand -base64 32
```

Set the result as `KEPRIX_VAULT_KEY` in `.env` before first use.

## API

Vault routes: `/api/vault/*` (authenticated).

## Backup warning

Backups include vault keys. Store archives offline and encrypted.
