# Propreneur agent capability contract (canonical)

**Canonical contract:** `keprix/domain-packs/propreneur/contracts/propreneur-agent-capabilities.v1.json` (v1.3.0)
**Tools twin version:** 1.3.0 (compatible: 1.0.0, 1.1.0, 1.2.0, 1.3.0)

## Authority

This file is the canonical Propreneur agent capability contract. OpenAPI, tool twins, pack nodes, connector route declarations, and coverage matrices are generated or drift-gated from it.

## Version reconciliation

| Axis | Version | Notes |
| --- | --- | --- |
| Agent capabilities (canonical) | 1.3.0 | Source of truth for ops, aliases, pack bindings |
| Tools twin `propreneur-aiva-tools` | 1.3.0 | Generated; keeps compatible_versions ['1.0.0', '1.1.0', '1.2.0', '1.3.0'] |
| OpenAPI `info.version` | 1.2.0 (document) | HTTP detail; drift-gated against canonical HTTP ops |
| Product sidecar pack `contract_version` | 1.0.0 | Pack manifest schema axis; unrelated to tools version |

## Stable operation IDs

Agents and handlers must key on `operation_id` (snake `propreneur_*`). Display titles may change without renumbering IDs.

## Bridge kebab aliases

Kebab bridge tool names remain aliases until the removal window. Agents should prefer stable operation_id / propreneur_* names. After 2026-11-09, kebab names may be removed from discoverable catalogues unless an owner extends the window.

**Removal window:** 2026-11-09

| Alias | Stable operation_id |
| --- | --- |
| `propreneur-get-compliance` | `propreneur_compliance_get` |
| `propreneur-propose-compliance-update` | `propreneur_compliance_propose` |
| `propreneur-get-contacts` | `propreneur_contacts_list` |
| `propreneur-propose-contact` | `propreneur_contacts_propose` |
| `propreneur-get-deals` | `propreneur_deals_list` |
| `propreneur-propose-deal` | `propreneur_deals_propose` |
| `propreneur-get-expenses` | `propreneur_expenses_list` |
| `propreneur-propose-expense` | `propreneur_expenses_propose` |
| `propreneur-propose-financial-log` | `propreneur_finance_log_propose` |
| `propreneur-propose-maintenance` | `propreneur_maintenance_propose` |
| `propreneur-get-maintenance-requests` | `propreneur_maintenance_tickets_list` |
| `propreneur-get-property` | `propreneur_properties_get` |
| `propreneur-get-portfolio` | `propreneur_properties_list` |
| `propreneur-proxy` | `propreneur_proxy` |
| `propreneur-get-rent-payments` | `propreneur_rent_payments_list` |
| `propreneur-propose-setting` | `propreneur_settings_propose` |
| `propreneur-propose-team-invite` | `propreneur_team_invite_propose` |
| `propreneur-open-workspace` | `propreneur_workspace_open` |

## Regeneration

```bash
bash /opt/lampp/htdocs/verlox/keprix/scripts/regen-propreneur-agent-contract.sh
```

CI must fail when generated outputs drift from the committed tree.
