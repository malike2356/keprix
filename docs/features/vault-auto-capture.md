# Vault auto-capture (Agent OS memory loop)

Conversations are written into the **single** markdown vault so every agent shares one memory.

## Behavior

- After each web chat turn, Keprix upserts one note per session under `conversations/YYYY/MM/<session>.md`.
- If no vault is configured, Keprix creates `~/.keprix/vault` (one-vault rule).
- Disable with `KEPRIX_VAULT_AUTO_CAPTURE=false`.

## Day-1 Hello World

```bash
keprix agent-os hello --name You
keprix vault ensure-default
keprix model   # switch provider with one command
```

## Code

- `src/keprix/vault/capture.py`
- Hook: `src/keprix/api/conversation_routes.py`
- Workflow: `src/keprix/agent_os/hello_world.py`
