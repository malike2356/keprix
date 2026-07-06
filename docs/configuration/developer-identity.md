# Developer identity

Local developer identity ties this machine to the installation owner (Prompt 01).

## Commands

```bash
keprix init                 # Create identity after owner confirmation
keprix identity status      # Show validity and paths
keprix identity revoke      # Remove identity from this host
```

## Storage

Identity material lives under `~/.keprix/identity/` (see `dev.json` and related files).

## Wizard integration

First-run setup may ask whether you are the developer. Answering yes runs the same flow as `keprix init`.

## Security

Do not copy identity files to shared machines. Revoke before decommissioning a laptop used for development.
