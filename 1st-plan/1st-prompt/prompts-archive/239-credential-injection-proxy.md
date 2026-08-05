# keprix - Prompt: Credential Injection Proxy (Cordon Pattern)

**Status:** Shipped (Python implementation under `src/keprix/proxy/`; CLI via `keprix proxy`).

## Purpose

keprix agents currently hold API keys in environment variables and the encrypted vault. Env vars leak into logs, crash dumps, child processes, and `ps` output. The vault stores secrets at rest but the agent still reads them into memory on startup. Prompt 08 (Vault) and Prompt 09 (agent-managed credentials) gave us encrypted storage and setup wizards. Now we eliminate secrets from the agent's memory entirely.

This prompt builds a local credential-injection proxy following the Cordon by CodeZero pattern. The proxy intercepts outbound HTTP/HTTPS requests, fetches credentials from an external vault (1Password, Bitwarden, or OS keychain) at request time, and injects them into the request. The keprix agent never holds real API keys.

## Guiding principle

The proxy is infrastructure, not a keprix feature. It runs as a separate process. keprix connects through it like any HTTP proxy. This keeps the security boundary clean: compromise of the agent does not compromise credentials.

## What already exists (do not rebuild)

- `security/vault_service.py` -- encrypted vault orchestration
- `security/vault_store.py` -- Fernet-encrypted credential storage
- `security/vault_session.py` -- vault session management
- `security/bitwarden_source.py` -- Bitwarden Secrets Manager integration
- `agent/credential_pool.py` -- credential pool for agent providers
- `agent/credential_sources.py` -- credential source abstraction
- `agent/credential_persistence.py` -- persistence layer
- `agent/secret_sources/` -- secret source plugins directory

## What to build

### 1. Local credential proxy (`keprix-proxy`)

A lightweight Rust (or Go) binary that runs as a background process:

```
keprix-proxy/
  Cargo.toml
  src/
    main.rs              - entry point, CLI args (start, setup, doctor, stop)
    proxy.rs             - HTTP/HTTPS MITM proxy using hyper or h3
    injector.rs          - route matching, credential injection
    vault/
      mod.rs             - vault provider trait
      onepassword.rs     - 1Password CLI (`op`) integration
      bitwarden.rs       - Bitwarden CLI (`bw`) integration
      keychain.rs        - OS keychain (macOS Keychain, freedesktop Secret Service)
    config.rs            - cordon.toml parser, route definitions
    certs.rs             - CA certificate generation, trust store management
    secret.rs            - Secret type: zeroize on drop, no Debug/Display
    doctor.rs            - diagnostic checks (config, certs, vault connectivity)
    telemetry.rs         - opt-in anonymous usage ping
```

### 2. Proxy configuration (`~/.keprix/proxy.toml`)

```toml
[proxy]
listen = "127.0.0.1:6790"
vault = "bitwarden"          # bitwarden | onepassword | keychain
log_level = "warn"

[[routes]]
host = "api.anthropic.com"
header_name = "x-api-key"
type = "header"
secret_ref = "anthropic-api-key"

[[routes]]
host = "api.openai.com"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "openai-api-key"

[[routes]]
host = "api.stripe.com"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "stripe-secret-key"

[[routes]]
host = "api.sendgrid.com"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "sendgrid-api-key"

[[routes]]
host = "generativelanguage.googleapis.com"
header_name = "x-goog-api-key"
type = "header"
secret_ref = "gemini-api-key"
```

### 3. Security model (hardcoded, not configurable)

The proxy enforces security structurally, not through configuration:

- Binds to `127.0.0.1` only. No option to bind to `0.0.0.0` or any other address.
- For unmatched outbound traffic, an SSRF denylist blocks private/loopback IPs. No disable option.
- Upstream TLS verification uses the system root store. No option to skip.
- Credentials are fetched per-request from the vault. Never cached, never persisted to disk.
- The `Secret` type zeroizes memory on drop. No Debug or Display implementations.
- `#![forbid(unsafe_code)]` in Rust. Security depends on compilation, not developer discipline.

### 4. CLI commands

```
keprix-proxy start       - start the proxy (foreground or --daemon)
keprix-proxy setup       - interactive setup wizard
keprix-proxy doctor      - diagnostic checks
keprix-proxy route add   - add a new route
keprix-proxy route list  - list configured routes
keprix-proxy route rm    - remove a route
keprix-proxy secret set  - store a credential in the vault
keprix-proxy env         - print proxy env vars (HTTPS_PROXY, SSL_CERT_FILE, etc.)
keprix-proxy stop        - stop a running proxy
keprix-proxy status      - show proxy status and health
```

### 5. keprix integration

Add to `keprix/__main__.py`:

```python
# New subcommand
keprix proxy setup        - run keprix-proxy setup, configure keprix to use it
keprix proxy start        - start proxy + configure keprix env
keprix proxy stop         - stop proxy
keprix proxy status       - show proxy status
keprix proxy doctor       - full diagnosis
```

The setup wizard:

1. Detects if keprix-proxy binary is installed. If not, offers to install it.
2. Detects available vaults (Bitwarden CLI, 1Password CLI, OS keychain).
3. For each configured LLM provider in keprix, offers to create a route.
4. Generates CA certificates.
5. Writes `~/.keprix/proxy.toml`.
6. Writes proxy env vars to `~/.keprix/.env` (like Cordon's `cordon env`).
7. Sets dummy keys in the existing keprix env vars so the agent knows which providers to use:

```
ANTHROPIC_API_KEY=dummy-replaced-by-proxy
OPENAI_API_KEY=dummy-replaced-by-proxy
```

The agent needs these dummy keys to know which providers are available. The real keys are injected by the proxy.

### 6. Migration from current vault

The existing keprix vault (`security/vault_store.py`) stores credentials encrypted on disk. The migration path:

1. `keprix proxy migrate-vault` reads credentials from the existing vault.
2. For each credential, prompts: "Store this in your external vault?".
3. The user copies the credential to their vault (1Password, Bitwarden, keychain).
4. The proxy route is created pointing to the vault reference.
5. The old vault entry is marked as migrated (not deleted -- user verifies first).
6. After all credentials are migrated, `keprix proxy verify` confirms all routes resolve.

## Files to create

```
keprix-proxy/                          - NEW: standalone Rust/Go project
  Cargo.toml
  src/main.rs
  src/proxy.rs
  src/injector.rs
  src/vault/mod.rs
  src/vault/onepassword.rs
  src/vault/bitwarden.rs
  src/vault/keychain.rs
  src/config.rs
  src/certs.rs
  src/secret.rs
  src/doctor.rs
  src/telemetry.rs

src/keprix/
  proxy/                               - NEW: keprix-side integration
    __init__.py
    cli.py                             - keprix proxy subcommands
    setup.py                           - setup wizard
    migrate.py                         - vault-to-proxy migration
    verify.py                          - route verification
    env_writer.py                      - writes proxy env vars to keprix .env

docs/
  security/credential-proxy.md         - operator guide

tests/
  proxy/
    test_setup.py
    test_migrate.py
    test_verify.py
    test_env_writer.py
    test_integration.py                - end-to-end: proxy + keprix + real vault
```

## Acceptance criteria

- `keprix proxy setup` detects available vaults, creates routes for configured providers, and writes proxy env vars.
- With the proxy running, the keprix agent makes LLM API calls without real keys in its environment.
- `keprix proxy migrate-vault` reads the existing vault and guides the user through moving each credential to an external vault.
- The proxy rejects requests to unmatched hosts that resolve to private/loopback IPs.
- The proxy never writes credentials to disk. The `Secret` type zeroizes on drop.
- `keprix proxy doctor` reports config validity, cert paths, vault connectivity, and proxy health.
- Changing a credential in the vault takes effect on the next request without restarting keprix.
- Certificate errors produce clear troubleshooting messages with exact fix commands.
