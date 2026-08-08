# Reference 600: worldwide distribution and GTM build order

**Status:** PENDING

## Current verdict

Keprix is publicly inspectable and can be installed by a technically capable user
from GitHub. It is not yet ready for an unrestricted worldwide launch. There are no
published release assets, PyPI package, or Docker Hub images, and the website does
not provide native downloads. The installer follows `main` by default and uses an
editable checkout, which is convenient for development but weak for stable public
distribution.

## Must, Nice, and Ultimate

### Must before GTM

- One canonical version across Python, desktop, images, docs, and release notes.
- Immutable GitHub Release with source archives, checksums, SBOM, provenance, and
  supported native artifacts.
- Clean-room install tests for curl, pipx or PyPI, Docker Compose, and desktop.
- Multi-architecture Docker images published under a verified public namespace.
- Signed macOS and Windows desktop packages; notarized macOS artifacts.
- Website download centre driven by the release manifest, with honest OS support.
- TUI and desktop release-parity contracts for all launch-critical modules.
- Upgrade, migration, backup, restore, rollback, and uninstall paths.
- Public security policy, vulnerability reporting, dependency scanning, licence
  inventory, privacy disclosure, support expectations, and release runbooks.
- A fail-closed GTM gate that checks live artifact availability and hashes.

### Nice after the first safe release

- Package manager channels such as Homebrew, WinGet, Chocolatey, and apt.
- Delta desktop updates, release rings, opt-in diagnostics, crash reporting, and
  in-product release notes.
- Interactive installer doctor, compatibility report, exportable support bundle,
  migration assistant, and offline installation bundle.
- Demo workspace, recipes, templates, guided module tours, and sidecar quickstarts.

### Ultimate

- Reproducible builds with independently verifiable provenance.
- Hardware-aware local model setup and GPU profiles.
- Enterprise offline mirror, signed update repository, fleet policy, and staged
  rollout controls.
- Accessibility and localization certification across web, TUI, and desktop.

## Workarounds until full completion

| Limitation | Safe temporary path |
| --- | --- |
| PyPI unpublished | Pin pipx to a full Git commit or release tag URL |
| No Docker registry images | Clone a release tag and build locally with Compose |
| No desktop release | Use the documented CLI or Docker path; label desktop preview |
| Native Windows uncertain | Support WSL2 only until Windows CI passes |
| Signing credentials unavailable | Publish checksums and unsigned preview assets, clearly marked; do not call them stable |
| ARM hardware unavailable | Use hosted arm64 runners plus one real-device smoke before support claim |
| Website and releases can drift | Render downloads from a signed release manifest and fail closed |
| Costly full matrices | Run fast PR tests, nightly clean-machine matrices, and mandatory release gates |

## Prompt map

600 inventory and truth lock; 601 release and support contract; 602 versioning and
release manifest; 603 bare-metal installer; 604 PyPI and pipx; 605 Docker; 606
supply chain; 607 GitHub release automation; 608 TUI parity; 609 desktop parity;
610 desktop packaging; 611 updates and lifecycle; 612 website download centre;
613 public repository; 614 security and privacy; 615 docs and support; 616
observability and launch operations; 617 stranger beta; 618 final GTM gate.
