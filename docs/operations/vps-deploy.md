# VPS deploy (Compose + Caddy)

Canonical production path for a single VPS: Docker Compose for the app stack, Caddy for TLS, orchestrated by `scripts/deploy-keprix-production.sh`.

For a shorter overview and cloud helpers (DigitalOcean, Fly), see [Cloud deploy](../getting-started/cloud-deploy.md).

## Prerequisites

- Ubuntu-class Linux host with Docker and Docker Compose
- DNS A/AAAA for your public hostname pointing at the host
- Ports 80/443 reachable for Caddy ACME
- Repo checkout (or a pinned ref from bootstrap)

Keep `BACKEND_BIND=127.0.0.1` and `FRONTEND_BIND=127.0.0.1` so only Caddy (or another local reverse proxy) terminates TLS.

## 1. Generate production `.env`

Never leave `GENERATE_RANDOM_*`, `REPLACE_ME*`, or `changeme` values on a public host.

```bash
bash scripts/generate-production-env.sh --domain https://app.example.com
```

This copies `.env.example` when needed, writes strong secrets (values are not printed), sets DB/Redis URLs, and pins `KEPRIX_INSTANCE_URL` / `KEPRIX_ALLOWED_ORIGINS` / `KEPRIX_FRONTEND_URL` from `--domain`.

Review `.env` before deploy. Rotate `KEPRIX_ADMIN_PASSWORD` via your secret store if you need a known value after generation.

## 2. Bootstrap (first host)

Install Caddy, firewall/timers as implemented by `deploy-server.sh`, then deploy:

```bash
bash scripts/deploy-keprix-production.sh \
  --bootstrap \
  --domain app.example.com \
  --skip-scout
```

`--bootstrap` requires `--domain`. Omit `--skip-scout` when Scout is configured and you want the post-deploy security audit, Scout tests, and `keprix scout ping`.

## 3. Rolling deploy (existing host)

After `.env` exists and secrets are real:

```bash
bash scripts/deploy-keprix-production.sh --domain app.example.com --skip-scout
```

Optional flags (passed through to the server deploy path where applicable):

| Flag | Purpose |
| --- | --- |
| `--tag TAG` | Image / release tag (non-canary skips pull when tag set) |
| `--ref REF` | Git ref for `deploy-server` pull |
| `--skip-scout` | Skip Scout audit/tests/ping |
| `--skip-tests`, `--skip-pull`, `--skip-migrate`, `--skip-backup` | Server-path shortcuts |

The script refuses to start if `.env` is missing or still contains placeholder secrets.

## 4. Canary

Requires both `--domain` and `--tag`. Runs `scripts/deploy-canary.sh` instead of a rolling server deploy:

```bash
bash scripts/deploy-keprix-production.sh \
  --domain app.example.com \
  --canary \
  --tag v0.16.1 \
  --skip-scout
```

## 5. Health gate

On success the script curls local health:

```bash
curl -fsS "http://127.0.0.1:${BACKEND_PORT:-3333}/api/health"
```

## TLS / Caddy

TLS is terminated at Caddy (`deploy/Caddyfile` or its template). Compose services stay on loopback; do not expose Postgres or Redis on the public interface.

## Optional helpers (not the primary path)

| Script | Role |
| --- | --- |
| `scripts/deploy-server.sh` | Low-level fail-closed Compose steps |
| `scripts/deploy-managed.sh` | Fly / droplet wrappers |
| `scripts/bootstrap-do-droplet.sh` | DigitalOcean provisioning + pinned ref |

DigitalOcean example (does not pipe `install.sh` from the network):

```bash
bash scripts/bootstrap-do-droplet.sh \
  --domain app.example.com \
  --email you@example.com \
  --ssh-key "your-do-ssh-key-name" \
  --ref v0.16.0
```

## Post-deploy

1. [First run](../getting-started/first-run.md): admin account, LLM provider, optional channels
2. [Hardening](../security/hardening.md): secrets, binds, 2FA, backups
3. [Readiness](readiness.md): `keprix readiness` and Admin > Readiness
4. [Backup](backup.md): schedule hot backups before upgrades

## Related

- [Cloud deploy](../getting-started/cloud-deploy.md)
- [Docker Compose](../configuration/docker-compose.md)
- [Environment variables](../configuration/environment-variables.md)
- [Release signing](../security/release-signing.md)
