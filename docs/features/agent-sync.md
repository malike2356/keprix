# GitHub agent-sync

Keprix mounts the same durable-memory bridge used by Carina, Aiva, and Hermes (Fowler).

**Configure in the GUI:** Settings -> Agent sync (`/settings/integrations/agent-sync`), or the Settings overview card.

Canonical repo: `malike2356/agent-sync` (changeable in the GUI).

## What it is

- Shared markdown/skills memory over GitHub
- Pull on an interval; push on approved durable writes (or interval)
- Local keyword index under `~/.keprix/data/github-agent-sync/<scope>/`
- Policy denies secrets and ephemeral chat dumps

**Not the Obsidian vault.** Vault sync uses [Syncthing](syncthing.md). Do not point agent-sync and Syncthing at the same write-heavy tree.

## GUI setup

1. Open **Settings -> Agent sync**
2. Paste a fine-grained GitHub PAT
3. Set owner/repo/branch (defaults are fine)
4. Set product to `keprix` (use `hermes` on Fowler)
5. Enable, Save, then Pull now

No `.env` changes are required for normal use. Tokens saved from the GUI live under `~/.keprix/data/github-agent-sync/` (mode 600).

## API (same as the GUI)

- `GET /api/agent-sync/status`
- `PUT /api/agent-sync/settings`
- `POST /api/agent-sync/pull|push|index|search|note`

## Tool

`github_agent_sync` (toolset `github-agent-sync`): actions `status|pull|push|search|note`.

## Hermes / Fowler

Local Hermes (Fowler) should use product `hermes` on the same repo. VPS Keprix uses `keprix`. They share `memory/` and `skills/` while keeping distinct agent mounts.

## Optional env bootstrap

Env vars exist only as an optional bootstrap for headless hosts. Prefer the Settings GUI whenever you have a browser.
