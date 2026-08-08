# Prompt XCS-04: Xeclone approvals, publishing, channels, and Scout governance

**Status: COMPLETED 2026-08-08**
**Depends on:** XCS-01, XCS-02
**Blocks:** XCS-05

## Goal

Run useful iLaud workflows while keeping public and private representation under
owner control, channel rules and an immediate kill switch.

## Must-haves

1. Workflows: post ideation-to-approval, scheduled post, inbound reply draft,
   weekly digest, voice note, likeness image, talking-head package, repurpose and
   performance-informed revision.
2. Approval preview includes content/media, channel/account, audience, time,
   persona version, factual sources, disclosure, links, cost and exact hashes.
3. Any edit to content, media, channel, audience, schedule, disclosure or link
   invalidates approval. Expired approval cannot publish.
4. Private messages remain draft-only until a separately signed policy allows a
   narrow class. Never conceal that an AI handled a conversation where disclosure
   or owner policy requires it.
5. Scout receives generation, policy, approval, publish, provider and deletion
   events with hashes and redacted metadata; kill switch blocks queued actions.
6. Channel connectors follow official APIs and terms, rate limits and webhook
   verification. No browser-login scraping or personal account automation.
7. Claims, promises, sensitive relationships, financial/legal statements,
   controversy and identity/security requests route to owner review.
8. Publishing uses transactional outbox/idempotency and reconciles provider event
   ids. Retry cannot double-post or double-message.
9. Watermark/disclosure removal requires an explicit later policy, not Phase 1-4.

## Acceptance

- [ ] Approved fixture publishes once with complete audit correlation
- [ ] Kill switch stops queued publish and media jobs
- [ ] Material edit invalidates approval
- [ ] High-risk/private reply is owner-reviewed

## What was built

- Approval hash invalidation, outbox publish once, Scout events, kill switch

