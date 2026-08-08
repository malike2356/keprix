# keprix - Prompt: Cordon Integration and Operator Guide

## Purpose

CodeZero's Cordon is an existing open-source credential injection proxy. It already has a Hermes Agent integration guide. Since keprix is a Hermes fork, Cordon works with keprix today.

This prompt creates the operator documentation, skill pack, and integration tests so keprix operators can choose between:
- **Cordon (external):** Use CodeZero's existing proxy. Lighter lift, fewer features to maintain.
- **keprix-proxy (built-in, Prompt 239):** Deeper integration, fleet-aware, keprix-native tooling.

Both follow the same credential contract. Operators can switch between them by changing the proxy URL.

## What to build

### 1. Cordon integration guide

```markdown
# Using Cordon with keprix

Cordon by CodeZero is a local credential-injection proxy. It intercepts outbound
HTTP requests from keprix and injects API keys from your vault (1Password, OS
keychain). keprix never holds real secrets.

## Quick start

1. Install Cordon: `npm install -g @codezero-io/cordon`
2. Run: `cordon setup hermes` (uses keprix's Hermes-compatible config path)
3. Store your API keys in 1Password or your OS keychain
4. Add dummy keys to `~/.keprix/.env`:
   ```
   ANTHROPIC_API_KEY=dummy-replaced-by-cordon
   OPENAI_API_KEY=dummy-replaced-by-cordon
   ```
5. Start Cordon: `cordon service install --config ~/.keprix/cordon.toml`
6. Start keprix normally. All API calls route through Cordon.

## Verification

```bash
cordon doctor --config ~/.keprix/cordon.toml
keprix proxy doctor  # keprix-side diagnostics
```

## Switching between Cordon and keprix-proxy

Both proxies expose the same env var contract. To switch:

```bash
# Switch to keprix-proxy
keprix proxy setup
keprix proxy start

# Switch back to Cordon
cordon service install --config ~/.keprix/cordon.toml
```

The agent does not care which proxy is running. It just honours HTTPS_PROXY.
```

### 2. Cordon skill pack

A keprix skill pack at `skills/devops/cordon/` that the agent can use to help operators:

```
skills/devops/cordon/
  SKILL.md               - skill definition
  scripts/
    diagnose.sh           - run cordon doctor + keprix proxy doctor
    rotate.sh             - rotate a credential via cordon secret set
    verify.sh             - verify all routes resolve
    setup.sh              - full setup from zero
  templates/
    cordon.toml.template  - template with keprix provider routes
```

The skill pack enables the agent to respond to queries like:
- "My API calls are failing with 401 -- check if Cordon is working"
- "Set up Cordon with my Anthropic key"
- "Rotate the Stripe API key"
- "Show me which credentials are configured in Cordon"

### 3. Provider route templates

Pre-configured route templates for all LLM providers keprix supports:

```toml
# Anthropic
[[routes]]
host = "api.anthropic.com"
header_name = "x-api-key"
type = "header"
secret_ref = "anthropic-api-key"

# OpenAI
[[routes]]
host = "api.openai.com"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "openai-api-key"

# Google Gemini
[[routes]]
host = "generativelanguage.googleapis.com"
header_name = "x-goog-api-key"
type = "header"
secret_ref = "gemini-api-key"

# DeepSeek
[[routes]]
host = "api.deepseek.com"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "deepseek-api-key"

# Groq
[[routes]]
host = "api.groq.com"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "groq-api-key"

# OpenRouter
[[routes]]
host = "openrouter.ai"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "openrouter-api-key"

# Mistral
[[routes]]
host = "api.mistral.ai"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "mistral-api-key"

# Together AI
[[routes]]
host = "api.together.xyz"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "together-api-key"

# Fireworks
[[routes]]
host = "api.fireworks.ai"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "fireworks-api-key"

# X.AI / Grok
[[routes]]
host = "api.x.ai"
header_name = "Authorization"
scheme = "Bearer"
type = "header"
secret_ref = "xai-api-key"
```

### 4. Cordon health check integration

Add to `keprix/security/health_monitor.py`:

```python
class CordonHealthCheck:
    """Checks that the credential proxy (Cordon or keprix-proxy) is running."""

    async def check(self) -> HealthStatus:
        # 1. Check if HTTPS_PROXY is set
        # 2. Check if the proxy port is listening
        # 3. Make a probe request through the proxy
        # 4. Return status with diagnostic info
```

The health check appears in `keprix status` and the admin dashboard alongside Postgres, Redis, and SearXNG health checks.

### 5. Decision matrix documentation

A guide helping operators choose between Cordon and keprix-proxy:

| Factor | Cordon (external) | keprix-proxy (built-in) |
|---|---|---|
| Setup time | 2 minutes (`cordon setup hermes`) | 5 minutes (wizard) |
| Vault support | 1Password, OS keychain | Bitwarden, 1Password, OS keychain |
| Fleet-aware | No (local only) | Yes (Prompt 239 extends to fleet) |
| Audit integration | Basic (proxy logs) | Full (keprix audit trail) |
| Rotation scheduling | No | Yes (reminders, grace periods) |
| Maintenance burden | Zero (CodeZero maintains) | keprix team maintains |
| Offline/air-gapped | Requires npm install | Ships with keprix |
| Recommendation | Individual developers, quick start | Production deployments, fleet operators |

## Files to create

```
skills/devops/cordon/
  SKILL.md
  scripts/diagnose.sh
  scripts/rotate.sh
  scripts/verify.sh
  scripts/setup.sh
  templates/cordon.toml.template

src/keprix/proxy/
  cordon_bridge.py         - Cordon compatibility layer (env var contract, health check)

docs/
  security/cordon-integration.md
  security/proxy-comparison.md

tests/
  proxy/
    test_cordon_compat.py
```

## Acceptance criteria

- `cordon setup hermes` configures a working keprix credential proxy without manual steps beyond storing API keys.
- The keprix agent makes LLM API calls through Cordon with zero code changes.
- `keprix status` shows Cordon proxy health alongside other services.
- The Cordon skill pack enables the agent to diagnose and fix credential issues.
- Operators can switch between Cordon and keprix-proxy by changing one environment variable.
- All 10 provider route templates are tested and resolve correctly.
