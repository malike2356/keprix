# Prompt XCS-01: Xeclone pack and multimodal capability nodes

**Status: COMPLETED 2026-08-08**
**Depends on:** XCS-00
**Blocks:** XCS-02, XCS-04

## Goal

Build `domain-packs/xeclone/` for iLaud with consent-aware text, audio, image and
video nodes, separate generation from distribution, and disclose live/stub status.

## Must-haves

1. Pack manifest, persona binding, schemas, consent policies, content safety,
   RAG sources, provider routes, playbooks, media jobs and evaluation fixtures.
2. Text nodes: `persona_chat`, `post_draft`, `reply_draft`, `email_draft`,
   `content_repurpose`, `digest`, `decision_style_explain`, `fact_retrieve`.
3. Audio nodes: `speech_transcribe`, `voice_note_draft`, `voice_synthesise`.
   Image nodes: `image_brief`, `likeness_image_generate`. Video nodes:
   `talking_head_script`, `talking_head_generate`, `caption_and_package`.
4. Distribution actions are separate: `approval_submit`, `content_schedule`,
   `channel_publish`, `private_reply_send`. They require product-held OAuth,
   exact approval, idempotency and channel policy.
5. Node checks consent scope, asset provenance, persona version, channel, audience,
   disclosure, watermark, provider transfer, cost and approval before execution.
6. No generic face-swap, voice-clone-anyone, upload-arbitrary-person, remove-
   watermark, credential-read or unrestricted publish node.
7. RAG responses separate owner's stated facts, private correspondence, inferred
   preferences and generated style. Relationship/private data is excluded from
   public drafts unless specifically approved.
8. Media outputs carry job/model/version, source-consent ids, hashes, prompt
   template, disclosure/watermark state and storage expiry.
9. Deterministic fallback produces text-only drafts when media providers fail.

## Acceptance

- [ ] Capability discovery labels risk, provider and consent requirements
- [ ] Revoked asset consent blocks generation and future indexing
- [ ] Generation cannot call distribution implicitly
- [ ] Another person's media cannot be used as owner identity input

## What was built

- 20 capability nodes (text/audio/image/video + distribution)
- Consent-gated handlers; generation separated from distribution

