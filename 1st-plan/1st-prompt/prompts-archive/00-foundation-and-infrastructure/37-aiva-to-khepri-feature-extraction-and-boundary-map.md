# keprix - Prompt 37: Carina and Aiva Feature Extraction and Boundary Map

## Purpose

Define how keprix learns from the **Carina commercial platform** and its customer product
**Aiva** without copying private production secrets, customer data, commercial-only features,
or enterprise-only Scout controls.

This prompt exists because Carina/Aiva is the mature stack and keprix is the public
self-hosted foundation. keprix adopts platform lessons (memory, RAG, workspace, vault,
integrations, operator UX) and rebuilds them under MIT with clear boundaries.

See also: `00a-product-vision-and-agent-consolidation-map.md` (Carina features table).

## Scope

Implement a feature extraction process for Carina core (`core.carinaai.uk`), Aiva product
surfaces, and shared integration patterns:

- Feature inventory (subsystem, owner, source path, target keprix prompt).
- Source-to-target mapping.
- Licensing review.
- Security review.
- Secret scanning.
- Data boundary review.
- Rebuild plans (never blind copy).
- Test mapping.
- Documentation mapping.
- Enterprise and Scout gate classification.

Do not copy:

- Production `.env` files from Carina or Aiva.
- Customer data or private tenant records.
- Private Scout server code.
- Aiva Keys, `keys.carinaai.uk`, or billing infrastructure.
- Paid enterprise-only controls.
- Stripe live credentials.
- Operational secrets.
- Internal-only runbooks that expose infrastructure.
- Proprietary customer workflows not intended for the public product.

## Classification

Every Carina or Aiva feature must be classified:

| Class | Meaning | keprix Action |
| --- | --- | --- |
| Public core | Suitable for free self-host. | Rebuild in keprix. |
| Public optional | Useful but dependency-heavy. | Ship as optional plugin or pack. |
| Paid managed | Belongs to Aiva managed SaaS. | Stub or integration hook only. |
| Scout enterprise | Paid governance or trust control. | Gate behind Scout connection. |
| Unsafe or private | Not suitable for keprix. | Do not port. |

## Output Paths

```text
keprix/product/boundaries/
  carina-feature-inventory.md
  carina-to-keprix-map.md
  aiva-to-keprix-map.md
  enterprise-gates.md
  extraction-rules.md
  rejected-features.md

keprix/backend/extraction/
  scanner.py
  classifier.py
  license_check.py
  secret_check.py
  report.py

keprix/tests/extraction/
```

## Extraction Workflow

1. Scan Carina core and Aiva product directories (read-only reference).
2. Build a feature inventory by subsystem.
3. Mark dependencies, data touched, secrets touched, and tenant scope.
4. Classify each feature.
5. Check license and third-party obligations.
6. Check whether the feature conflicts with keprix's free self-host position.
7. Write a rebuild plan instead of copying blindly.
8. Map existing tests to new keprix tests.
9. Mark enterprise-only features as gated.
10. Produce a boundary report.

## Tests

Add tests for:

- Secret patterns are rejected.
- Enterprise-only Scout features are gated.
- Customer data directories are excluded.
- Feature inventory includes owner, source path, and target prompt.
- Public core features can produce a rebuild plan.
- Rejected features include a reason.

## Acceptance Criteria

- keprix has a documented Carina/Aiva extraction boundary.
- No private credentials or customer data are copied into keprix.
- Every imported idea has a classification.
- Enterprise-only features remain gated.
- Rebuild plans preserve behavior without copying private implementation.
