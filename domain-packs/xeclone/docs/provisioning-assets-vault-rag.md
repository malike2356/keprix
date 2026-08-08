# Provisioning, assets, vault, RAG, models

## Provision

`plan_provision`, `provision`, `deprovision`, `upgrade_validate`, `rollback`.

Receipts include versions and rollback instructions. **No secrets.**

Provision never changes the live Carina path (`carina_path_changed: false`).

## Assets

Registry stores reference, owner/subject, media type, hash, capture source,
consent, allowed uses/providers, quality, retention and deletion state.

## Vault

Nodes receive narrow handles only. Raw secret export is forbidden.

## RAG

Allowlisted corpora with sensitivity labels and relationship scopes. Cross-tenant
retrieval fails closed. Public audience excludes relationship private notes.

## Models

Router declares stub providers with inference-only / no-train policy and
text-only fallback when media providers fail.

## Upgrade / rollback

Persona and pack pin separately. Rollback restores both without rolling back
consent revocations.
