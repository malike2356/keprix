# Approvals, publishing, Scout, kill switch

## Approvals

Preview includes content/media hashes, channel, audience, persona version,
disclosure, links, cost and factual sources. Any material edit invalidates
approval. Expired approval cannot publish.

## Publishing

Transactional outbox with idempotency keys. Retry cannot double-post.
`private_reply_send` is draft-only unless a narrow policy allows send, and
always requires owner review.

## Scout

Events for generation, policy, approval, publish, provider and deletion with
hashes and redacted metadata (no tokens/secrets).

## Kill switch

Blocks queued publish and media jobs immediately.

## Watermark

Removal of watermark/disclosure requires an explicit later policy, not Phase 1-4.
