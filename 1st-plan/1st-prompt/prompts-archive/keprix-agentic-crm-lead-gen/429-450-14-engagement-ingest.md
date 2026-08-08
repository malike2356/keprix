# Prompt 443 / 14: Engagement ingest (email replies + Telegram)

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 442  
**Blocks:** 444, 447  
**Writing style:** plain ASCII only.

## What was built

- Implemented in crm/ Soft Wall glue + UI + tests (442-448 wave)

## Goal

Collect responses when leads engage; write Activities; update stages.

## Must-haves

1. Hook Soft Wall reply classify into CRM Activity + stage suggestions.
2. Inbound email webhook/IMAP path already in Soft Wall: ensure CRM id resolution.
3. Telegram: if lead has telegram handle and messages in operator chat tagged to lead, log activity (best-effort).
4. Engagement types: replied, interested, not_interested, bounce, unsubscribe, booked_intent.
5. Soft Wall for auto stage change when confidence low; auto-apply when high and policy allows.
6. Suppression on unsubscribe/bounce.
7. Tests for classify -> activity -> stage.
8. Verify webhook signatures, dedupe provider event ids, preserve immutable raw
   metadata, and keep mutable classification/model/version separate.
9. Reply, complaint, unsubscribe, bounce, or human takeover pauses pending sends
   before classification. Auto-replies and out-of-office messages do not promote stages.
10. Low confidence, legal language, negotiation, complaints, regulated advice,
    and ambiguous intent route to an assigned human queue with SLA.
11. **GUI:** `/crm/inbox` (466) with tabs for replies, Soft Wall stage
    suggestions, takeover, complaints. Claim/assign/pause/resume from UI.
    Telegram-only digest is not sufficient for Must.

## Acceptance

- [x] Reply "interested" moves toward engaged/qualified per policy
- [x] Unsubscribe adds SuppressionEntry and stops enroll sends
- [x] Activity visible on CRM detail timeline
- [x] Operator can claim takeover items from `/crm/inbox` without Telegram

## Done When

444 can nurture based on real engagement.
