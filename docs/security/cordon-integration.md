# Using Cordon with Keprix

Cordon by CodeZero is a local credential-injection proxy. It intercepts outbound HTTP requests from Keprix and injects API keys from your vault. Keprix keeps dummy keys and never holds real secrets.

## Quick Start

```bash
npm install -g @codezero-io/cordon
cordon setup hermes
cp src/keprix/optional-skills/devops/cordon/templates/cordon.toml.template ~/.keprix/cordon.toml
cordon service install --config ~/.keprix/cordon.toml
```

Add dummy keys to `~/.keprix/.env`:

```bash
ANTHROPIC_API_KEY=dummy-replaced-by-cordon
OPENAI_API_KEY=dummy-replaced-by-cordon
HTTPS_PROXY=http://127.0.0.1:6790
```

Store real values in 1Password or your OS keychain under the `secret_ref` names in the template.

## Verification

```bash
cordon doctor --config ~/.keprix/cordon.toml
keprix proxy doctor
keprix proxy verify
```

## Switching Proxies

Both Cordon and `keprix proxy` use the same dummy-key and `HTTPS_PROXY` contract.

```bash
keprix proxy setup
keprix proxy start
export HTTPS_PROXY=http://127.0.0.1:6790
```

Switch back to Cordon by starting its service with `~/.keprix/cordon.toml`.
