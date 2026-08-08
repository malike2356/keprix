# Public GTM hard inventory

**Updated:** 2026-08-08

The canonical detailed inventory is
[`worldwide-distribution-gap-map.md`](worldwide-distribution-gap-map.md). This
document maps the earlier 570-582 questions into the consolidated 600-618
programme.

| Channel | Stranger path | State | Remaining external configuration |
| --- | --- | --- | --- |
| Source | Public GitHub clone | Available | None |
| Development CLI | Public `scripts/install.sh` | Available | None |
| Stable CLI | `scripts/install-release.sh --version X.Y.Z` | Built, public proof blocked | Publish signed GitHub Release |
| PyPI | `pipx install 'keprix[tui]'` | Pipeline built, package absent | Configure OIDC trusted publisher and approve publish |
| Docker | `docker/compose.release.yml` | Pipeline built, images absent | Add protected Docker Hub credentials and publish |
| Desktop | DMG, NSIS/MSI, AppImage/deb/rpm | Source build only | Signing credentials plus release matrix |
| Website | `keprixai.com` | Live; Community CTA corrected | Publish manifest-driven downloads |

Hard READY requires the fail-closed prompt 618 gate. Marketing may claim public
source, self-hosting, development installation, current web features, and MIT
licensing. It must not claim stable native downloads, PyPI availability, public
container images, signed desktop installers, or worldwide READY until live probes
pass.

Owner-only configuration consists of protected GitHub environments, OIDC publisher
registration, Docker registry credentials, Apple notarization, Windows code
signing, and final stable promotion approval. Any Contabo change must preserve an
HTTP 200 response from `https://carinaai.uk/`.
