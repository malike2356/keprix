# Keprix - Prompt 234: Connector Catalog Marketplace

**Series:** KNIME adoption pack **233-238**  
**Principle:** Bridge KNIME's **connector discoverability**, not KNIME's **300+ Java nodes**. MCP manifests + hub packs + n8n sidecar remain the integration spine.

**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

A first-class **Integrations** marketplace at `/integrations` where operators browse, install, and attach connectors to Visual Playbook Studio nodes. Addresses KNIME's perceived moat (connector count) with **20 excellent connectors** and honest copy.

| Surface | Route |
| --- | --- |
| Marketplace grid | `/integrations` |
| Catalog API | `GET /api/integrations/catalog` |
| Install | `POST /api/integrations/catalog/{id}/install` |
| Studio deep link | `/playbooks/studio/new?connector={id}` |

---

## 2. KNIME / n8n study map (read only)

| Pattern | Mirror | Keprix target |
| --- | --- | --- |
| Node category taxonomy | `knime-base/` package prefixes (`org.knime.base.io.*`) | `category` field on `ConnectorEntry` |
| Node factory registration | KNIME `NodeFactory` + plugin.xml | MCP manifest + hub pack registry |
| Integration search | KNIME node repository view | Marketplace search + filters |
| Prebuilt node on canvas | Drag connector -> configured node | `sample_playbook_node` seed in studio |

Do not parse KNIME plugin.xml or port Java nodes.

---

## 3. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Hub pack install | `src/keprix/hub/routes.py`, `frontend/.../hub/page.tsx` |
| MCP catalog | `src/keprix/keprix_cli/mcp_catalog.py` |
| MCP admin | `src/keprix/keprix_cli/mcp_admin_routes.py`, `admin/mcp/page.tsx` |
| MCP tool bridge | `src/keprix/tools/mcp_tool.py` |
| n8n sidecar | `src/keprix/optional-mcps/n8n/manifest.yaml`, prompt 210 |
| n8n YAML migrate | `src/keprix/backend/migration/n8n_converter.py` |
| Studio HTTP/agent nodes | Prompt **233** |
| Productivity skill pack | Prompt 175 |
| Notion RAG | Prompt 174 |

---

## 4. Connector registry schema

Create `src/keprix/integrations/__init__.py` and `src/keprix/integrations/connector_catalog.py`:

```python
from dataclasses import dataclass, field
from typing import Literal

AuthPattern = Literal["api_key", "oauth", "mcp", "sidecar", "none", "env"]
AuditClass = Literal[
    "external_read", "external_write", "messaging_send",
    "filesystem", "code_exec", "network_egress", "none"
]
Category = Literal["productivity", "data", "messaging", "ai", "devtools", "automation"]

@dataclass(frozen=True)
class ConnectorEntry:
    id: str
    label: str
    category: Category
    description: str
    icon: str              # lucide icon name OR /integrations/icons/{id}.svg
    auth_pattern: AuthPattern
    mcp_server_id: str | None = None
    hub_pack_id: str | None = None
    sidecar_id: str | None = None
    scout_audit_class: AuditClass = "external_read"
    docs_url: str = ""
    sample_playbook_node: dict = field(default_factory=dict)
    featured: bool = False
    tags: tuple[str, ...] = ()
    install_hint: str = ""  # operator-facing one-liner
```

### 4.1 Bootstrap loader

```python
def load_connector_catalog() -> list[ConnectorEntry]:
    """Merge static seeds + MCP manifest scan + hub connector metadata."""

def get_connector(connector_id: str) -> ConnectorEntry | None: ...

def catalog_install_status(connector_id: str, *, workspace_id: str) -> dict:
    """Return { installed: bool, reason?: str } from MCP/hub state."""
```

**Static seed file:** `src/keprix/integrations/connector_seeds.yaml` (20 entries). Loader enriches from live MCP manifests where ids match.

### 4.2 Required v1 connectors (minimum 20)

| id | category | auth | source |
| --- | --- | --- | --- |
| notion | productivity | mcp | existing MCP |
| trello | productivity | mcp | existing MCP |
| slack | messaging | mcp/oauth | existing |
| github | devtools | mcp | existing |
| google_drive | productivity | oauth | MCP or stub |
| gmail | messaging | oauth | MCP or stub |
| telegram | messaging | env | gateway |
| discord | messaging | env | gateway |
| web_search | ai | api_key | tool registry |
| n8n_sidecar | automation | sidecar | optional-mcps/n8n |
| postgres | data | api_key | MCP stub ok |
| sqlite | data | none | local |
| http_generic | devtools | none | built-in http step |
| openai | ai | api_key | provider |
| anthropic | ai | api_key | provider |
| filesystem | devtools | none | local tools |
| email_smtp | messaging | env | productivity pack |
| calendar | productivity | oauth | stub |
| jira | devtools | api_key | stub |
| stripe | data | api_key | stub |

Stubs must set `install_hint: "Coming soon; use HTTP node with API key"` and `installed: false` until MCP exists. Do not fake installed state.

### 4.3 sample_playbook_node shape (for studio 233)

```json
{
  "type": "agent_task",
  "data": {
    "label": "Notion: search pages",
    "prompt": "Search Notion for {{ state.query }}",
    "tools": ["mcp_notion_search"],
    "connector_id": "notion"
  }
}
```

HTTP connectors use `type: "http"` with sample url/method in `data`.

---

## 5. API routes

Create `src/keprix/integrations/connector_routes.py`:

| Method | Route | Query/body | Response |
| --- | --- | --- | --- |
| GET | `/api/integrations/catalog` | `category`, `featured`, `q`, `installed` | `{ connectors: [...] }` |
| GET | `/api/integrations/catalog/{id}` | - | `{ connector, install_status }` |
| POST | `/api/integrations/catalog/{id}/install` | `{ confirm?: bool }` | `{ ok, next_url? }` |
| GET | `/api/integrations/categories` | - | `{ categories: [{ id, label, count }] }` |

**Install routing:**

```python
def install_connector(connector_id: str) -> InstallResult:
    if entry.mcp_server_id:
        return install_mcp_server(entry.mcp_server_id)  # existing admin path
    if entry.hub_pack_id:
        return install_hub_pack(entry.hub_pack_id)
    if entry.sidecar_id:
        return redirect_sidecar_setup(entry.sidecar_id)
    raise HTTPException(501, detail="connector_not_installable")
```

**Enterprise governance (235):** When `feature_enabled("connector_governance")`, install returns `{ status: "pending_approval" }` instead of immediate install. Admin approve route deferred to 235.

Register router in `src/keprix/api/server.py`. Session auth required.

---

## 6. Scout audit class wiring

Create `src/keprix/integrations/connector_audit.py`:

```python
def audit_class_for_tools(tool_names: list[str]) -> str | None:
    """Map tool name prefix to scout_audit_class via catalog."""

def enrich_run_event(event: dict, *, step_config: dict) -> dict:
    """Add connector_id and scout_audit_class to playbook run event payload."""
```

Extend playbook run event emission in `src/keprix/playbook/run_routes.py` or event builder:

- When step config includes `connector_id`, attach `{ connector_id, scout_audit_class }` to `playbook.node.completed` events.

Document classes in `docs/integrations/connector-catalog.md`:

| Class | Meaning |
| --- | --- |
| external_read | Reads third-party data |
| external_write | Creates/updates remote records |
| messaging_send | Sends user-visible messages |
| filesystem | Local file access |
| code_exec | Executes code |
| network_egress | Generic HTTP egress |

---

## 7. Frontend marketplace UI

Create:

```
frontend/src/app/(workspace)/integrations/page.tsx
frontend/src/components/integrations/
├── ConnectorGrid.tsx
├── ConnectorCard.tsx
├── ConnectorDetailDrawer.tsx
├── CategoryFilter.tsx
└── InstallButton.tsx
frontend/src/lib/integrations-api.ts
```

### 7.1 Page layout

| Section | Content |
| --- | --- |
| Header | Title **Integrations**; subtitle honest count: "20+ connectors" |
| Featured row | Horizontal scroll, max 8 `featured: true` |
| Filters | Category chips + search input |
| Grid | Responsive 3-col cards |

### 7.2 Connector card

| Element | Source field |
| --- | --- |
| Icon | `icon` |
| Title | `label` |
| Category chip | `category` |
| Auth badge | `auth_pattern` (API Key, OAuth, MCP, Sidecar) |
| Installed dot | `install_status.installed` |

### 7.3 Detail drawer

| Action | Behavior |
| --- | --- |
| Install | POST install; toast result; refresh status |
| Documentation | Open `docs_url` |
| Open in Playbook Studio | Navigate `/playbooks/studio/new?connector={id}` |
| Configure MCP | Link `/admin/mcp` when auth_pattern=mcp |

### 7.4 n8n sidecar card (special)

| Field | Value |
| --- | --- |
| Badge | **Sidecar bridge** |
| Copy | Import workflows with `keprix migrate from-n8n`; run via sidecar until native node ships |
| Link | `docs/integrations/n8n-sidecar.md` |
| Install | Sidecar setup wizard |

### 7.5 Navigation

Add to `frontend/src/lib/navigation.ts` under **Automations**:

```typescript
{ id: "integrations", label: "Integrations", href: "/integrations", icon: "Plug" }
```

Cross-link from `/hub` ("Browse all integrations") and `/admin/mcp` ("Marketplace view").

---

## 8. Studio integration (233)

In `frontend/src/app/(workspace)/playbooks/studio/[id]/page.tsx`:

- Parse `?connector={id}` on load
- Fetch `GET /api/integrations/catalog/{id}`
- If `sample_playbook_node` present, add node to canvas at center with unique id
- Show toast: "Added {label} sample node"

In `NodeInspector.tsx`:

- When `data.connector_id` set, show read-only connector badge + link to `/integrations?id={connector_id}`

---

## 9. Tests

`tests/integrations/test_connector_catalog.py`:

| Test | Assert |
| --- | --- |
| `test_catalog_minimum_count` | >= 20 entries |
| `test_each_entry_complete` | icon, auth_pattern, scout_audit_class, sample_playbook_node |
| `test_get_unknown_404` | |
| `test_install_notion_mcp` | mock MCP install called |
| `test_audit_class_enrichment` | run event includes class |

`tests/integrations/test_connector_seeds.yaml` valid YAML (optional schema test).

---

## 10. Documentation

Create `docs/integrations/connector-catalog.md`:

- Marketplace purpose vs MCP admin vs hub
- How to add a connector (seed YAML + MCP manifest)
- Scout audit classes
- Honest positioning vs KNIME (bridge, not port)

Update `docs/features/hub-and-packs.md` cross-link.

---

## 11. Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `GET /api/integrations/catalog` returns >= 20 connectors |
| 2 | Each entry has icon, auth_pattern, scout_audit_class, sample_playbook_node |
| 3 | `/integrations` renders grid; search filters results |
| 4 | Install triggers existing MCP or hub flow for at least 3 live connectors |
| 5 | **Open in Studio** prefills sample node via query param |
| 6 | n8n sidecar card shows bridge badge + migrate doc link |
| 7 | Run events include connector metadata when step tagged |
| 8 | Copy never claims "300+" connectors |
| 9 | `pytest tests/integrations/test_connector_catalog.py` passes |
| 10 | No duplicate connector registry in Carina (Carina reads this API per `knime-adoption--04`) |

---

## 12. Out of scope

| Item | Owner |
| --- | --- |
| Porting n8n node implementations | Never |
| Paid marketplace revenue share | GTM later |
| Carina-branded hub UI | `knime-adoption--04` |
| Connector approval admin UI | Prompt **235** enterprise |
| Warehouse connectors (Snowflake, SAP) | Defer unless MCP exists |

---

## 13. Archive

`prompts-archive/234-connector-catalog-marketplace.md` when AC pass. Update build order and competitive note.
