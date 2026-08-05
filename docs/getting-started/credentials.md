# Credentials

Keprix recommends external credential storage for new installs.

| Option | Recommendation |
| --- | --- |
| External vault | Recommended for production. Use Bitwarden, 1Password, or OS keychain through `keprix proxy`. |
| Cordon proxy | Recommended quick start for individual developers. |
| Keprix encrypted vault | Legacy. Existing installs continue to work, but migrate when practical. |
| Plain `.env` secrets | Legacy. Use only for local throwaway development. |

Start with:

```bash
keprix proxy setup
keprix proxy migrate-vault
keprix proxy verify
```

For Cordon, see [Using Cordon with Keprix](../security/cordon-integration.md).
