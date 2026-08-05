# Manual install (bare metal)

Use this path when Docker is not available or you need systemd-managed services.

For a normal single-user workstation install, use [Install Keprix](install.md) instead. That path installs the packaged `keprix` command with `pipx` and does not require an activated development environment.

## Requirements

- Python 3.11 or 3.12
- Node.js 22+ (for the frontend)
- PostgreSQL 16 with pgvector
- Redis 7

## Steps

```bash
git clone https://github.com/malike2356/keprix.git && cd keprix
bash scripts/install.sh
cp .env.example .env
# Edit .env with database URLs and secrets
python3 -m keprix.keprix_cli.main setup
```

Start the API:

```bash
keprix start --host 127.0.0.1 --port 3333
```

In another terminal, build and run the frontend:

```bash
cd frontend && npm ci && npm run build && npm run start
```

For guided values, run `python3 scripts/wizard.py`.

Full installer automation is tracked in Prompt 33 (`install-baremetal.sh`).
