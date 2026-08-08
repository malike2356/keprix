# Keprix - Prompt 236: Scout Publish Pipeline and Run Telemetry Bridge

**Series:** KNIME adoption pack **233-238**  
**Principle:** KNIME Server governs **deploy and monitor**; Keprix delegates governance to **Scout** without duplicating playbook execution in Scout.

**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`  
**Carina consumer:** `knime-adoption--03-scout-agent-lifecycle.md`

---

## 1. What this prompt builds

Keprix-side **publish versioning** and **run telemetry export** so Scout console can implement deploy/monitor/drift/retrain (Carina prompt 03). This prompt does not build Scout UI; it emits structured events Scout ingests.

| Component | Role |
| --- | --- |
| Playbook version store | Hash + metadata on each publish |
| Publish API | Personal + org scope (235) |
| Scout webhook client | POST events when `LABYRINTH_ENABLED` |
| Run telemetry enricher | Attach playbook_id, version_hash, cost, duration to run completion |

---

## 2. KNIME lifecycle reference (read only)

| KNIME Server | Keprix + Scout |
| --- | --- |
| Deploy workflow to server | Publish playbook version + optional Scout approval |
| Job monitor | Scout dashboard from `playbook_run_completed` events |
| Model validation | Drift eval on output samples (Scout 03) |
| Retrain trigger | Scout action webhook (Scout 03) |

Mirror: no Java port. Read `knime-visual-workflow-adoption.md` lifecycle table.

---

## 3. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Studio save | Prompt **233** `studio_store.py` |
| Publish stub | Prompt **233** `POST .../publish` returns hash only |
| Scout extension | `src/keprix/extensions/scout/` |
| Scout policy bridge | `extensions/scout/persona/policy_bridge.py` |
| Edition org publish gate | Prompt **235** |
| Connector audit metadata | Prompt **234** `connector_audit.py` |
| Playbook run events | `run_routes.py`, timeline events |

---

## 4. Playbook versioning

Create `src/keprix/playbook/version_store.py`:

```python
@dataclass
class PlaybookVersion:
    playbook_id: str
    version_hash: str          # sha256 canonical yaml
    published_at: str          # ISO8601
    publisher_user_id: str
    scope: Literal["personal", "org"]
    status: Literal["draft", "pending_approval", "published", "rejected"]
    note: str = ""
    canvas_schema_version: int = 1

class PlaybookVersionStore:
    def record_publish(self, ...) -> PlaybookVersion: ...
    def list_versions(self, playbook_id: str) -> list[PlaybookVersion]: ...
    def get_current(self, playbook_id: str, *, scope: str) -> PlaybookVersion | None: ...
```

Storage: `~/.keprix/playbooks/{id}/versions/{hash}.json` + `current.json` pointer.

Canonical hash: YAML dump with sorted keys, UTF-8, SHA256 hex.

---

## 5. Publish flow

Extend `src/keprix/playbook/studio_routes.py`:

```
POST /api/playbooks/studio/{id}/publish
Body: { scope?: "personal"|"org", note?: string, require_scout_approval?: bool }
```

### 5.1 Algorithm

1. Load latest YAML from store; compile via `compile_playbook_document` (fail 422 if invalid)
2. Compute `version_hash`
3. If `scope=org` and community edition -> 403 (235)
4. If Scout enabled and (org scope OR `require_scout_approval`):
   - status = `pending_approval`
   - emit `playbook_publish_requested`
5. Else:
   - status = `published`
   - emit `playbook_published`
6. Write version record; update `current.json`

Response:

```json
{
  "playbook_id": "aiva-deal-analyse",
  "version_hash": "abc123...",
  "status": "pending_approval",
  "scout_event_id": "evt_..."
}
```

---

## 6. Scout webhook client

Create `src/keprix/integrations/scout_lifecycle_client.py`:

```python
async def emit_scout_lifecycle_event(
    event_type: str,
    payload: dict,
    *,
    workspace_id: str,
) -> str | None:
    """POST to Scout when LABYRINTH_ENABLED; no-op otherwise."""
```

### 6.1 Event types (v1)

| event_type | When | Payload fields |
| --- | --- | --- |
| `playbook_publish_requested` | Publish pending approval | playbook_id, version_hash, publisher, tenant, scope, yaml_preview_first_500_chars |
| `playbook_published` | Approved or auto-published | playbook_id, version_hash, approved_by, scope |
| `playbook_publish_rejected` | Scout reject callback | playbook_id, version_hash, reason |
| `playbook_run_completed` | Run terminal state | playbook_id, run_id, version_hash, status, duration_ms, cost_usd, step_count, connector_ids_used |
| `playbook_drift_sample` | Optional hook after agent_task | playbook_id, run_id, step_id, output_hash, eval_score |

Config (existing Scout env pattern):

- `LABYRINTH_ENABLED=1`
- `LABYRINTH_SCOUT_WEBHOOK_URL` or reuse Scout API base from `extensions/scout/manifest.py`
- `LABYRINTH_SCOUT_API_KEY`

Never block playbook run if Scout webhook fails; log warning + retry queue (in-memory v1 ok).

### 6.2 Inbound callback (optional v1)

```
POST /api/scout/callbacks/playbook-publish
Body: { playbook_id, version_hash, decision: "approve"|"reject", reason? }
```

Auth: shared secret header `X-Scout-Callback-Secret`. Updates version status; emits `playbook_published` or `playbook_publish_rejected`.

---

## 7. Run telemetry enricher

Create `src/keprix/playbook/run_telemetry.py`:

```python
def enrich_run_completion(
    run: PlaybookRun,
    *,
    playbook_id: str | None,
    version_hash: str | None,
) -> dict:
    """Build scout payload from run record + events."""
```

Wire in run completion path (`runtime/runner.py` or `run_routes.py`):

1. On terminal status (completed, failed, cancelled), call enricher
2. Emit `playbook_run_completed` via scout_lifecycle_client
3. Include aggregated `connector_ids_used` from step configs (234)

Cost estimate: use existing token/cost fields from agent_task steps if present; else null.

Duration: `completed_at - started_at` in ms.

---

## 8. Studio UI updates

In `StudioToolbar.tsx`:

| Control | Behavior |
| --- | --- |
| Publish button | Opens dialog: scope (personal/org), note, checkbox "Require Scout approval" (if Scout enabled) |
| Version history | Side panel lists past hashes + status (read from `GET /api/playbooks/studio/{id}/versions`) |

Add route:

```
GET /api/playbooks/studio/{id}/versions
```

---

## 9. Tests

`tests/playbook/test_version_store.py` - hash stability, list versions  
`tests/integrations/test_scout_lifecycle_client.py` - mock HTTP, disabled when LABYRINTH off  
`tests/playbook/test_publish_flow.py` - pending vs published, org 403 in community

Fixtures: minimal 2-node YAML; assert same hash across key order permutations.

---

## 10. Documentation

Add section to `docs/features/playbooks.md`: **Publishing and Scout governance**  
Add `docs/integrations/scout-lifecycle-events.md` with event schema for Scout team.

Cross-link Carina `knime-adoption--03`.

---

## 11. Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Publish computes stable version_hash |
| 2 | Personal publish auto-publishes without Scout when disabled |
| 3 | Scout enabled + org scope -> pending + `playbook_publish_requested` emitted |
| 4 | Callback approve -> published status |
| 5 | Run completion emits `playbook_run_completed` with duration |
| 6 | Scout webhook failure does not fail playbook run |
| 7 | Org publish 403 in community edition (235) |
| 8 | pytest suite passes |
| 9 | No playbook execution code added under Scout |

---

## 12. Out of scope

| Item | Owner |
| --- | --- |
| Scout dashboard UI | `knime-adoption--03` |
| Drift eval algorithm | Scout 03 |
| GPU retrain | Never in v1 |

---

## 13. Archive

`prompts-archive/236-scout-publish-telemetry-bridge.md` when AC pass.
