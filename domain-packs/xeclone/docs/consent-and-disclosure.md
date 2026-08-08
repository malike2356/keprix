# Consent and disclosure

## Purposes

ingest, index, train, generate, transform, upload_to_provider, publish,
private_message, retain, export, delete.

## Rules

1. Consent is versioned and revocable per asset and purpose.
2. `check_consent(asset_id, purpose)` returns allowed or denied.
3. Revoke blocks generation and future indexing.
4. Another person's media cannot be used as owner identity input (`subject_id`
   must match owner `owner-laud`).
5. Media outputs carry disclosure and watermark state.
6. Watermark/disclosure removal is blocked in Phase 1-4.
7. Persona/pack rollback never rolls back consent revocation records.

## Labels

Drafts separate:

- stated_facts
- private_correspondence
- inferred_preferences
- generated_style

Relationship/private data is excluded from public drafts unless specifically approved.
