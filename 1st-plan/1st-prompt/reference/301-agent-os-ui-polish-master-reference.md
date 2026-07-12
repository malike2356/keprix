# Agent OS UI polish master reference (Keprix 301-315)

## Problem

Prompt 270 shipped Agent OS backends (glass, galaxy, usage-by-agent, milestones, Phase 5 playbook/guardrails/error-paste). The web UI is thin and scattered: ~12 flat Automations nav items, milestones not rendered, Phase 5 CLI-only, twin onboard routes, breadcrumb/nav drift.

## Goal

Best polish for least thrash: wire existing APIs into product UI, collapse IA, reuse shared components. No new parallel stacks.

## Already exists (do not rebuild)

| Capability | Backend / path |
| --- | --- |
| Glass dashboard | `GET /api/agent-os/glass`, `frontend/.../agent-os/glass/page.tsx` |
| Memory Galaxy | `GET /api/vault/graph`, `frontend/.../memory/galaxy/`, `MemoryGalaxyCanvas.tsx` |
| Usage by agent | `GET /api/usage/breakdown/agent`, `/usage` |
| Milestones | `GET /api/agent-os/milestones` (also embedded in onboarding payload) |
| Token playbook | `GET /api/agent-os/token-playbook` |
| Guardrails | `GET /api/agent-os/guardrails`, `POST .../backup-vault` |
| Error paste | `POST /api/agent-os/error-paste` |
| Nav contract | `src/keprix/ui_contract/navigation.py` |
| Shared UI | `frontend/src/components/ui/{PageHeader,EmptyState,ErrorState,AsyncView,...}` |
| Brain layouts | `frontend/src/lib/brain/layout-registry.ts` (force layout for 313) |
| Usage period toolbar | usage page components (reuse for 305/314) |

## Design rules

1. Reuse `frontend/src/components/ui/*` and existing usage/memory patterns.
2. Do not build a parallel Agent OS chrome or second token set.
3. Prefer contract-first nav (`/api/ui/contract`); keep frontend fallback in sync.
4. Glass product name means dashboard of agents/memory/tasks/tokens; frosted CSS (312) is optional and must use existing MUI CSS vars.
5. Writing style: no em dashes, no en dashes, no emojis.

## Surfaces to touch

| Route | Role after polish |
| --- | --- |
| `/agent-os` | Hub shell + Action Board (subnav host) |
| `/agent-os/glass` | Primary Agent OS home / glass |
| `/agent-os/onboarding` | Activation checklist + Day 1/7/30 milestones |
| `/agent-os/onboard` | Interview skill (clearly labeled) |
| `/memory/galaxy` | Galaxy with Brain tabs + note open |
| `/usage` | Period sync with glass |
| Automations nav | Hub entry + fewer flat siblings |

## Out of scope

- New Agent OS APIs (unless a tiny BFF field is required)
- Redesigning the whole Automations group from scratch
- Replacing Brain with Galaxy as the only graph
- VPS/deploy work (already shipped separately)

## Build order

See `301-agent-os-ui-polish-build-order.md`.
