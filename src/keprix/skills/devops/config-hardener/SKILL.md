---
name: config-hardener
description: OS, container, and application hardening templates for WARDEN.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [warden, security, hardening, docker, headers]
    related_skills: [keprix-core-security]
---

# Config Hardener

Assess and apply security hardening for containers, HTTP headers, and application config.

## Templates

- Docker: disable privileged mode, drop capabilities
- Application: disable debug, enable rate limiting, secure cookies
- OS: restrict .env file permissions
- HTTP: enable security headers and HSTS when HTTPS is active

## Approval

All hardening changes require explicit approval before apply. Use `WardenHardener.apply(..., approved=True)`.
