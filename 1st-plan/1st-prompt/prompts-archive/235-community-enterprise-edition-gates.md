# Keprix - Prompt 235: Community vs Enterprise Edition Gates

**Series:** KNIME adoption pack **233-238**  
**Principle:** KNIME gives the **visual editor away**; charges for **governance, fleet, and deployment**. Match that split: **never paywall Visual Playbook Studio**.

**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

A single **edition model** (`community` | `enterprise`) enforced server-side and reflected in UI. Operators always get studio, YAML playbooks, local/TUI agent, and basic MCP in Community Edition.

---

## 2. KNIME business model reference (read only)

| KNIME free | KNIME paid |
| --- | --- |
| Analytics Platform desktop | Server / Business Hub |
| Visual editor, local execution | Team deploy, scheduling, governance |
| Community extensions | Admin, SSO, audit |

Keprix mapping:

| Community (MIT self-host) | Enterprise |
| --- | --- |
| Visual Playbook Studio | Fleet multi-node deploy |
| YAML + canvas authoring | SSO (OIDC/SAML) |
| Local agent + TUI | Audit log export |
| Basic MCP install | Scout fleet dashboard |
| Personal playbooks | Org-wide playbook publish |
| Connector self-install | Connector install governance |

---

## 3. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| SSO / account security | Prompts 214-219 |
| Scout extension | `src/keprix/extensions/scout/` |
| Hub entitlements | Prompt 184 |
| Fleet-ish deploy docs | `docs/deploy/` |
| Studio (233) | `/playbooks/studio` |
| Connector catalog (234) | `/integrations` |

---

## 4. Edition model

Create `src/keprix/licensing/__init__.py` and `src/keprix/licensing/edition.py`:

```python
from typing import Literal

Edition = Literal["community", "enterprise"]

FEATURE_MATRIX: dict[str, dict[Edition, bool]] = { ... }

def current_edition() -> Edition: ...
def feature_enabled(feature: str) -> bool: ...
def require_enterprise(feature: str) -> None:  # raises HTTPException 403
```

### 4.1 Feature keys (v1)

| Feature key | Community | Enterprise |
| --- | --- | --- |
| `visual_studio` | yes | yes |
| `yaml_playbooks` | yes | yes |
| `local_agent` | yes | yes |
| `basic_mcp` | yes | yes |
| `fleet_deploy` | no | yes |
| `sso` | no | yes |
| `audit_export` | no | yes |
| `scout_fleet_dashboard` | no | yes |
| `connector_governance` | no | yes |
| `org_playbook_publish` | no | yes |
| `shared_template_library` | no | yes |

### 4.2 Resolution order

1. Env `KEPRIX_EDITION=community|enterprise` (default `community`)
2. Optional file `~/.keprix/license.json` stub:

```json
{ "edition": "enterprise", "license_id": "ee-demo-001", "expires_at": null }
```

3. No vendor SDK in v1; file is trust-on-self-host (honest docs)

Log edition at startup once (info level).

---

## 5. Server enforcement

Create `src/keprix/licensing/dependencies.py`:

```python
def enterprise_feature(feature: str):
    """FastAPI dependency factory."""

def get_edition_info() -> dict:
    """Return { edition, features: { key: bool } } for UI."""
```

Add route `GET /api/licensing/edition` (session auth optional; public ok).

### 5.1 Routes to gate (minimum set)

Audit codebase for fleet/SSO/audit routes from prompts 214-219. Apply `@Depends(enterprise_feature("..."))`:

| Feature key | Example routes |
| --- | --- |
| `fleet_deploy` | Fleet admin API routes if present |
| `audit_export` | Audit export download endpoints |
| `connector_governance` | `POST /api/integrations/governance/approve` (new stub) |
| `org_playbook_publish` | `POST /api/playbooks/studio/{id}/publish?scope=org` |

**Must NOT gate:**

- All `/api/playbooks/studio/*` routes
- `POST /api/playbook-runs/start`
- `GET /api/integrations/catalog`
- Local save to `~/.keprix/playbooks/`

Return **403**:

```json
{ "detail": "enterprise_required", "feature": "fleet_deploy" }
```

---

## 6. Connector governance extension (enterprise)

Add to prompt 234 install flow when `connector_governance` enabled:

Create `src/keprix/integrations/governance_routes.py`:

| Route | Behavior |
| --- | --- |
| POST `/api/integrations/governance/request` | User requests install; status pending |
| POST `/api/integrations/governance/approve` | Admin approves (enterprise) |
| GET `/api/integrations/governance/pending` | Admin queue |

Community: install proceeds immediately (current 234 behavior).

---

## 7. Org playbook publish (enterprise)

Extend studio publish (233/236):

| Scope | Edition |
| --- | --- |
| `personal` | community + enterprise |
| `org` | enterprise only |

Personal publish writes to `~/.keprix/playbooks/`. Org publish writes to `~/.keprix/org/playbooks/` (create dir) and triggers Scout approval (236).

---

## 8. Frontend

Create `frontend/src/lib/edition.ts`:

```typescript
export type Edition = "community" | "enterprise";
export async function fetchEdition(): Promise<EditionInfo>;
export function isFeatureEnabled(feature: string): boolean;
```

### 8.1 UI surfaces

| Location | Behavior |
| --- | --- |
| Settings footer | Badge: Community Edition / Enterprise Edition |
| Fleet nav items | Hidden or disabled with tooltip in community |
| SSO settings | Enterprise only |
| Studio Publish dropdown | Org scope disabled in community |
| Integrations install | Show "Requires admin approval" when governance on |

Use MUI `Tooltip`: "Available in Enterprise Edition. See docs."

---

## 9. Tests

`tests/licensing/test_edition_gates.py`:

| Test | Assert |
| --- | --- |
| `test_default_community` | |
| `test_studio_allowed_community` | compile + save 200 |
| `test_fleet_blocked_community` | 403 |
| `test_enterprise_unlocks` | env EE -> fleet 200 |
| `test_edition_endpoint` | returns matrix |

---

## 10. Documentation

Create `docs/editions/community-vs-enterprise.md`:

- KNIME-style rationale (free canvas, paid governance)
- Feature matrix matching code
- Self-host CE vs managed EE
- Scout as optional governance connector
- Explicit: **Visual Playbook Studio is free forever in CE**

Update:

- `docs/features/playbooks.md`
- Marketing FAQ if present under `docs/marketing/`

---

## 11. Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `current_edition()` defaults to `community` |
| 2 | All studio routes work in community |
| 3 | At least one fleet/audit route returns 403 in community |
| 4 | `KEPRIX_EDITION=enterprise` unlocks gated routes |
| 5 | `/api/licensing/edition` matches docs matrix |
| 6 | No paywall on `/playbooks/studio` |
| 7 | Org publish returns 403 in community |
| 8 | `pytest tests/licensing/test_edition_gates.py` passes |
| 9 | UI badge visible in settings |

---

## 12. Out of scope

| Item | Notes |
| --- | --- |
| License key vendor (FlexNet etc.) | Stub file only |
| Usage metering / seats | Aiva billing separate |
| Carina cloud edition | Carina docs |
| Stripe EE checkout | GTM later |

---

## 13. Archive

`prompts-archive/235-community-enterprise-edition-gates.md` when AC pass.
