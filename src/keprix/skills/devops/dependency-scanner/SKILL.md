---
name: dependency-scanner
description: Dependency and CVE advisory scanning for WARDEN.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [warden, security, dependencies, cve, supply-chain]
    related_skills: [keprix-core-security]
---

# Dependency Scanner

Check project dependencies against known CVE advisories and pinning policy.

## Checks

- Unpinned dependencies flagged as Medium severity
- Known vulnerable package versions flagged per advisory database
- Lockfiles recommended for reproducible builds

## Usage

Pass requirements lines to `WardenAuditor.audit_dependencies()` or include in a full audit run.

Upgrade critical and high findings before deployment.
