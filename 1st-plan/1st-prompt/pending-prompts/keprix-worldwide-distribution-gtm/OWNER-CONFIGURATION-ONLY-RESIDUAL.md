# Owner configuration and external evidence residual

**Status:** OWNER ACTION REQUIRED
**Updated:** 2026-08-08

The credential-independent implementation is prepared. These prompts remain in
pending because a public release cannot be truthfully completed or archived until
external publication and clean-machine evidence exists.

## Owner configuration

1. Configure PyPI trusted publishing for the protected `pypi` environment.
2. Add scoped Docker Hub publisher credentials to `dockerhub`.
3. Add Apple signing and notarization values to `desktop-macos`.
4. Add Windows code-signing values to `desktop-windows`.
5. Enable protected tags, required checks, and owner approvals in GitHub.
6. Select and approve the privacy, support, vulnerability, and telemetry policies.

Use `docs/operations/owner-release-configuration.md`. Do not place these release
credentials in source, `.env`, Keprix tenant storage, or runtime credential forms.

## Evidence that can exist only after configuration

- TestPyPI and PyPI publication with anonymous installation.
- Public amd64 and arm64 image pulls and clean-host Compose tests.
- Signed and notarized desktop packages on macOS, Windows, and Linux.
- Published manifest with live immutable URLs, signatures, SBOMs, and provenance.
- Independent stranger beta and accessibility reports.
- Rollback, compromised-key, and registry outage exercises.
- Final live gate:
  `KEPRIX_GTM_REQUIRE_LIVE_ARTIFACTS=1 bash scripts/check-worldwide-gtm-gate.sh`.

No prompt in this directory should be archived until its corresponding external
evidence has passed and is linked from the sign-off record.
