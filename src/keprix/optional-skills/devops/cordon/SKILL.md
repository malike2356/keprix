---
name: cordon-credential-proxy
description: "Diagnose and operate Cordon or keprix-proxy credential injection. Use for API key 401s, proxy setup, route verification, and credential rotation."
version: 1.0.0
author: Keprix
license: MIT
platforms: [linux, macos]
metadata:
  keprix:
    tags: [security, credentials, proxy, cordon, devops]
---

# Cordon Credential Proxy

Use this skill when an operator asks to set up, diagnose, verify, or rotate credentials for Cordon or the built-in `keprix proxy`.

## Decision

- Use **Cordon** for individual developers who want CodeZero's external proxy and Hermes-compatible setup.
- Use **keprix-proxy** for production deployments that need Keprix audit trails, rotation reminders, and fleet-aware operation.

## Workflows

### Diagnose 401s

Run:

```bash
scripts/diagnose.sh
```

Check `HTTPS_PROXY`, Cordon status, Keprix proxy status, and route verification. Do not ask the user to paste real API keys.

### Setup

Run:

```bash
scripts/setup.sh
```

Then ask the operator to store real secrets in 1Password or the selected keychain. Dummy keys belong in `~/.keprix/.env`.

### Rotate

Run:

```bash
scripts/rotate.sh stripe-secret-key
```

For the built-in proxy, prefer:

```bash
keprix proxy rotate stripe-secret-key --verify
```

### Verify

Run:

```bash
scripts/verify.sh
```

Report missing routes and missing vault items separately.
