# Worldwide distribution gap map

**Audited:** 2026-08-08
**Release baseline:** 0.16.0
**Scope:** anonymous Community Edition installation and operation

## Verdict

Keprix source and its curl installer are publicly reachable. A technically capable
Linux, macOS, or WSL2 user can install the CLI from GitHub. Keprix is not ready for
an unrestricted stable launch because there is no published GitHub Release, PyPI
distribution, public container image, signed desktop package, or website download
centre. The public installer also resolves mutable `main` and installs an editable
checkout by default.

## Live evidence

| Probe | Observed result |
| --- | --- |
| GitHub repository | HTTP 200 |
| Raw `scripts/install.sh` | HTTP 200 |
| `https://keprixai.com/` | HTTP 200 |
| GitHub latest Release API | HTTP 404 |
| PyPI `keprix` JSON API | HTTP 404 |
| Docker Hub `carinaai/keprix-backend:latest` | HTTP 404 |
| Docker Hub `carinaai/keprix-frontend:latest` | HTTP 404 |
| Website native download links | None found |

## Delivery inventory

| Surface | Source | Advertised state | Proven state | Owner | Priority | Blocker or next proof |
| --- | --- | --- | --- | --- | --- | --- |
| Curl install | `scripts/install.sh` | Primary install | Public URL and local pipx smoke pass | Release engineering | Must | Pin stable manifest and verify artifact before install |
| Verified install | `scripts/install-verified.sh` | Integrity path | Source exists | Release engineering | Must | Integrate with public signed manifest |
| Bare-metal install | `scripts/install-baremetal.sh` | Linux host path | Source and tests exist | Release engineering | Must | Clean supported-OS VM matrix |
| PyPI and pipx | `pyproject.toml` | Optional documented path | PyPI package absent | Owner and release engineering | Must or explicit deferral | Trusted publisher and first release |
| Compose local build | `docker/docker-compose.yml` | Full local stack | Compose source exists and has prior local smoke | Platform | Must | Clean clone, backup, upgrade, rollback matrix |
| Compose production | `docker/docker-compose.prod.yml` | Production overlay | Source exists | Platform | Must | Published immutable images and clean host proof |
| Backend image | `.github/workflows/release.yml` | Docker Hub publication | Public tag absent | Release engineering | Must | Registry credentials, buildx, fail-closed push |
| Frontend image | `.github/workflows/release.yml` | Docker Hub publication | Public tag absent | Release engineering | Must | Registry credentials, buildx, fail-closed push |
| GitHub Release | release-please workflows | Tagged public release | No public Release | Owner | Must | Protected release environment and first candidate |
| Checksums and signatures | `scripts/sign-release.sh` | Manual integrity support | Script exists; no public artifacts | Security and release engineering | Must | CI-generated checksums, signatures, SBOM, provenance |
| TUI | `src/keprix/tui/` | Hermes-class command centre | pipx launch passes; broad tests exist | Product and terminal | Must | Release environment dependency and module-parity gate |
| Desktop renderer | `src/keprix/apps/desktop/` | Native shell | Build passes locally | Desktop | Must if advertised stable | Feature-parity and clean install matrix |
| macOS package | desktop electron-builder config | DMG and zip | No published signed or notarized artifact | Desktop and owner | Must if advertised | Apple signing and notarization |
| Windows package | desktop electron-builder config | NSIS and MSI | No published signed artifact | Desktop and owner | Must if advertised | Windows signing and clean VM tests |
| Linux desktop | desktop electron-builder config | AppImage, deb, rpm | No published artifact | Desktop | Must if advertised | Supported distro tests and signatures |
| Desktop update | `electron/update-remote.cjs` | Remote updates | Code and tests exist | Desktop | Must | Signed feed, channels, migration and rollback proof |
| CLI upgrade | `src/keprix/upgrade/` | Planned and executable upgrades | Extensive code and tests exist | Platform | Must | Public package resolution and old-version fixtures |
| Backup and restore | `scripts/backup.sh`, `scripts/restore.sh` | Operator recovery | Scripts and tests exist | Platform | Must | Release-to-release restore drill |
| Website | `frontend/src/components/marketing/` | Public product entry | Production HTTP 200 | Marketing and web | Must | Manifest-driven `/download` page |
| Documentation | `README.md`, `docs/getting-started/` | Public onboarding | Public and extensive | Documentation | Must | Commands run against exact release candidate |
| Uninstall | desktop and installer modules | Lifecycle support | Partial implementations exist | Platform and desktop | Must | Program versus user-data choices and clean proof |
| Homebrew, WinGet, apt | None canonical | Not supported | Absent | Release engineering | Nice | Add after first stable channel |
| Offline bundle | None canonical | Not supported | Absent | Release engineering | Nice | Signed dependency and model-aware bundle |
| Fleet update policy | Upgrade and admin modules | Internal capabilities | Not a public release channel | Enterprise | Ultimate | Signed mirror and rollout policy |

## Version drift

- Python, frontend, and release-please declare `0.16.0`.
- Desktop declares `0.15.1`.
- CLI release date declares `2026.6.5`, which is not an ISO date and is stale.
- Desktop still contains inherited `HERMES_DESKTOP_*`, `Nous Research`, and
  `com.nousresearch.keprix` identity or compatibility metadata.
- Public docs contain fixed versions that require synchronization at release time.

## Test evidence and gaps

- `bash scripts/smoke-pipx-install.sh`: passed on 2026-08-08.
- Desktop renderer build: passed on 2026-08-08.
- Desktop platform tests: 180 passed, 1 failed, 1 skipped. The failure checks a
  missing Windows hidden-console subprocess call site.
- The public GTM gate reached the private TUI gate but the active development
  environment lacked the optional `textual` dependency. This is an environment and
  gate reproducibility defect even though the isolated pipx TUI install passed.
- No clean macOS, Windows, WSL2, arm64, or signed artifact proof is recorded.

## Public claim rule

A distribution surface is supported only when its exact release artifact exists,
can be fetched anonymously, has a verified digest and signature, installs on the
declared clean-machine matrix, reaches first healthy use, upgrades, rolls back, and
uninstalls without losing user data by default.
