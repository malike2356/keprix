# Prompts 600-601: truth lock and release contract

**Status: COMPLETED 2026-08-08**
**Severity:** CRITICAL

## Prompt 600: inventory every delivery surface

Act as release engineering lead. Audit the repository and live public endpoints.
Create `docs/architecture/worldwide-distribution-gap-map.md` with one row for every
install command, Docker image, Compose file, website button, GitHub workflow,
desktop target, terminal command, update channel, migration, backup, uninstall,
and support path. Record owner, source file, advertised state, proven state,
supported OS and architecture, version source, validation command, and blocker.

Run read-only live checks against GitHub Releases, PyPI, container registries, and
the production website. Scan for stale Hermes, Nous, Carina, private path, private
host, and unsupported-platform claims. Do not silently fix findings in this prompt.
Classify every row Must, Nice, Ultimate, or explicitly out of scope.

Acceptance: the inventory is exhaustive, reproducible, dated, and identifies every
public claim that lacks evidence. Tests and live probes are attached without secrets.

## Prompt 601: lock the release contract

Using 600, define `docs/architecture/release-support-contract.md`. Specify the
first stable support matrix for Linux distributions, macOS versions and CPUs,
Windows native or WSL2, Docker Engine and Compose versions, Python versions,
browsers, RAM, disk, and optional GPU use. Define Community support boundaries,
sidecar compatibility, data ownership, network requirements, semantic versioning,
deprecation windows, release cadence, LTS policy if any, and end-of-life rules.

Define one canonical release manifest schema containing product version, git SHA,
build time, channel, artifact URL, size, SHA-256, signature, SBOM, provenance,
platform, architecture, minimum requirements, database schema, compatibility API,
and rollback constraints. State who approves stable promotion.

Acceptance: product, engineering, support, website, updater, and CI can all consume
the same contract without inventing local rules. Unsupported paths are explicit.

## What was built

- `docs/architecture/worldwide-distribution-gap-map.md` with dated live probes,
  delivery inventory, version drift, owners, priorities, and evidence gaps.
- `docs/architecture/release-support-contract.md` with the first-stable support
  matrix, channels, compatibility rules, release-manifest contract, ownership,
  Community support boundary, and lifecycle requirements.
