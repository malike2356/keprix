# Syncthing (Obsidian vault)

Keprix wires Syncthing for the **Obsidian vault only**. Durable agent memory and skills stay on **GitHub agent-sync**.

**Configure in the GUI:** Settings -> Syncthing (`/settings/integrations/syncthing`).

## Separation (hard rule)

| Channel | Owns | Path example |
| --- | --- | --- |
| Syncthing | Obsidian vault notes | `~/.keprix/vault` (host) / `/var/syncthing/vault` (sidecar) |
| Agent-sync | Shared memory + skills | `~/.keprix/data/github-agent-sync/<scope>/` |

Do **not** point Syncthing and agent-sync at the same write-heavy tree. Keprix rejects enable when the vault path overlaps the agent-sync clone or forbidden markers (`github-agent-sync`, etc.).

## One writer

Pick exactly one primary writer in Settings:

- **home**: Obsidian / home Syncthing is the writer. Keprix folder type is `receiveonly` and vault `read_only` is set true.
- **keprix**: Keprix writes captures; home peer should be receive-only / browse.
- **both**: both sides write. Expect Syncthing conflict copies. Prefer home or keprix.

## Docker sidecar

```bash
cd keprix
COMPOSE_FILE=docker/docker-compose.yml:docker/docker-compose.syncthing.yml docker compose up -d syncthing
```

- GUI on host: `http://127.0.0.1:8384`
- From Keprix containers: base URL `http://syncthing:8384`
- Vault bind: host `~/.keprix/vault` -> Syncthing `/var/syncthing/vault` (same files as Keprix `/home/keprix/.keprix/vault`)

Paste the Syncthing API key in the GUI. Optional env bootstrap only: `SYNCTHING_API_KEY` / `KEPRIX_SYNCTHING_API_KEY`.

## API

- `GET /api/syncthing/status`
- `PUT /api/syncthing/settings`
- `POST /api/syncthing/ensure-folder`
- `POST /api/syncthing/pause` body `{ "paused": true|false }`

## Tool

`syncthing_vault` (toolset `syncthing`): actions `status|ensure_folder|pause|resume`.

## Related

- [GitHub agent-sync](agent-sync.md) for memory/skills (not the vault)
