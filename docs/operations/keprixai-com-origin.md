# keprixai.com public origin (Cloudflare + Contabo nginx)

**Audience:** Contabo operators and coding agents  
**Date:** 2026-09-20  
**Status:** Live marketing-only origin. There is **no** hosted Keprix workspace or public API on Contabo.

Public Keprix uses Cloudflare in front of Contabo shared nginx.
This is **not** the Caddy-on-dedicated-VPS path in [VPS deploy](vps-deploy.md).
Do **not** install Keprix Caddy on Contabo ports 80/443 (conflicts with the
shared nginx container). Do **not** bring up `docker-compose.app.yml`,
Postgres, or Redis on Contabo for `keprixai.com`.

The product runs on the operator's machine: [Local web dashboard](../getting-started/dashboard.md).

## Hostname map

| Host | Role | Upstream |
| --- | --- | --- |
| `https://keprixai.com/` | Marketing homepage + `/guide` docs | `keprix-frontend` marketing image |
| `https://www.keprixai.com/` | Redirect to apex | nginx |
| `https://keprixai.com/docs` | In-site docs catalog | same marketing image |
| `https://keprixai.com/install.sh` | curl installer (GitHub clone) | marketing image / static |
| `https://app.keprixai.com/` | Redirect to `https://keprixai.com/docs` | nginx redirect, **not** a workspace |

There is no public `https://app.keprixai.com/api/health` or OpenAPI. Probe the
local dashboard instead (`http://127.0.0.1:9120/home`, API `:9119`).

Nginx sources (canonical in Carina core, not nested under Keprix):

- `carina/02-backends/core.carinaai.uk/docker/nginx/keprixai.com.conf`
- `carina/02-backends/core.carinaai.uk/docker/nginx/app.keprixai.com.conf` (docs redirect)

Carina platform work is on hold. Do not change Carina trees to "fix" Keprix.
Do not take live Carina URLs offline.

## Never break carinaai.uk

Owner hard rule. After any Contabo nginx, compose, or mount change **on the
owner deploy device**, verify:

```bash
curl -fsS -o /dev/null -w 'carina %{http_code}\n' https://carinaai.uk/
curl -fsS -o /dev/null -w 'keprix %{http_code}\n' https://keprixai.com/
```

Expect both `200`. Canonical rule: `shared/workspace-governance/CONTABO-CARINAAI-UK-NEVER-BREAK.md`

## Facts

| Item | Value |
| --- | --- |
| DNS | Cloudflare proxied A for apex, `www`, and `*` -> Contabo |
| SSL (Cloudflare) | Full (origin must speak HTTPS) |
| Shared nginx | Docker service in `core.carinaai.uk` |
| Marketing FE | `keprix/deploy/contabo/docker-compose.marketing.yml` |
| Product stack | **Not deployed.** `docker-compose.app.yml` is unused on Contabo. |

## DNS expectations

Cloudflare zone `keprixai.com`:

- `A` / `AAAA` for apex, `www`, and `*` -> Contabo origin IP, **proxied** (orange cloud)
- `app` is covered by the wildcard; nginx must **redirect** to `/docs`, not proxy a workspace
- Do not point apex at Caddy on another host while Contabo nginx is the intended origin
- Email (MX / SPF / DKIM / DMARC): out of scope here until a mail provider is chosen

## Marketing frontend (live)

Owner-side on Contabo (not from this workstation unless the owner lifts git-first):

```bash
cd /home/malike/apps/keprix
docker compose -f deploy/contabo/docker-compose.marketing.yml up -d --build
```

Agents on the Verlox workstation: commit and `git push origin HEAD`. Stop.
Do not rsync or SSH-deploy to Contabo from here.

## Product stack on app.keprixai.com (not live)

Do not start `docker-compose.app.yml` on Contabo. Do not expect
`https://app.keprixai.com/api/health` to return 200. The workspace is
`keprix dashboard` on the user's machine.

## TLS notes

| Cloudflare mode | Origin cert |
| --- | --- |
| Full | Shared origin cert (current Clinicom-style) is enough |
| Full (strict) | Need a cert whose SAN includes `keprixai.com` / `app.keprixai.com` |

## Git-first deploy

Coding agents: after local build/smoke, commit (no secrets) and
`git push origin HEAD`. Contabo marketing image rebuild is **owner-side**
from another device. Do not rsync from the Verlox workstation.

## Owner checklist

- [x] Marketing apex `https://keprixai.com/` -> 200
- [x] `https://app.keprixai.com/` redirects to docs (not a workspace)
- [x] Contabo compose: marketing image only
- [ ] Do not require `https://app.keprixai.com/api/health` -> 200
- [x] `https://carinaai.uk/` still 200 (do not take it offline)

## Related

- [Local web dashboard](../getting-started/dashboard.md)
- [Cloud deploy](../getting-started/cloud-deploy.md) (Caddy VPS path; not Contabo)
- [VPS deploy](vps-deploy.md)
- [Public GTM gate](readiness.md#public-gtm-gate)
- Never-break: `shared/workspace-governance/CONTABO-CARINAAI-UK-NEVER-BREAK.md`
