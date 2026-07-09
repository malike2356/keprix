# Credential injection proxy

Keprix can route outbound LLM and integration HTTP calls through a **local credential-injection proxy**. The agent keeps dummy API key env vars; the proxy fetches real secrets from an external vault at request time and injects them into outbound headers.

## Why

Environment variables leak into logs, crash dumps, child processes, and `ps` output. The encrypted Keprix vault still loads secrets into agent memory on startup. The proxy keeps the security boundary outside the agent process.

## Quick start

```bash
keprix proxy setup
keprix proxy doctor
keprix proxy start
```

In another shell:

```bash
eval "$(keprix proxy env)"
curl -s http://127.0.0.1:3333/api/health
```

## Configuration

Config file: `~/.keprix/proxy.toml`

```toml
[proxy]
listen = "127.0.0.1:6790"
vault = "keychain"
log_level = "warn"

[[routes]]
host = "api.anthropic.com"
header_name = "x-api-key"
type = "header"
secret_ref = "anthropic-api-key"
```

## Vault providers

| Provider | Value | Notes |
| --- | --- | --- |
| Local keychain file | `keychain` | Default; secrets in `~/.keprix/proxy-local-vault.json` |
| Bitwarden | `bitwarden` | Requires `bws` or `bw` CLI |
| 1Password | `onepassword` | Requires `op` CLI |

## Commands

| Command | Purpose |
| --- | --- |
| `keprix proxy setup` | Create routes and write proxy env vars |
| `keprix proxy start [--daemon]` | Run the proxy (localhost only) |
| `keprix proxy stop` | Stop background proxy |
| `keprix proxy status` | Show proxy process status |
| `keprix proxy doctor` | Config, CA, vault, and route checks |
| `keprix proxy env` | Print `export` lines for shell |
| `keprix proxy migrate-vault` | Copy real keys from `.env` into local vault |
| `keprix proxy verify` | Confirm every route resolves a secret |
| `keprix proxy route add/list/rm` | Manage routes |

## OAuth upstream proxy (legacy)

The OAuth upstream proxy for Nous Portal / xAI remains available:

```bash
keprix proxy oauth start --provider nous
keprix proxy oauth status
```

## Security model

- Binds to `127.0.0.1` only
- Unmatched outbound hosts are checked against a private/loopback SSRF denylist
- Upstream TLS verification uses the system trust store
- Secrets are fetched per request and zeroized after use
- Trust the generated CA via `SSL_CERT_FILE` when using HTTPS through the proxy

## Related

- [Vault](vault.md)
- [Hardening](hardening.md)
