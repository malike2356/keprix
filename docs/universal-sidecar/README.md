# Keprix Universal Sidecar

Contract version **1.0.0**. Plain ASCII docs only.

The Universal Sidecar lets any product project attach Keprix agent capabilities
without giving Keprix unrestricted database access or becoming a hidden product
backend. The product remains source of truth for users, tenancy, entitlements,
records, billing, domain workflows, and UI.

## Journey overview

1. Author a `keprix.sidecar.yaml` for your project (see examples under
   `src/keprix/universal_sidecar/manifest/examples/`).
2. Pair the product with a short-lived bootstrap / pairing code.
3. Discover health and capabilities.
4. Create a scoped session, then invoke declared nodes or start jobs.
5. Exchange events and webhooks; gate writes with approvals.
6. Harden egress, TLS, budgets, and kill switches before production.

## Ports and modes

| Mode | Bind | Port | Notes |
| --- | --- | --- | --- |
| Mounted | `127.0.0.1` | **3333** | Routes under `/sidecar/v1` on the existing Keprix backend |
| Sidecar-only | `127.0.0.1` | **3360** | Reduced process without admin/workspace UI |

Default bind is loopback. Do not expose anonymous invoke on a public address.

API prefix: `/sidecar/v1` (separate from OpenAI-compatible `/v1/chat/*` and
legacy product packs `/v1/products/{key}`).

## Doc index

| Doc | Topic |
| --- | --- |
| [architecture.md](architecture.md) | Ownership, modes, non-goals |
| [manifest-reference.md](manifest-reference.md) | `keprix.sidecar.yaml` fields |
| [authentication.md](authentication.md) | Pairing, tokens, scopes |
| [connectors.md](connectors.md) | Southbound product API |
| [nodes-and-playbooks.md](nodes-and-playbooks.md) | Capability nodes |
| [events-jobs-streaming.md](events-jobs-streaming.md) | Events, jobs, SSE |
| [memory-and-files.md](memory-and-files.md) | Memory namespaces and files |
| [approvals.md](approvals.md) | Human approval gates |
| [production-hardening.md](production-hardening.md) | Production checklist |
| [observability.md](observability.md) | Metrics and audit |
| [troubleshooting.md](troubleshooting.md) | Common failures |
| [upgrades.md](upgrades.md) | Expand / migrate / contract |
| [security-checklist.md](security-checklist.md) | Operator security list |
| [threat-model.md](threat-model.md) | Threat scenarios |
| [api-reference.md](api-reference.md) | HTTP routes |
| [compatibility.md](compatibility.md) | Product pack migration |
| [changelog.md](changelog.md) | Version history |
| [self-knowledge-blurb.md](self-knowledge-blurb.md) | RAG / self-knowledge hint |

## Schema and examples

- JSON Schema: `schemas/universal-sidecar/keprix.sidecar.schema.json`
- Example manifests: `src/keprix/universal_sidecar/manifest/examples/`
- Starters: `examples/universal-sidecar/`
- Deploy: `deploy/universal-sidecar/`
- SDKs: `keprix_sdk/python` and `keprix_sdk/typescript` (`SidecarClient`)
