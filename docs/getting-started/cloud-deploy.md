# Cloud deploy

**Primary path:** [VPS deploy](../operations/vps-deploy.md) with Docker Compose + Caddy via `scripts/deploy-keprix-production.sh`.

Contabo shared-nginx / marketing-origin patterns differ from this Caddy-only VPS path.
See [keprixai.com origin (Cloudflare + Contabo)](../operations/keprixai-com-origin.md).
Do not treat Contabo as identical to the Caddy deploy below. Do not install Keprix
Caddy on Contabo 80/443.

## Recommended

```bash
bash scripts/generate-production-env.sh --domain https://app.example.com
bash scripts/deploy-keprix-production.sh --bootstrap --domain app.example.com --skip-scout
```

Keep `BACKEND_BIND=127.0.0.1` and `FRONTEND_BIND=127.0.0.1`. TLS at Caddy (`deploy/Caddyfile` / template).

## DigitalOcean

```bash
bash scripts/bootstrap-do-droplet.sh \
  --domain app.example.com \
  --email you@example.com \
  --ssh-key "your-do-ssh-key-name" \
  --ref v0.16.0
```

Requires a DO SSH key. Cloud-init installs Docker + Caddy from apt repos, clones a pinned ref, and runs the production path. It does **not** pipe `install.sh` from the network.

## Fly.io (optional helper)

Not one-click. Use `fly.fullstack.toml` after creating Postgres, Redis, volume, and secrets. See file header. Backend-only sketch: `fly.backend-only.toml`.

```bash
bash scripts/deploy-managed.sh fly
```

## Verified install

See [Release signing](../security/release-signing.md). The curl installer is the public CLI path for workstations; production VPS uses the deploy scripts above and does not require piping `install.sh` on the server.

## Canary

```bash
bash scripts/deploy-keprix-production.sh --domain app.example.com --canary --tag v0.16.1 --skip-scout
```

## Post-deploy

[First run](first-run.md), [Hardening](../security/hardening.md).
