# Capability mesh gap report

Generated: `2026-08-04T11:11:38.050209+00:00`

Soft DoD: only `status=wired` + telegram must have tools in core/`keprix-telegram`.

## Counts

- `exception`: 1
- `partial`: 2
- `ui_only`: 1
- `untracked`: 76
- `wired`: 8

## DoD (wired telegram)

- ok: `True`
- violations: `0`

## Seed graph nodes

`calendar`, `chat`, `companies-house`, `contacts`, `cron`, `domain-pack-research-intel`, `domain-pack-scheduling-ops`, `home`, `leads`, `memory`, `playbooks`, `vault`, `vical`

## Nav rows (graph-tracked + untracked sample)

| nav_id | status | telegram | tools_in_telegram | tools |
| --- | --- | --- | --- | --- |
| `home` | `ui_only` | False | None | - |
| `chat` | `partial` | True | None | - |
| `sessions` | `untracked` | False | None | - |
| `voice` | `untracked` | False | None | - |
| `tasks` | `untracked` | False | None | - |
| `calendar` | `wired` | True | True | calendar_list_events |
| `vical` | `wired` | True | True | vical_offer_slots, vical_create_booking, vica... |
| `notes` | `untracked` | False | None | - |
| `email` | `untracked` | False | None | - |
| `notifications` | `untracked` | False | None | - |
| `contacts` | `wired` | True | True | contacts_search, contacts_get |
| `leads` | `wired` | True | True | create_lead, list_leads, link_booking_to_lead |
| `tenants` | `untracked` | False | None | - |
| `documents` | `untracked` | False | None | - |
| `files` | `untracked` | False | None | - |
| `gallery` | `untracked` | False | None | - |
| `memory` | `wired` | True | True | memory |
| `memory-galaxy` | `untracked` | False | None | - |
| `brain` | `untracked` | False | None | - |
| `tools` | `untracked` | False | None | - |
| `workspace-new` | `untracked` | False | None | - |
| `brain-graph` | `untracked` | False | None | - |
| `brain-health` | `untracked` | False | None | - |
| `graphiti` | `untracked` | False | None | - |
| `rag-pipeline` | `untracked` | False | None | - |
| `playbook` | `untracked` | False | None | - |
| `video-ingest` | `untracked` | False | None | - |
| `analytics` | `untracked` | False | None | - |
| `usage` | `untracked` | False | None | - |
| `observability` | `untracked` | False | None | - |
| `research` | `untracked` | False | None | - |
| `companies-house` | `wired` | True | True | search:companies_house, get:company_profile |
| `opportunities` | `untracked` | False | None | - |
| `compare` | `untracked` | False | None | - |
| `hub` | `untracked` | False | None | - |
| `agent-apps` | `untracked` | False | None | - |
| `skills` | `untracked` | False | None | - |
| `domain-packs` | `wired` | False | True | create_lead, list_leads |
| `builder` | `untracked` | False | None | - |
| `design-preview` | `untracked` | False | None | - |
| `channels` | `untracked` | False | None | - |
| `messaging-settings` | `untracked` | False | None | - |
| `voice-wake` | `untracked` | False | None | - |
| `migrate` | `untracked` | False | None | - |
| `control-center` | `untracked` | False | None | - |
| `agent-os-glass` | `untracked` | False | None | - |
| `agent-studio` | `untracked` | False | None | - |
| `agent-teams` | `untracked` | False | None | - |
| `agent-runtime` | `untracked` | False | None | - |
| `a2a` | `untracked` | False | None | - |
| `playbooks` | `partial` | True | None | - |
| `playbook-triggers` | `untracked` | False | None | - |
| `integrations` | `untracked` | False | None | - |
| `cron` | `wired` | True | True | cronjob |
| `mcp` | `untracked` | False | None | - |
| `browser-adoption` | `untracked` | False | None | - |
| `coding-adoption` | `untracked` | False | None | - |
| `ponytail-ladder` | `untracked` | False | None | - |
| `tools-adoption` | `untracked` | False | None | - |
| `analytics-adoption` | `untracked` | False | None | - |
| `evals` | `untracked` | False | None | - |
| `vault` | `exception` | False | None | - |
| `vault-setup` | `untracked` | False | None | - |
| `knowledge-vault-settings` | `untracked` | False | None | - |
| `review-gateway` | `untracked` | False | None | - |
| `channel-shield` | `untracked` | False | None | - |
| `scout-warden` | `untracked` | False | None | - |
| `dsar` | `untracked` | False | None | - |
| `operator-copilot` | `untracked` | False | None | - |
| `support` | `untracked` | False | None | - |
| `settings` | `untracked` | False | None | - |
| `dashboard` | `untracked` | False | None | - |
| `admin` | `untracked` | False | None | - |
| `users` | `untracked` | False | None | - |
| `billing` | `untracked` | False | None | - |
| `modules` | `untracked` | False | None | - |
| `upgrade` | `untracked` | False | None | - |
| `feature-flags` | `untracked` | False | None | - |
| `admin-quotas` | `untracked` | False | None | - |
| `admin-tool-acl` | `untracked` | False | None | - |
| `admin-network-egress` | `untracked` | False | None | - |
| `admin-isolation-audit` | `untracked` | False | None | - |
| `admin-upstream` | `untracked` | False | None | - |
| `backup` | `untracked` | False | None | - |
| `readiness` | `untracked` | False | None | - |
| `self-knowledge` | `untracked` | False | None | - |
| `module-inventory` | `untracked` | False | None | - |
| `developer` | `untracked` | False | None | - |

## Regenerate

```bash
cd keprix && PYTHONPATH=src python3 -m keprix.capability_mesh audit --write
```
