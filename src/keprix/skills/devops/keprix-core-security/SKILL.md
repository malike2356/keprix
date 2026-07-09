---
name: keprix-core-security
description: Base defensive security capabilities for WARDEN; audits, hardening, and incident response.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [warden, security, audit, ciso, defensive]
    related_skills: [config-hardener, privacy-scanner, dependency-scanner]
---

# Keprix Core Security

WARDEN defensive security skill pack for the Keprix platform and user-owned infrastructure.

## Capabilities

- Structured security audits with severity ratings
- Configuration hardening recommendations
- Incident response templates
- Out-of-scope refusal for offensive operations (external tooling)

## Scope

**In scope:** audits, hardening, privacy scanning, dependency advisories, access review guidance.

**Out of scope:** penetration testing, OSINT, forensics, SIEM, threat intel (use dedicated offensive-security products).

## Reporting

Every finding includes severity (Critical/High/Medium/Low) and remediation steps. Audit reports are encrypted at rest.
