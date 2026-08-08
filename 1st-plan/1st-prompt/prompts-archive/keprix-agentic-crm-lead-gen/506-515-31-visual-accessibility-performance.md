# Prompt 514 / V09: Visual CRM accessibility, responsiveness, and performance

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 506-513
**Blocks:** 515
**Writing style:** plain ASCII only.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Make complex visual CRM surfaces usable with keyboards, screen readers, reduced
motion, smaller screens, large datasets, slow networks, and lower-power devices.

## Must-haves

1. Establish accessibility acceptance against WCAG 2.2 AA for all new routes.
2. Canvas has an equivalent semantic outline: ordered nodes, connections,
   conditions, status, errors, and actions. Nothing requires pointer-only drag.
3. Pipeline provides keyboard card navigation, move dialog, lane headings/counts,
   focus restoration, announcements, and non-colour status labels.
4. Charts provide accessible names, summaries, keyboard data exploration where
   useful, and exact tabular alternatives with matching filters and totals.
5. Animation respects `prefers-reduced-motion`, supports a user override, avoids
   flashing, preserves focus, and never blocks interaction or comprehension.
6. Responsive contracts cover desktop, tablet, and mobile. Dense canvases become
   ordered step views; dashboards prioritise critical cards and filters; side
   inspectors become sheets with reliable back navigation.
7. Define performance budgets for initial JavaScript, route load, interaction,
   graph layout, event latency, chart query, memory, and long-task duration.
8. Lazy-load the graph/chart libraries by route. Avoid shipping them to users
   who only open contacts or settings.
9. Virtualise large boards and lists. Aggregate high-volume workflow runs. Use
   worker-based layout or server layout where graph size would block the UI.
10. Define supported scale targets and degradation: nodes/workflow, cards/lane,
    runs/campaign, events/run, dashboard range, and concurrent live clients.
11. Loading uses cancellable requests and stable skeletons. Errors retain user
    context and offer retry. Offline/stale data is visibly timestamped.
12. Automated and manual tests cover keyboard-only, screen reader smoke, contrast,
    zoom 200/400 percent, reduced motion, touch targets, RTL readiness, slow
    network, large fixtures, and memory/event-stream cleanup.

## Acceptance

- [x] Every visual task has a keyboard and semantic alternative
- [x] Reduced-motion mode communicates identical runtime state
- [x] Visual libraries are route-split and meet agreed performance budgets
- [x] Large datasets degrade to useful aggregation, not browser failure

## Done When

The visual CRM is inclusive and reliable enough for daily operational use.
