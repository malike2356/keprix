# Obsidian Vault Starter Pack

The Obsidian vault starter pack creates a markdown vault layout that Keprix agents can read and write without requiring an Obsidian desktop plugin.

## Contents

```text
KEPRIX.md
00-inbox/
01-projects/
02-areas/
03-resources/
04-archive/
templates/
  daily-note.md
  meeting.md
  research-summary.md
.keprix/
  vault-manifest.json
```

`KEPRIX.md` is the agent bootstrap. It contains standing instructions, folder rules, and the session export convention.

## CLI

```bash
keprix vault list-packs
keprix vault init --pack obsidian-starter --path /path/to/vault
keprix vault validate --path /path/to/vault
keprix vault render-template --path /path/to/vault --template daily-note --output 00-inbox/today.md
```

## API

- `GET /api/vault/packs`
- `POST /api/vault/init`
- `POST /api/vault/validate`

## Vault Provider Contract

The universal vault provider can use `.keprix/vault-manifest.json` as a folder resolver. A `VaultProvider.resolve_path("inbox")` implementation should read `folders.inbox` from the manifest and resolve it inside the vault root.
