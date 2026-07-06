---
name: privacy-scanner
description: PII and secret detection with redaction recommendations for WARDEN.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [warden, security, privacy, pii, gdpr, secrets]
    related_skills: [keprix-core-security]
---

# Privacy Scanner

Detect exposed PII and secrets in text and files.

## Patterns

- Email addresses
- Phone numbers
- National insurance style identifiers
- Credit card numbers
- API keys, tokens, JWTs, connection strings (via vault patterns)

## Output

Returns sanitized text with redactions and remediation recommendations. Critical and high findings block export without review.
