# Worldwide GTM sign-off

## Current verdict

Code readiness can pass without credentials. Worldwide market readiness cannot
pass until the owner configures protected publishing and signing environments and
the exact release workflow publishes its first verified artifacts.

## Fail-closed command

Run the local preparation gate:

```bash
bash scripts/check-worldwide-gtm-gate.sh
```

Run the final live gate after owner configuration and release publication:

```bash
KEPRIX_GTM_REQUIRE_LIVE_ARTIFACTS=1 bash scripts/check-worldwide-gtm-gate.sh
```

The second command must remain red when the manifest is unavailable, invalid, or
contains no artifacts. A source checkout passing tests is not a substitute for a
signed public release.

## Reserved owner actions

1. Configure the protected environments in `docs/operations/owner-release-configuration.md`.
2. Enable required branch and environment approvals in GitHub.
3. Approve the first release candidate and its PyPI, Docker, macOS, and Windows jobs.
4. Recruit independent clean-machine beta testers and record the acceptance evidence.
5. Approve public launch only after the live gate passes.
