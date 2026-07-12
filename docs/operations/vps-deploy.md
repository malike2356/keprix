# VPS deploy (hardened)

**Canonical production path:** Docker Compose + Caddy via `scripts/deploy-keprix-production.sh`.

Optional helpers (use only when needed):

| Helper | Role |
| --- | --- |
| `scripts/deploy-server.sh` | Low-level fail-closed steps called by production |
| `scripts/deploy-canary.sh` | Canary → health → flip Caddy → promote |
| `scripts/bootstrap-do-droplet.sh` | DigitalOcean provision (SSH key, UFW, Caddy) |
| `scripts/deploy-managed.sh` | Thin wrapper (Fly fullstack / DO bootstrap) |
| `fly.fullstack.toml` | Optional Fly recipe (Postgres/Redis/volume required) |

## One runtime story

| Profile | When to use | Process |
| --- | --- | --- |
| **compose** (recommended) | Full stack on a VPS | Docker: `uvicorn keprix.api.main:app` + Next + Postgres + Redis |
| **systemd** (bare-metal API) | API only | `deploy/keprix.service` on `127.0.0.1:3333` |

Do not expose `0.0.0.0:3333` publicly. Terminate TLS at Caddy; keep binds on `127.0.0.1`.

## First-time bootstrap

```bash
bash scripts/generate-production-env.sh --domain https://app.example.com
bash scripts/deploy-keprix-production.sh --bootstrap --domain app.example.com --skip-scout
# later deploys
bash scripts/deploy-keprix-production.sh --ref v0.16.0 --skip-scout
# canary
bash scripts/deploy-keprix-production.sh --domain app.example.com --canary --tag v0.16.1 --skip-scout
```

DigitalOcean (SSH key required; no curl|bash install):

```bash
bash scripts/bootstrap-do-droplet.sh \
  --domain app.example.com \
  --email you@example.com \
  --ssh-key "my-laptop" \
  --ref v0.16.0
```

## Verified install (no raw pipe)

```bash
bash scripts/install-verified.sh --version v0.16.0
# or
bash scripts/install-verified.sh --from-git --ref v0.16.0
```

`scripts/install-curl.sh` refuses unsafe curl|bash unless `KEPRIX_ALLOW_UNSAFE_CURL_BASH=1`.

## Canary

1. Start canary on `127.0.0.1:3001` / `:3334`
2. Health-check canary
3. Point Caddy at canary
4. Promote images to live ports `3000` / `3333`
5. Flip Caddy back to live; stop canary

## Fail-closed steps

`deploy-server.sh` (used by production): pull → doctor → smoke → backup → migrate → restart → health.

## Production compose overlay

```bash
cd docker
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Fly (optional)

Not one-click. See `fly.fullstack.toml` header: create app, attach Postgres + Redis, create volume, set secrets, then `fly deploy -c fly.fullstack.toml`. Backend-only sketch: `fly.backend-only.toml`.

## Rollback

```bash
bash scripts/deploy-keprix-production.sh --ref v0.15.2 --skip-scout
KEPRIX_IMAGE_TAG=v0.15.2 bash scripts/deploy-keprix-production.sh --skip-scout
```

## Trusted proxies / secrets

See [Hardening](../security/hardening.md). Set `KEPRIX_TRUSTED_PROXIES=127.0.0.1,::1` behind local Caddy.

## Related

- [Cloud deploy](../getting-started/cloud-deploy.md)
- [Hardening](../security/hardening.md)
- [Backup](backup.md)
- [Release signing](../security/release-signing.md)
