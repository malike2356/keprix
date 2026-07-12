# Agent OS Phase 3 glass + Memory Galaxy

## Surfaces

| Surface | Path |
| --- | --- |
| Agent OS glass | `/agent-os/glass` · `GET /api/agent-os/glass?days=` |
| Memory Galaxy | `/memory/galaxy` · `GET /api/vault/graph` |
| Tokens by agent | `/usage?days=` (By agent chart) · `GET /api/usage/breakdown/agent` |
| Activation checklist | `/agent-os/onboarding` · milestones + steps |
| Action board | `/agent-os` |

Glass is the Agent OS hub home. Period control uses the same `days` values as Usage (7 / 30 / 90) and syncs via `?days=` plus localStorage.

Memory Galaxy shows Brain section tabs (Graph / Galaxy / List / Health). Click a node to open the vault note in a drawer. Layout toggle: Circle or Force (Brain force layout).

## Channels

Discord and Slack adapters already ship with Keprix. Configure them under `/dashboard/channels`.

## Agent token metadata

Usage events group by `metadata.agent_id`, then `metadata.agent`, then `metadata.app_name`, then channel.
