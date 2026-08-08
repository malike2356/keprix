# Keprix Desktop

Keprix Desktop is currently a release candidate built from
`src/keprix/apps/desktop`. Do not download installers from third-party or legacy
Nous locations.

## Planned stable matrix

| Platform | Target | Current state |
| --- | --- | --- |
| macOS 13 or newer | arm64 DMG and zip; x86_64 DMG and zip | Build configured; signing and notarization pending |
| Windows 10 or newer | x86_64 NSIS and MSI | Build configured; signing pending |
| Ubuntu 22.04 and 24.04 | x86_64 AppImage and deb | Build configured; clean-machine proof pending |

Stable installers will be linked from `https://keprixai.com/download` and the
matching GitHub Release only after signature, checksum, first-boot, update, backup,
rollback, and uninstall gates pass. Until then, use the CLI/TUI or Docker web
workspace, or build Desktop from source for development.
