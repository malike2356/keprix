# keprix - Prompt 30: Domain Knowledge Pack Factory

## Purpose

Build a factory for creating, validating, localizing, updating, and distributing domain knowledge packs.

Aiva (commercial, separate product) already has many vertical knowledge areas. keprix needs a public, safe, repeatable way to create domain packs for sectors such as property, healthcare, legal, finance, agriculture, education, logistics, construction, recruitment, retail, manufacturing, energy, hospitality, automotive, technology, and local African services.

## Scope

Implement:

- Domain pack manifest.
- Source ingestion.
- Source quality scoring.
- Jurisdiction tagging.
- Glossaries.
- Playbooks.
- Tool mappings.
- Data schemas.
- Localization.
- Human review.
- Versioning.
- Tests.
- Hub publication.
- Update workflows.

## Output Paths

```text
keprix/backend/domain_packs/
  __init__.py
  manifests.py
  ingestion.py
  source_quality.py
  jurisdiction.py
  glossary.py
  playbooks.py
  schemas.py
  validation.py
  localization.py
  publisher.py

keprix/domain-packs/
  _template/

keprix/ui/web/domain-packs/
keprix/tests/domain_packs/
```

## Pack Contract

Each domain pack must include:

- Domain name.
- Jurisdictions covered.
- Source list.
- Source quality score.
- Update date.
- Glossary.
- Common tasks.
- Playbooks.
- Required disclaimers.
- Data schemas.
- Tool permissions.
- Localization coverage.
- Tests.
- Limitations.

## Review Rules

High-stakes domains require human review:

- Healthcare.
- Legal.
- Finance.
- Insurance.
- Employment.
- Safety.
- Construction.
- Cybersecurity.

The pack must state what it can and cannot do.

## Localization

Domain packs must integrate with Prompt 28:

- Local-language glossary.
- Region-specific examples.
- Country-specific compliance notes.
- Voice-friendly explanations.
- Low-resource language fallback.

## Tests

Add tests for:

- Pack manifest validates.
- Missing jurisdiction fails for regulated pack.
- Source without citation fails quality check.
- Glossary terms are preserved.
- Playbook links are valid.
- Localization metadata validates.
- High-stakes pack requires disclaimer and review gate.

## Acceptance Criteria

- keprix can create domain packs safely.
- Domain packs are versioned.
- Domain packs can be localized.
- High-stakes domains include review and compliance gates.
- Packs can be published through the Hub.
