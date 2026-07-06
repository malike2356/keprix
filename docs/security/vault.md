# Credential vault

The vault encrypts stored credentials at rest using `KEPRIX_VAULT_KEY`.

## Generate a key

```bash
openssl rand -base64 32
```

Set the result as `KEPRIX_VAULT_KEY` in `.env` before first use.

## API

Vault routes: `/api/vault/*` (authenticated).

## Backup warning

Backups include vault keys. Store archives offline and encrypted.
