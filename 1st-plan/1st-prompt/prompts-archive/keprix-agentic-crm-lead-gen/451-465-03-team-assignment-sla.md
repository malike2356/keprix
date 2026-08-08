# Prompt 453 / N03: Team assignment, SLA inbox, collision prevention

**Status: COMPLETED 2026-08-08**

**Series:** 429-465  
**Depends on:** 431, 432, 448  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- Assignment module already present: teams, round-robin, claim, locks, comments, SLA inbox
- Soft Wall `deal_reassign_paying` for paying/customer deal reassignment
- GUI `/crm/sla` (teams, overdue/due today/unassigned, claim + round-robin)
- Soft lock banner on lead detail open (`CrmSoftLockBanner`)
- API client helpers for teams/assign/locks/comments/SLA
- Tests: `test_453_round_robin_lock_sla`, `test_453_paying_deal_reassign_soft_wall`

## Goal

Team assignment and SLA tooling: ownership, round-robin, inbox, collision prevention, comments.

## Must-haves

1. Fields: `owner_user_id`, `team_id`, `sla_due_at`, `sla_state`.
2. Assignment modes: manual, round-robin, claim-from-queue.
3. Collision prevention: soft lock when operator opens record; warn on concurrent edit.
4. Comments/mentions on Lead/Contact/Deal with notification (in-app + optional Telegram).
5. SLA inbox view: overdue, due today, unassigned.
6. Soft Wall for reassign of deals in `paying`/`customer` if policy on.
7. Tests: round-robin fairness; lock conflict; SLA overdue query.

## Acceptance

- [x] Two operators cannot silently overwrite without warning
- [x] Unassigned queue claim works
- [x] Overdue SLA list accurate

## Done When

Multi-user workspaces can operate CRM without stepping on each other.
