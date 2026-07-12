# Agent brief: Agent OS UI polish (Prompts 301-315)

## Status: DONE (2026-07-12)

## Goal

Wire Prompt 270 backends into product UI with least thrash. Reuse shared UI components. Do not invent a parallel Agent OS design system.

## Read first

- `1st-plan/1st-prompt/reference/301-agent-os-ui-polish-master-reference.md`
- `1st-plan/1st-prompt/reference/301-agent-os-ui-polish-build-order.md`
- Archived prompts: `prompts-archive/completed/301-*.md` through `315-*.md`

## Shipped

1. 301 hub + subnav (`AgentOsSubnav`, glass as home)
2. 302 milestones on onboarding (`MilestonesPanel`)
3. 303 Ship defaults on glass (`ShipDefaultsPanel`)
4. 304 nav fallback sync + `dashboard` icon
5. 305 glass period selector
6. 306 onboard vs onboarding IA
7. 307 shared Empty/Error/skeletons on maturity/connections/glass/galaxy
8. 308 breadcrumbs to `/agent-os/glass`
9. 309 Memory Galaxy Brain tabs + node click drawer
10. 310 glass Tasks links + workflow boards
11. 311 action board header deep links
12. 312 frosted glass panels (MUI tokens)
13. 313 force-directed galaxy layout toggle
14. 314 usage ↔ glass `?days=` sync
15. 315 api.md + feature docs

## Validation sketch

```bash
cd /opt/lampp/htdocs/verlox/keprix
PYTHONPATH=src .venv/bin/python -m pytest tests/agent_os/ -q --tb=line
```

Manual: open `/agent-os/glass`, `/agent-os/onboarding`, `/memory/galaxy`, `/usage`; confirm subnav, milestones, Ship defaults, period control, galaxy node click.
