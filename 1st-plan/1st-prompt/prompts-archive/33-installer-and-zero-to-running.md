# keprix - Prompt 33: Installer and Zero-to-Running

## Purpose

No amount of features matter if nobody can get the product running in under 10 minutes.
This prompt builds the full installation and update experience.

A first-time user must be able to go from a blank Ubuntu 22.04 server to a fully running
keprix instance in one command, without reading documentation first.

## Paths to Running

### Path 1: One-Command Install (Docker, recommended for most users)

The fastest path. User copies and runs:

```bash
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
```

What the script does:
1. Detect OS (Ubuntu, Debian, Fedora, Arch, macOS).
2. Check for Docker and Docker Compose. If missing, install them automatically (with user
   confirmation) or print the install command if auto-install is declined.
3. Check for minimum system resources (2 GB RAM, 10 GB disk, 2 CPU cores). Warn but do not
   block if below minimum.
4. Create `~/keprix/` if it does not exist.
5. Download `docker-compose.yml` and `.env.example` from the release.
6. Copy `.env.example` to `.env`.
7. Run the setup wizard (see below).
8. Run `docker compose up -d`.
9. Wait for health endpoints to pass.
10. Print the access URL: `http://localhost:3000`.
11. Print the first-run credentials (generated during wizard, shown once).

The script must be idempotent: re-running it on an existing install prints the current
status and offers to upgrade, not to re-initialize.

### Path 2: Manual Docker

For users who want control over each step:

```bash
git clone https://github.com/malike2356/keprix.git
cd keprix
cp .env.example .env
# Edit .env with your settings
./scripts/install.sh
```

`scripts/install.sh` runs the same wizard and `docker compose up -d`.

### Path 3: Bare Metal (without Docker)

For users who cannot use Docker or prefer native installs.

`scripts/install-baremetal.sh`:

1. Check Python 3.11+. Install via `deadsnakes` PPA if missing (Ubuntu).
2. Check Node.js 22+. Install via `nvm` if missing.
3. Check PostgreSQL 16. Install if missing.
4. Check Redis 7. Install if missing.
5. Install `uv` if missing.
6. Run `uv sync` in the backend directory.
7. Run `pnpm install` in the frontend directory.
8. Copy and populate service files for systemd.
9. Run the setup wizard.
10. Start services via systemd.
11. Print access URL and credentials.

### Path 4: Cloud (AWS EC2, DigitalOcean Droplet)

Pre-built setup scripts for common cloud providers:

`scripts/bootstrap-aws-ec2.sh`:
- Provisions a t3.medium EC2 instance with Ubuntu 22.04.
- Runs the one-command install.
- Optionally configures a domain and SSL via Let's Encrypt (certbot).

`scripts/bootstrap-do-droplet.sh`:
- Same for DigitalOcean.

These scripts require AWS CLI or `doctl` to be configured. They are not interactive; they
take flags: `--domain`, `--email`, `--size`.

## Setup Wizard

`scripts/wizard.py`

The wizard runs interactively during first install. It sets the values in `.env`.

Questions (in order):
1. "Are you the owner or developer of this installation? (yes/no)"
   - If yes: run developer identity bootstrap from Prompt 00.
2. "What would you like to call this installation?" (default: "keprix")
3. "External domain or leave blank for localhost-only access" (e.g., `carina.yourcompany.com`)
4. "Enable SSL? (requires domain above and certbot)" (yes/no)
5. "Admin email address" (for Let's Encrypt and notifications)
6. Generate a random admin password. Display it once. Confirm the user has saved it.
7. Generate random secrets for `SECRET_KEY`, `SESSION_SECRET`, `IP_HASH_SALT`.
8. "LLM provider API key (OpenAI, Anthropic, etc.) - press Enter to skip and configure later"
9. Developer identity step (`keprix init`)
   - If provided: validate and store it.
10. Show a summary of the settings and ask for confirmation.
11. Write the final `.env` file.

The wizard is also accessible after install via `keprix setup-wizard`.

## Health Checks

`scripts/check-health.sh`

Runs after install to verify all services are up:

```bash
check backend:   curl -sf http://localhost:3333/api/health
check frontend:  curl -sf http://localhost:3000
check postgres:  pg_isready -h localhost -p 5432
check redis:     redis-cli ping
check searxng:   curl -sf http://localhost:8080
```

Exits 0 if all pass, 1 if any fail. Prints a clear pass/fail table.

The installer waits for all health checks to pass (with a 2-minute timeout) before printing
the access URL.

## Update

`scripts/update.sh`

Safe, non-destructive update:

1. Check `https://api.github.com/repos/malike2356/keprix/releases/latest` for the
   latest version.
2. Compare with the installed version (`keprix_VERSION` in `.env`).
3. If already current: say so and exit.
4. Pull the new release.
5. Run database migrations (`scripts/migrate.sh`).
6. Rebuild Docker images (`docker compose build`).
7. Restart services (`docker compose up -d`).
8. Run health checks.
9. Print changelog summary for the new version.

The update script never deletes data. It only replaces application code and images.

`keprix update` runs this script. It is also run by the self-configuration
health monitor from Prompt 16 when an update is available and auto-update is enabled.

## Rollback

`scripts/rollback.sh`

If an update causes issues:

```bash
keprix rollback
```

1. Stop running containers.
2. Restore the previous Docker image tags (stored during update).
3. Run database rollback (reverse the last migration if applicable).
4. Restart services.
5. Run health checks.

The rollback only works for the immediately preceding update. Deep rollbacks require
a database backup restore.

## CLI Entry Point

`keprix/__main__.py`

All operations are accessible via the CLI:

```
keprix start              - start all services
keprix stop               - stop all services
keprix restart            - restart all services
keprix status             - show service status and version
keprix update             - check and apply updates
keprix rollback           - roll back the last update
keprix setup-wizard       - re-run the setup wizard
keprix health             - run health checks
keprix logs [service]     - tail service logs
keprix backup             - create a full backup
keprix restore {file}     - restore from a backup
# keprix has no remote licence keys
keprix keys status        - show current key tier
```

## Backup and Restore

`scripts/backup.sh`

Full backup:
1. `pg_dump` of the PostgreSQL database.
2. Tar of `/data/keprix/` (uploads, memory, generated files).
3. Tar of `~/.keprix/` (identity, config, key cache).
4. Compressed into `keprix-backup-{timestamp}.tar.gz`.

`scripts/restore.sh {file}`:
1. Verify the archive is a valid backup.
2. Stop all services.
3. Restore PostgreSQL from the dump.
4. Restore data directories.
5. Restart services.
6. Run health checks.

## Output Paths

```
scripts/
  install.sh
  install-baremetal.sh
  bootstrap-aws-ec2.sh
  bootstrap-do-droplet.sh
  wizard.py
  update.sh
  rollback.sh
  migrate.sh
  check-health.sh
  backup.sh
  restore.sh
  audit-deps.sh          - from Prompt 02

keprix/
  __main__.py
```

## Tests

```
tests/installer/
  test_wizard.py         - wizard generates valid .env, developer mode flag set correctly
  test_health_checks.py  - health check script passes against mock services
  test_update.py         - version comparison, mock release API
  test_backup_restore.py - backup produces valid archive, restore succeeds
```

## Acceptance Criteria

- Running `curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash` on a clean Ubuntu 22.04
  with Docker installed completes without errors and prints the access URL.
- The wizard generates a `.env` with all required variables populated.
- Answering "yes" to the developer question in the wizard creates `~/.keprix/identity/dev.json`.
- `scripts/check-health.sh` passes after install.
- `keprix update` does not delete any data.
- `keprix rollback` restores the previous state after a failed update.
- `keprix backup` produces a `.tar.gz` that `keprix restore` can import.
- The installer is idempotent: running it twice does not re-initialize the database.
