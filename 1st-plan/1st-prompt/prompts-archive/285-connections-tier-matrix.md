# Keprix - Prompt 285: Connections tier matrix (duplicate)

**Status:** Shipped (same implementation as archived **277-connections-tier-matrix.md**).  
**Note:** This pending file reused number 285; implementation landed under prompt **277** in the Nate Herk AIOS series.

---

# Keprix - Prompt 277: Connections tier matrix

**Series:** Nate Herk AIOS adoption **274-279**  
**Master reference:** `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Connections tier matrix**: living `connections.md` doc, tier-1 domain model, day-2 connection priority wizard, and **AI service account** integration guidance (Nate "Up AI" pattern).

**Tier-1 domains:**

| ID | Label | Example integrations |
| --- | --- | --- |
| `revenue` | Revenue | Stripe, QuickBooks, sheets |
| `customer` | Customer | CRM, support |
| `calendar` | Calendar | Google Calendar |
| `comms` | Communications | Slack, email |
| `tasks` | Tasks | ClickUp, Linear |
| `meetings` | Meetings | Fireflies, transcript folder |
| `knowledge` | Knowledge | Drive, vault wiki, Notion export |

**Non-goals:**

- Storing OAuth secrets in `connections.md` (reference env keys only)
- Full connector implementations (those live in Hub / **234** / **279**)
- n8n or second workflow engine

---

## 2. Architecture

```text
connections.md (workspace or vault root)
        |
        v
connections_service.py
  - parse / validate matrix
  - suggest priority order (day 2)
  - score for 274 Connections dimension
        |
        v
/agent-os/connections wizard
        |
        v
Connector catalog links (**234**, **279**)
```

---

## 3. `connections.md` format

```markdown
# Connections

> Tier-1 domains for OS maturity (**274**). Status: planned | configuring | live | n/a

## revenue
- status: planned
- tools: []
- integration_ref: null
- service_account: false

## calendar
- status: live
- tools: [google-workspace]
- integration_ref: google-workspace
- service_account: true
- notes: Uses dedicated workspace bot account
```

Machine-readable mirror: `connections.json` (optional auto-sync on save).

---

## 4. AI service account pattern

Document in `docs/integrations/ai-service-accounts.md`:

- Create dedicated integration user (not personal admin)
- Scope: read vs write per domain
- Rotate credentials; map to Keprix credential store
- Example: ClickUp member "Keprix AI", Google Workspace group account

Wizard step: "Use service account?" with checklist (no auto-provision).

---

## 5. Day-2 wizard

`/agent-os/connections` (Nate day-2 flow):

1. Load `connections.md` or seed from **276** Q5
2. Show tier-1 grid with status chips
3. Suggest top 3 by leverage (tasks + calendar + comms default for solo ops)
4. Per domain: link to connector install (**279**, Hub MCP, manual API key doc)
5. Mark `configuring` -> user confirms -> `live`

Emit `connections.domain_live` event for **274** scorer.

---

## 6. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/agent-os/connections` | Parsed matrix |
| PUT | `/api/agent-os/connections` | Update domain status |
| POST | `/api/agent-os/connections/suggest-priority` | Ranked list |
| POST | `/api/agent-os/connections/init-template` | Write default md+json |

---

## 7. CLI

```bash
keprix agent-os connections init --workspace <id>
keprix agent-os connections show
keprix agent-os connections set tasks --status live --tool clickup
```

---

## 8. Files to create

```
src/keprix/agent_os/
  connections_service.py
  connections_parser.py
  connections_templates.py

src/keprix/api/
  agent_os_connections_routes.py

frontend/src/app/(workspace)/agent-os/connections/page.tsx

docs/integrations/ai-service-accounts.md
docs/features/connections-tier-matrix.md

templates/connections.md.tpl

tests/agent_os/
  test_connections_parser.py
  test_connections_service.py
```

Register **279** google-workspace in suggested tools map.

---

## 9. Acceptance criteria

- `init-template` creates valid `connections.md` with all 7 domains.
- Parser round-trips md -> model -> md without data loss.
- Wizard suggest-priority returns >= 3 domains with rationale strings.
- **274** Connections scorer reads `live` count correctly.
- **265** day-2 step (`l2_connect_one`) auto-completes when first domain goes `live`.
- Service account doc linked from wizard; no secrets in markdown files.
- Tests use fixture `connections.md`.

---

## 10. Dependencies

- **Feeds:** **274**, **276**, **265**
- **Links:** **279**, **234** connector catalog
