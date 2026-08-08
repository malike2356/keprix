# keprixai.com public origin (Cloudflare + Contabo nginx)

**Audience:** Contabo operators  
**Date:** 2026-08-07  
**Status:** Live Contabo marketing origin (HTTP 200). Product stack on `app.keprixai.com` is the next Contabo step.

Public Keprix uses Cloudflare in front of Contabo shared nginx.
This is **not** the Caddy-on-dedicated-VPS path in [VPS deploy](vps-deploy.md).
Do **not** install Keprix Caddy on Contabo ports 80/443 (conflicts with the
shared Carina nginx container).

## Hostname map

| Host | Role | Upstream |
| --- | --- | --- |
| `https://keprixai.com/` | Marketing homepage | `keprix-frontend:3000` |
| `https://www.keprixai.com/` | Redirect to apex | nginx |
| `https://app.keprixai.com/` | Workspace Web UI | `keprix-frontend:3000` |
| `https://app.keprixai.com/api/` | Backend / OpenAPI API | `keprix-backend:3333` |
| `https://app.keprixai.com/openapi.json` | OpenAPI | `keprix-backend:3333` |

Same-origin browser calls: empty `NEXT_PUBLIC_*` API URL on the FE; nginx (and Next rewrite) talk to the backend on the Docker network. No separate `api.` host required for day one.

Nginx sources (canonical in Carina core, not nested under Keprix):

- `carina/02-backends/core.carinaai.uk/docker/nginx/keprixai.com.conf`
- `carina/02-backends/core.carinaai.uk/docker/nginx/app.keprixai.com.conf`

## Never break carinaai.uk

Owner hard rule. After any Contabo nginx, compose, or mount change in this
session, verify:

```bash
curl -fsS -o /dev/null -w 'carina %{http_code}\n' https://carinaai.uk/
curl -fsS -o /dev/null -w 'keprix %{http_code}\n' https://keprixai.com/
```

Expect both `200`. If carinaai.uk is not 200, repair before ending the session:

```bash
ssh malike@80.190.81.208 'cd /home/malike/apps/core.carinaai.uk && bash docker/scripts/reload-marketing-nginx.sh && CARINA_MARKETING_AUTO_RELOAD=1 bash docker/scripts/check-carina-marketing.sh'
```

Canonical rule: `shared/workspace-governance/CONTABO-CARINAAI-UK-NEVER-BREAK.md`

## Facts

| Item | Value |
| --- | --- |
| DNS | Cloudflare proxied A for apex, `www`, and `*` -> Contabo `80.190.81.208` |
| SSL (Cloudflare) | Full (origin must speak HTTPS) |
| Shared nginx | Docker service in `core.carinaai.uk` |
| Marketing FE | `keprix/deploy/contabo/docker-compose.marketing.yml` |
| Product stack | `keprix/deploy/contabo/docker-compose.app.yml` (FE + backend + Postgres + Redis on `proxy`) |

## DNS expectations

Cloudflare zone `keprixai.com`:

- `A` / `AAAA` for apex, `www`, and `*` -> Contabo origin IP, **proxied** (orange cloud)
- `app` is covered by the wildcard; optional explicit `app` A record is fine
- Do not point apex at Caddy on another host while Contabo nginx is the intended origin
- Email (MX / SPF / DKIM / DMARC): out of scope here until a mail provider is chosen

## Option A: Marketing-only frontend (live today)

```bash
cd /home/malike/apps/keprix
docker compose -f deploy/contabo/docker-compose.marketing.yml up -d --build
```

Sync and reload:

```bash
# From workstation: rsync nginx confs into Contabo core tree
# Then on Contabo:
cd /home/malike/apps/core.carinaai.uk
docker exec corecarinaaiuk-nginx-1 nginx -t
docker exec corecarinaaiuk-nginx-1 nginx -s reload
```

## Option B: Product stack on app.keprixai.com

1. Stop marketing-only compose if it owns `keprix-frontend` alone (app compose reuses that name).
2. Ensure Contabo `/home/malike/apps/keprix/.env` has at least `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, and auth admin settings. Set `KEPRIX_PUBLIC_BASE_URL=https://app.keprixai.com`.
3. Bring up the app stack:

```bash
cd /home/malike/apps/keprix
docker compose -f deploy/contabo/docker-compose.app.yml up -d --build
```

4. Sync both nginx confs (apex marketing narrowed; `app.keprixai.com.conf` added). Reload nginx.
5. Verify:

```bash
curl -fsS -o /dev/null -w 'apex %{http_code}\n' https://keprixai.com/
curl -fsS -o /dev/null -w 'app %{http_code}\n' https://app.keprixai.com/
curl -fsS -o /dev/null -w 'api %{http_code}\n' https://app.keprixai.com/api/health
curl -fsS -o /dev/null -w 'carina %{http_code}\n' https://carinaai.uk/
```

Expect apex/app/carina `200`, api health `200`.

## TLS notes

| Cloudflare mode | Origin cert |
| --- | --- |
| Full | Shared `carinaai.uk` origin cert (current Clinicom-style) is enough |
| Full (strict) | Need a cert whose SAN includes `keprixai.com` / `app.keprixai.com` |

## 3-way deploy reminder

Coding agents: after local build/smoke, commit + push `keprix/` then rsync + Contabo app compose rebuild. Do not leave changes local-only. Canonical: `shared/workspace-governance/THREE-WAY-DEPLOY.md`.

## Owner checklist

- [x] Marketing apex `https://keprixai.com/` -> 200
- [x] Nginx sources for apex + `app.keprixai.com` in Carina core tree
- [x] Contabo compose: `docker-compose.marketing.yml` + `docker-compose.app.yml`
- [x] Sync nginx confs to Contabo and reload
- [x] Bring up `docker-compose.app.yml` with production `.env`
- [x] `https://app.keprixai.com/api/health` -> 200
- [x] `https://carinaai.uk/` still 200

## Related

- [Cloud deploy](../getting-started/cloud-deploy.md) (Caddy VPS path; not Contabo)
- [VPS deploy](vps-deploy.md)
- [Public GTM gate](readiness.md#public-gtm-gate)
- Never-break: `shared/workspace-governance/CONTABO-CARINAAI-UK-NEVER-BREAK.md`
