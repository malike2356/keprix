# Manifest reference

File name: `keprix.sidecar.yaml` (or `.yml`).

Contract: **1.0.0**. Schema:
`schemas/universal-sidecar/keprix.sidecar.schema.json`.

## Required fields

| Field | Type | Notes |
| --- | --- | --- |
| `contract_version` | string | Must be `"1.0.0"` |
| `project_key` | string | `^[a-z][a-z0-9_-]{1,63}$` |
| `display_name` | string | Human label |
| `deployment` | string | Deployment id |
| `environment` | enum | `local`, `dev`, `staging`, `prod`, `airgap` |
| `base_url` | uri | Product southbound base URL |
| `auth` | object | See Authentication |

## Common optional fields

- `callback_urls` - product callback endpoints
- `auth.vault_ref` - `env:NAME`, `vault:path`, or `secret:name` (never raw secrets)
- `capabilities[]` - node bindings (`node`, `version`, scopes, timeouts)
- `connectors[]` - declared southbound operations (default deny)
- `events[]` - inbound/outbound CloudEvents-style declarations
- `webhooks` - signature algorithm and vault ref
- `context_slices[]` - purpose-limited context for prompts
- `memory` - `disabled` / `ephemeral` / `project_facts` / `subject` / `shared_approved`
- `approvals` - risk classes requiring human decision
- `budgets` - RPM, concurrent jobs, tokens, cost, callbacks, storage
- `retention` - days for events, jobs, artifacts, audit
- `egress` - `allow_loopback`, `allow_private_networks`, `allowed_hosts`
- `feature_flags` - boolean map

## Forbidden

- Embedding passwords, API keys, or token values in the YAML
- Executable hooks (`hooks`, `exec`, `eval`, inline code)
- Blocked URI schemes (`file`, `ftp`, `data`, ...) and cloud metadata hosts

## Examples

See `src/keprix/universal_sidecar/manifest/examples/`:

- `minimal.yaml`
- `read-only.yaml`
- `read-plus-propose.yaml`
- `async-job.yaml`
- `event-driven.yaml`
