# Prompts 612-615: website, repository, security, and support

**Status:** CODE PREPARED; LIVE ARTIFACT AND OWNER POLICY PROOF PENDING
**Depends on:** 601-611 as applicable

## Prompt 612: production download centre

Build `/download` on `keprixai.com`. Populate it from the signed release manifest,
not copied URLs. Detect platform only as a convenience; always let users select OS,
architecture, version, and channel. Show file size, checksum, signature verification,
requirements, release notes, known issues, installation, upgrade, uninstall, Docker,
CLI, and source links. Never show a button for a missing artifact.

Add a copyable verified terminal path and beginner-friendly GUI path. Track only
privacy-preserving aggregate download events with consent where required. Add link,
hash, accessibility, responsive, no-JavaScript fallback, stale manifest, unavailable
registry, and anonymous download tests. Deploy without disrupting Carina.

## Prompt 613: public repository consumption readiness

Audit tracked history and current files for secrets, private paths, customer data,
generated assets, internal prompt libraries, dead links, oversized files, licences,
copyright, third-party attribution, issue templates, discussions, code of conduct,
contribution guide, governance, support, roadmap claims, and branch protection.

Create a clean clone experience with install-first README, architecture map, minimal
examples, development setup, test commands, release policy, compatibility matrix,
security policy, and good-first-issue path. Decide explicitly whether `1st-plan/`
belongs in the public distribution. Do not rewrite public history without owner
approval and a migration plan. Add a public-tree export check and anonymous clone
test.

## Prompt 614: security, privacy, and legal launch gate

Threat-model installers, update feeds, desktop IPC, Docker defaults, plugin and skill
installation, model providers, sidecars, CRM outreach, uploaded files, telemetry,
and supply-chain compromise. Verify least privilege, SSRF controls, path boundaries,
tenant isolation, CSRF, rate limits, audit logs, approval gates, prompt injection
defence, consent, suppression, and secret storage.

Publish responsible disclosure, supported versions, response targets, privacy notice,
data retention and deletion, subprocess and network disclosure, third-party licence
notices, and an accurate Community MIT statement. Legal review remains an owner task;
code must not present unreviewed text as legal advice.

## Prompt 615: onboarding, documentation, and support readiness

Write task-based paths for first conversation, provider setup, local models, Docker,
TUI, desktop, CRM, spreadsheet preprocessing, sidecar integration, channels, backup,
updates, and uninstall. Include exact supported commands and screenshots or terminal
captures generated from the release candidate. Add troubleshooting by symptom,
`keprix doctor`, redacted support bundles, FAQ, compatibility table, status page,
support scope, response expectations, and migration guides.

Run documentation link, command, code sample, accessibility, spelling, and version
drift checks. Recruit readers unfamiliar with the repository and record where they
fail without coaching.
