# Release and support contract

**Effective baseline:** 0.16.x prerelease
**Contract status:** approved engineering baseline; stable promotion still gated

## Supported first-stable matrix

| Surface | Initial support contract |
| --- | --- |
| Python | CPython 3.11 and 3.12 |
| Linux CLI and TUI | Ubuntu 22.04 and 24.04 x86_64; Debian 12 x86_64 |
| macOS CLI and TUI | macOS 13 or newer on arm64 and x86_64 |
| Windows CLI and TUI | WSL2 with Ubuntu 22.04 or 24.04; native Windows is preview until its matrix passes |
| Docker | Docker Engine 26 or newer and Compose v2.27 or newer on linux/amd64 and linux/arm64 |
| Web browser | Current and previous major Chrome, Edge, Firefox, and Safari |
| Desktop | Preview until signed macOS, Windows, and supported Linux artifacts pass prompt 610 |
| Memory | 4 GB minimum for CLI; 8 GB recommended for the full Compose stack |
| Storage | 5 GB free minimum; additional capacity is required for models and user data |
| GPU | Optional; never required for cloud-model operation |

An artifact is not supported merely because its build configuration exists. The
final sign-off may narrow this matrix when clean-machine evidence demands it.

## Channels and compatibility

- `stable`: production-quality, signed, immutable releases that passed prompt 618.
- `beta`: signed release candidates suitable for informed testers.
- `development`: mutable source builds with no stability promise.
- Semantic versioning governs public APIs and persisted data compatibility.
- Patch releases must not require destructive data migration.
- Minor releases may add backward-compatible APIs and reversible migrations.
- Major releases may remove deprecated contracts after at least one minor release
  and 90 days of public notice, whichever is longer.
- Sidecars negotiate the `/sidecar/v1` contract and must reject incompatible major
  versions without mutating host data.
- Stable support covers the current minor line and the immediately previous minor
  line for critical security fixes unless an explicit LTS policy supersedes it.

## Release manifest contract

The canonical JSON manifest uses schema `keprix.release-manifest.v1` and contains:

- product name and semantic version;
- git commit, source tag, build time, and release channel;
- database schema version and minimum rollback-compatible schema;
- public API and sidecar compatibility versions;
- minimum OS, CPU architecture, Python, Docker, memory, and disk requirements;
- for every artifact: stable identifier, kind, platform, architecture, filename,
  anonymous HTTPS URL, byte size, SHA-256, signature URL, SBOM URL, provenance URL,
  installation role, and required or optional status;
- release notes URL, known-issues URL, support URL, and end-of-support date.

Unknown required fields or unsupported schema majors fail closed. Artifact URLs must
be HTTPS and immutable. Stable manifests cannot point at `main`, `latest` alone, or
an unauthenticated mutable object.

## Ownership and promotion

| Responsibility | Accountable role |
| --- | --- |
| Version and release manifest | Release engineering |
| Database migration and rollback declaration | Backend owner |
| CLI and TUI matrix | Terminal owner |
| Desktop signing and notarization | Desktop owner plus credential owner |
| Image publishing and operations | Platform owner |
| Security exception approval | Security owner |
| Privacy and legal wording | Product owner with qualified review |
| Stable promotion | Product owner after prompt 618 reports READY |

No workflow may convert a failed required publication step into a green release.
Missing owner credentials produce a blocked prerelease, not an unsigned stable build.

## Community support boundary

Community Edition remains usable without payment and without diagnostic consent.
Public support consists of documentation, issue templates, security reporting, and
best-effort community response. There is no uptime guarantee for self-hosted
instances. Operators own their model-provider accounts, backups, lawful CRM use,
email reputation, infrastructure, and local data-retention choices. Keprix must
provide safe defaults and accurate diagnostics without uploading prompts, contacts,
credentials, or file contents.

## Lifecycle requirements

Every stable path must support preflight, install, first healthy use, diagnostics,
backup, update, migration, rollback where schema-compatible, recovery, and uninstall.
Uninstall preserves user-created data unless the user separately confirms deletion.
Security releases may shorten deprecation periods only when the advisory documents
the risk and migration path.
