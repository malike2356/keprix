# Universal Sidecar security policy

Security vulnerabilities in the Universal Sidecar must be reported privately.

Do not open a public GitHub issue for security vulnerabilities.

Prefer the process in the repository root [SECURITY.md](../../SECURITY.md):
report to **security@carinaai.uk** with reproduction steps, impact, and
affected paths. Coordinated disclosure (90-day window) applies.

Sidecar-specific notes to include:

- contract version and deployment mode (mounted vs sidecar-only)
- whether the issue is northbound (`/sidecar/v1`) or southbound connectors
- whether secrets or cross-tenant data were exposed (do not paste live secrets)
