# Community vs Enterprise

Keprix follows a KNIME-style split: the visual builder is free, while organization governance and fleet controls are enterprise features.

## Feature matrix

| Feature | Community | Enterprise |
| --- | --- | --- |
| Visual Playbook Studio | Yes | Yes |
| YAML playbooks | Yes | Yes |
| Local agent and TUI | Yes | Yes |
| Basic MCP install | Yes | Yes |
| Fleet deploy | No | Yes |
| SSO | No | Yes |
| Audit export | No | Yes |
| Scout fleet dashboard | No | Yes |
| Connector install governance | No | Yes |
| Organization playbook publish | No | Yes |
| Shared template library | No | Yes |

Visual Playbook Studio is free forever in Community Edition.

## Resolution

Keprix resolves edition in this order:

1. `KEPRIX_EDITION=community|enterprise`
2. `~/.keprix/license.json`, for example:

```json
{ "edition": "enterprise", "license_id": "ee-demo-001", "expires_at": null }
```

The v1 self-hosted license file is trust-based. No vendor SDK is required.

## API

```http
GET /api/licensing/edition
```

Returns the current edition and feature matrix used by the UI.

## Scout

Scout is an optional governance connector. Enterprise features can require Scout approval for organization publish and connector governance, while personal playbooks remain available locally.
