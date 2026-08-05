# n8n workflow sidecar (MCP bridge)

Use n8n as an **integration sidecar** next to Keprix: keep your existing n8n instance and 300+ community nodes, and let the Keprix agent list, inspect, export, and (optionally) mutate workflows through a stdio MCP bridge. Keprix does **not** bundle n8n or port n8n node implementations.

## When to use

| Goal | Path |
| --- | --- |
| **Live control** of workflows on a running n8n instance | Install the **`n8n`** catalog MCP (this guide) |
| **One-time migration** of workflow JSON into Keprix playbooks | [`migrate from-n8n`](../features/migration.md#from-n8n) CLI |
| **Visual import** into Studio canvas | [Playbook import and export](../features/playbook-import-export.md) |
| **Replace n8n entirely** with native playbooks | Import first, then retire the sidecar when YAML is reviewed |

Choose the sidecar when a customer already runs n8n and needs connectors Keprix has not ported. Choose import when the workflow should become a first-class Keprix playbook.

## Architecture

```text
┌─────────────────┐     stdio MCP      ┌──────────────────┐
│  Keprix agent   │ ◄────────────────► │ keprix-n8n-mcp   │
│  (chat / cron)  │                    │ (catalog install)│
└────────┬────────┘                    └────────┬─────────┘
         │                                    │ HTTPS + API key
         │                                    ▼
         │                           ┌──────────────────┐
         │                           │  n8n instance    │
         │                           │  (your infra)    │
         └──────────────────────────►│  300+ nodes      │
                                     └──────────────────┘
```

- **Keprix** remains the agent OS (sessions, tools, playbooks, vault).
- **n8n** stays a separate process you operate (Docker, cloud, or on-prem).
- The **MCP bridge** is a small Python server cloned at install time; it talks to n8n's REST API over `N8N_BASE_URL`.

No inbound port is opened on Keprix for n8n; traffic is outbound from the bridge to your n8n URL.

## Quick start

### 1. Run n8n (local Docker example)

```bash
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

Open `http://127.0.0.1:5678`, complete setup, then create an API key under **Settings → API**.

### 2. Install the n8n MCP catalog entry

**CLI:**

```bash
keprix mcp install n8n
```

Follow prompts for `N8N_BASE_URL` (default `http://127.0.0.1:5678`) and `N8N_API_KEY`. The installer clones [keprix-n8n-mcp](https://github.com/CyberSamuraiX/keprix-n8n-mcp), creates a venv, and writes `mcp_servers.n8n` into `~/.keprix/config.yaml`.

**Workspace UI:** `/admin/mcp` → **n8n workflow bridge** card → **Install n8n MCP** (same flow; credentials saved to `.env`).

Git bootstrap can take a minute; the UI runs install in the background and tails the action log when needed.

### 3. Verify tools

Start a **new** chat session (MCP tools load at session start). On `/admin/mcp` → **My servers**, use **List tools** on the `n8n` server.

Default-enabled tools (read-mostly):

| Tool | Purpose |
| --- | --- |
| `health` | Bridge + n8n connectivity |
| `list_workflows` / `find_workflows` / `get_workflow` | Inspect workflows |
| `export_workflow` | Download workflow JSON |
| `list_executions` / `get_execution` / `recent_failures` | Execution history |

Mutating tools (activate/deactivate workflow, container logs) are **off by default**. Opt in during the install-time tool checklist if your threat model allows live changes.

### 4. Example chat prompts

- "List my n8n workflows and show which are active."
- "Export workflow `{id}` as JSON so I can review it."
- "Show recent failed executions in n8n."

When the user asks to **run** or **manage** an n8n workflow, prefer `mcp_n8n_*` tools if the server is installed (see routing in the **`productivity-integrations`** skill).

## Import path (playbook migration)

To convert exported n8n JSON into Keprix YAML (one-time, best-effort), use the migration CLI documented in [Migration → From n8n](../features/migration.md#from-n8n):

```bash
python3 -m keprix.keprix_cli.main migrate from-n8n \
  --source n8n-export.json \
  --output-dir .keprix/playbooks/
```

That path does **not** require the MCP sidecar. Use sidecar + import together when you want live n8n control **and** a playbook copy for gradual cutover.

## Security

- **API key scope:** Create a dedicated n8n API key with the minimum rights you need. Store it in `~/.keprix/.env` or Vault; never commit it.
- **Mutations off by default:** Activate/deactivate and similar tools are excluded from `tools.default_enabled` in the catalog manifest. Enable them only if operators accept live production changes from the agent.
- **Network:** Point `N8N_BASE_URL` at a URL reachable from the Keprix host (localhost, VPN, or TLS-terminated internal hostname). Treat the n8n API like any admin surface.
- **License:** n8n's [fair-code license](https://n8n.io/sustainable-use-license/) applies to the n8n instance the **customer** runs. Keprix ships only the MCP bridge connector, not n8n itself.

## Limitations

- Keprix does not ship or support n8n node parity; the sidecar delegates to your n8n instance.
- Workflow **execution** semantics depend on n8n; the bridge exposes API operations exposed by keprix-n8n-mcp, not a full n8n UI replacement.
- Playbook import (`migrate from-n8n`) is best-effort; complex expressions and unsupported nodes need manual YAML edits (see migration doc).

## Operator surfaces

| Surface | Route |
| --- | --- |
| MCP admin + n8n bridge card | `/admin/mcp` |
| One-time JSON → playbook import | `/migrate` or [migration doc](../features/migration.md#from-n8n) |
| Catalog CLI | `keprix mcp catalog`, `keprix mcp install n8n` |

Related: [MCP servers](mcp.md), [Playbooks](../features/playbooks.md), [Migration](../features/migration.md).
