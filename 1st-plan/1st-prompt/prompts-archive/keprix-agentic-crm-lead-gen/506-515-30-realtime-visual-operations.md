# Prompt 513 / V08: Real-time visual operations, alerts, and collaboration

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 446, 507, 509, 511, 512
**Blocks:** 515
**Writing style:** plain ASCII only.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Keep pipeline, workflow runs, approvals, replies, and dashboards current while
giving teams a controlled visual operations centre across web and Telegram.

## Must-haves

1. Define workspace-scoped real-time topics for pipeline changes, run events,
   approvals, replies, human tasks, adapter health, budgets, and kill switches.
2. Authenticate subscriptions and re-authorise each topic. Reconnect from cursor,
   dedupe events, recover from missed windows with snapshot refresh, and apply
   backpressure for high-volume campaigns.
3. Presence and record ownership are advisory. Concurrent editing still uses
   durable version checks. Show who is viewing/editing without leaking identity.
4. Operations centre panels: active runs, waiting approvals, human takeover,
   overdue tasks, new replies, failed nodes, provider health, spend/budget,
   deliverability guardrails, and recently activated kill switches.
5. Alert rules support severity, threshold, window, cooldown, owner, escalation,
   acknowledgement, resolution note, and web/Telegram delivery.
6. Default high-severity alerts: complaint spike, hard-bounce spike, duplicate-send
   risk, suppression failure, sender-domain failure, budget breach, cross-workspace
   denial anomaly, stuck approval, dead-letter growth, and adapter policy block.
7. Clicking an alert opens the relevant filtered dashboard, run node, campaign,
   approval, or records. Acknowledgement never dismisses the underlying problem.
8. Telegram cards use signed, expiring, single-use actions for approve, reject,
   pause, cancel, assign, and open-in-web. Sensitive detail stays in authenticated web.
9. Notification preferences include channel, severity, digest/immediate, quiet
   hours, and role. Mandatory safety alerts cannot be silently disabled by users
   without the required administrator policy.
10. Provide comments, assignment, and resolution notes on approvals, failures,
    and human tasks with audit history and optional mentions.
11. Real-time failure degrades to visible polling with last-updated time. It must
    not freeze a stale dashboard while appearing live.
12. Load and isolation tests cover many runs, slow clients, reconnect storms,
    event ordering, cursor expiry, unauthorised topics, and Telegram replay.

## Acceptance

- [x] Visual state converges after disconnect without duplicated transitions
- [x] Safety alerts link to evidence and an authorised corrective action
- [x] Telegram actions are scoped, expiring, single-use, and audited
- [x] Real-time outage has an honest polling fallback

## Done When

Teams can supervise automation visually without watching every record manually.
