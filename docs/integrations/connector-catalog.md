# Connector catalog

The Integrations marketplace (`/integrations`) is the operator-facing catalog for playbook connectors. It brings together MCP manifests, hub connector packs, sidecar bridges, built-in local tools, and provider-backed tools in one searchable surface.

It is not a port of KNIME or n8n node implementations. Keprix exposes a focused starter catalog and routes execution through existing playbooks, MCP servers, hub packs, and HTTP nodes.

## Marketplace vs MCP admin vs Hub

| Surface | Use |
| --- | --- |
| `/integrations` | Browse connectors, see auth pattern, open a sample node in Studio |
| `/admin/mcp` | Configure MCP servers, credentials, OAuth, and tool selection |
| `/hub` | Install packs and templates with manifest checks and rollback |

## Adding a connector

1. Add or update `src/keprix/integrations/connector_seeds.yaml`.
2. Provide a `sample_playbook_node` with `type` and `data`.
3. Link `mcp_server_id`, `hub_pack_id`, or `sidecar_id` when an install path exists.
4. Set `install_hint` honestly. Use "Coming soon; use HTTP node with API key" for stubs.
5. Add or update an MCP manifest under `src/keprix/optional-mcps/` when the connector is MCP-backed.

## Scout audit classes

| Class | Meaning |
| --- | --- |
| `external_read` | Reads third-party data |
| `external_write` | Creates or updates remote records |
| `messaging_send` | Sends user-visible messages |
| `filesystem` | Reads or writes local files |
| `code_exec` | Executes code |
| `network_egress` | Generic outbound HTTP or sidecar traffic |
| `none` | No external audit class |

Studio nodes tagged with `connector_id` carry connector metadata into completed playbook node events as `connector_id` and `scout_audit_class`.

## KNIME positioning

KNIME has a broad node repository. Keprix mirrors the discoverability pattern, not the runtime or Java node model. The catalog starts with 20+ practical connectors and bridges existing systems through MCP, sidecars, and HTTP.
