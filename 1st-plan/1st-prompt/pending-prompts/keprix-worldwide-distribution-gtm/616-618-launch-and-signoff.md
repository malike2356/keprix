# Prompts 616-618: launch operations, stranger beta, and sign-off

**Status:** PENDING
**Depends on:** 600-615

## Prompt 616: production operations and market telemetry

Define service level indicators for download availability, install success, first
healthy run, update success, crash-free sessions, Docker health, API latency, queue
failures, and support volume. Use opt-in, privacy-preserving diagnostics for
self-hosted installations; Keprix must remain functional when telemetry is off.
Redact prompts, contacts, tokens, file contents, and tenant data by default.

Create dashboards and alerting for website downloads, release assets, registries,
documentation, status page, and supported hosted services. Add launch capacity,
incident, rollback, compromised release, key rotation, registry outage, PyPI outage,
and bad updater runbooks. Conduct a rollback and compromised-key tabletop exercise.

## Prompt 617: closed stranger beta and release candidate

Cut a signed prerelease from the exact production workflow. Test with users who have
no repository context across every supported OS and architecture. Each participant
must install, configure a provider or local model, use TUI or desktop, exercise one
major workflow, restart, upgrade, export or back up, restore, and uninstall.

Capture time to first value, failure stage, logs through the redacted support bundle,
accessibility issues, confusing claims, and support burden. Fix all Critical and High
issues, rerun affected matrices, and publish a release-candidate report. Do not use
customer production data or ask testers to disable platform security.

## Prompt 618: fail-closed worldwide GTM sign-off

Create `scripts/check-worldwide-gtm-gate.sh` and
`docs/architecture/worldwide-gtm-signoff.md`. The gate must verify:

- GitHub repo, latest stable Release, every manifest URL, checksum, signature, SBOM,
  provenance, and anonymous download.
- PyPI version and wheel install, or an explicit owner-approved deferral that removes
  all PyPI marketing claims.
- Docker amd64 and arm64 manifests, pull, Compose health, persistence, backup,
  upgrade, rollback, and uninstall.
- Bare-metal clean-machine install, doctor, first run, update, rollback, and uninstall.
- Signed desktop artifacts and clean-machine tests for every advertised target.
- Canonical version agreement, TUI and desktop parity contracts, migrations, docs,
  download centre links, public repository hygiene, security and privacy gates.
- Production website and status endpoints remain healthy. If Contabo is touched,
  `https://carinaai.uk/` must return HTTP 200 before completion.

Produce an evidence table with workflow run URLs, artifact digests, test dates,
supported matrix, known limitations, owners, and expiry dates. Verdict can be READY
only when every Must item passes. Owner-blocked signing, publication, legal review,
or DNS work must yield NOT READY, not a waiver disguised as success. Archive this
programme only after READY and after all completed prompts are marked and indexed.
