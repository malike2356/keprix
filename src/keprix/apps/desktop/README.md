# Keprix Desktop

<p align="center">
  <a href="https://github.com/malike2356/keprix"><img src="https://img.shields.io/badge/Source-GitHub-FFD700?style=for-the-badge" alt="Source"></a>
  <a href="https://keprixai.com/docs"><img src="https://img.shields.io/badge/Docs-keprixai.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://github.com/malike2356/keprix/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
</p>

The native desktop shell for Keprix by Verlox Limited. It provides agent chat,
streaming tool output, previews, file browsing, voice, and settings in a native
window. Desktop remains a release candidate until signed artifacts pass the clean
machine matrix.

<table>
<tr><td><b>Chat with the full agent</b></td><td>Streaming responses, live tool activity, structured tool summaries, and the same conversation history as every other Keprix surface.</td></tr>
<tr><td><b>Side-by-side previews</b></td><td>Render web pages, files, and tool outputs in a right-hand pane while you keep chatting.</td></tr>
<tr><td><b>File browser</b></td><td>Explore and preview the working directory without leaving the app.</td></tr>
<tr><td><b>Voice</b></td><td>Talk to Keprix and hear it back.</td></tr>
<tr><td><b>Settings & onboarding</b></td><td>Manage providers, models, tools, and credentials from a real UI. First-run setup gets you to your first message in seconds.</td></tr>
<tr><td><b>Stays current</b></td><td>Built-in updates pull the latest agent and rebuild the app in place.</td></tr>
</table>

---

## Install

### Install with Keprix (recommended)

Already have the Keprix CLI? Just run:

```bash
keprix desktop
```

It builds and launches the GUI against your Keprix home by default. On first launch Keprix creates its own config, keys, sessions, memory, and skills store; if you want to import from another install, do that explicitly.

### Prebuilt installers

No stable prebuilt installer is published yet. Stable links will appear on
`https://keprixai.com/download` only after GitHub Release assets are signed,
checksummed, and tested. Build from source for development use.

---

## Updating

The app checks for updates in the background and offers a one-click update when one is ready. You can also update any time from the CLI:

```bash
keprix update
```

---

## Requirements

The installer handles everything for you (Python 3.11+, a portable Git, ripgrep).

---

## Development

Want to hack on the app itself? Install workspace deps from the repo root once, then run the dev server from this directory:

```bash
npm install          # from repo root; links apps/desktop, web, apps/shared
cd apps/desktop
npm run dev          # Vite renderer + Electron, which boots the Python backend
```

Point the app at a specific source checkout, or sandbox it away from your real config:

```bash
KEPRIX_DESKTOP_KEPRIX_ROOT=/path/to/clone npm run dev
KEPRIX_HOME=/tmp/throwaway npm run dev
npm run dev:fake-boot   # exercise the startup overlay with deterministic delays
```

### Building installers

```bash
npm run dist:mac     # DMG + zip
npm run dist:win     # NSIS + MSI
npm run dist:linux   # AppImage + deb + rpm
npm run pack         # unpacked app under release/ (no installer)
```

Installers are built and uploaded to GitHub Releases manually. macOS/Windows signing & notarization happen automatically when the relevant credentials are present in the environment (`CSC_LINK` / `CSC_KEY_PASSWORD` / `APPLE_*` for macOS, `WIN_CSC_*` for Windows).

### How it works

The packaged app ships only the Electron shell. On first launch it installs the Keprix runtime into `KEPRIX_HOME` (`~/.keprix`, or `%LOCALAPPDATA%\keprix` on Windows); that is separate from any Hermes install. The renderer (React, in `src/`) talks to a `keprix dashboard` backend over the standard gateway APIs and reuses the embedded TUI rather than reimplementing chat. The install, backend-resolution, and self-update logic all live in `electron/main.cjs`.

### Verification

Run before opening a PR (lint may surface pre-existing warnings but must exit cleanly):

```bash
npm run fix
npm run typecheck
npm run lint
npm run test:desktop:all
```

### Troubleshooting

Boot logs land in `KEPRIX_HOME/logs/desktop.log` (includes backend output and recent Python tracebacks); check it first if the app reports a boot failure.

**macOS / Linux:**

```bash
# Force a clean first-launch setup
rm "$HOME/.keprix/hermes-agent/.hermes-bootstrap-complete"
# Rebuild a broken Python venv
rm -rf "$HOME/.keprix/hermes-agent/venv"
# Reset a stuck macOS microphone prompt (macOS only)
tccutil reset Microphone com.verlox.keprix
```

**Windows (PowerShell):**

```powershell
# Force a clean first-launch setup
Remove-Item "$env:LOCALAPPDATA\keprix\hermes-agent\.hermes-bootstrap-complete"
# Rebuild a broken Python venv
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\keprix\hermes-agent\venv"
```

> The default Keprix home on Windows is `%LOCALAPPDATA%\keprix`. Set the `KEPRIX_HOME` env var if you've relocated it.

---

## Community

- [Documentation](https://keprixai.com/docs)
- [Issues](https://github.com/malike2356/keprix/issues)

---

## License

MIT; see [LICENSE](../../LICENSE).

Built by Verlox Limited.
