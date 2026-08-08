# Agent OS UI polish build order (Keprix 301-315)

**Master reference:** `301-agent-os-ui-polish-master-reference.md`  
**Depends on:** Prompt 270 Phases 1-5 (backends shipped); Agentic OS 256-265 UI shells  
**Constraint:** Reuse `frontend/src/components/ui/*` and existing usage/memory patterns. Do not invent a parallel Agent OS design system.

---

## Critical path

```text
301 hub+subnav ----+
                   |
302 milestones ----+--> 303 ship defaults on glass
                   |
304 nav sync ------+
                   |
305 glass period --+--> 314 usage↔glass sync (nice)
                   |
306 onboard unify -+

307 shared states / 308 breadcrumbs  (parallel polish)
309 galaxy UX / 310 glass tasks / 311 action board links (parallel)
312 frosted glass / 313 force galaxy / 315 api docs (nice, last)
```

---

## Prompt order

| Order | Prompt | Title | Effort | Depends on | Parallel OK? |
| --- | --- | --- | --- | --- | --- |
| 1 | **301** | Agent OS hub + subnav | M | existing `/agent-os*` routes | - |
| 2 | **302** | Day 1/7/30 milestones on onboarding | L | `GET /api/agent-os/milestones` | Yes with 304 |
| 3 | **303** | Phase 5 Ship defaults panel on glass | M | 301 (glass as home), Phase 5 APIs | After 301 |
| 4 | **304** | Sync frontend nav fallback with NAV_ITEMS | L | backend `navigation.py` | Yes with 302 |
| 5 | **305** | Glass period selector | L | glass API `days` | Yes with 303 |
| 6 | **306** | Unify onboard vs onboarding IA | L | 301 subnav | After 301 |
| 7 | **307** | Shared PageHeader / Empty / Error / skeletons | M | ui components | Parallel |
| 8 | **308** | Fix Agent OS breadcrumbs | L | 301 | After 301 |
| 9 | **309** | Memory Galaxy Brain tabs + node click | M | `/memory/galaxy`, Brain patterns | Parallel |
| 10 | **310** | Glass Tasks links + workflow boards | L | glass payload | After 303 optional |
| 11 | **311** | Action board header deep links | L | `/agent-os` board | After 301 |
| 12 | **312** | Subtle frosted glass treatment | M | MUI tokens only | Nice |
| 13 | **313** | Force-directed galaxy layout | M | Brain layout registry | Nice |
| 14 | **314** | Usage ↔ glass period query sync | L | 305 | Nice after 305 |
| 15 | **315** | Docs: glass / milestones / phase5 APIs | L | APIs exist | Anytime |

---

## Minimum viable demo

Ship **301 + 302 + 303 + 304 + 305 + 306**:

1. Open Automations: Agent OS hub with subnav (Glass, Board, Onboarding, Memory, Usage).
2. Onboarding shows Day 1 / 7 / 30 milestone cards from the API.
3. Glass shows Ship defaults: playbook, guardrails + backup, error-paste box.
4. Frontend fallback nav includes glass + galaxy even if contract is stale.
5. Glass period control changes `days`; tokens refresh.
6. `/agent-os/onboard` and `/agent-os/onboarding` are clearly labeled (tabs or headers).

Then polish pack **307-311**, then nice **312-315**.

---

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
