# Manual install (for developers)

This is for contributors who need bare-metal Postgres, Redis, and Node. Strangers should use [Install](install.md) (curl / pipx) or [Quickstart](quickstart.md) (Docker Compose).

Use this path when Docker is not available or you need systemd-managed services on the host.

## Requirements

- Python 3.11 or 3.12
- Node.js 22+ (for the frontend)
- PostgreSQL 16 with pgvector
- Redis 7
- pnpm (frontend lockfile is `pnpm-lock.yaml`)

## Steps

```bash
git clone https://github.com/malike2356/keprix.git && cd keprix
bash scripts/install.sh
source .venv/bin/activate
cp .env.example .env
# Edit .env with database URLs and secrets
keprix setup
```

Alternative package install from the same checkout (pipx-managed env, same honesty as [Install](install.md)):

```bash
pipx install '.[tui]' --force
keprix setup
```

Start the API:

```bash
keprix start --host 127.0.0.1 --port 3333
```

In another terminal, build and run the frontend:

```bash
cd frontend && pnpm install && pnpm build && pnpm start
```

For guided values when `keprix setup` is unavailable, `python3 scripts/wizard.py` from the checkout is a fallback.

Optional automation: `scripts/install-baremetal.sh` can drive host package and service setup when you want scripted bare-metal provisioning.

Next: [First run](first-run.md).
