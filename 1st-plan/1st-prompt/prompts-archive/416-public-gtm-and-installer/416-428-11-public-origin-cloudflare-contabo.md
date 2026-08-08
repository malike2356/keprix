# Prompt 427 / 11: Public origin (Cloudflare + Contabo nginx marketing FE)

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 424  
Blocks: 428  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Document and (when owner approves implementation) wire the **public marketing
origin** for `keprixai.com` on Contabo using the shared Carina nginx pattern,
without requiring the full Keprix API stack on day one.

## Facts (2026-08-07)

- Cloudflare DNS: `keprixai.com`, `www`, `*` A -> `80.190.81.208` proxied.
- SSL mode Full: origin must speak HTTPS.
- Contabo shared nginx (`corecarinaaiuk-nginx-1`) has **no** `keprixai.com`
  server_name; requests 520.
- Frontend is separable from backend for marketing routes (home, docs shell,
  legal). Workspace/API need backend later.
- Do **not** install Keprix Caddy on Contabo :80/:443 (conflicts with shared
  nginx). Do **not** break `https://carinaai.uk/` (verify 200 after changes).

## Tasks

1. Write `docs/operations/keprixai-com-origin.md`:
   - DNS expectations (Cloudflare proxied A records).
   - Preferred Contabo pattern: nginx conf like `clinicomai.com.conf`, proxy to
     `keprix-frontend:3000` on docker network `corecarinaaiuk_carina` or `proxy`.
   - Marketing-only compose overlay: run `keprix-frontend` without requiring
     healthy backend **or** run full stack bound to localhost and proxy FE.
   - TLS: Cloudflare Full can use existing origin cert pattern (document
     clinicom-style shared cert vs dedicated `keprixai.com` cert).
   - Post-deploy: `curl -fsS -o /dev/null -w '%{http_code}\n' https://keprixai.com/`
     expects 200; also verify `https://carinaai.uk/` is 200.
2. Add nginx config source under the Contabo/core nginx tree used for other
   products (canonical: `carina/02-backends/core.carinaai.uk/docker/nginx/`)
   **only if** this workspace is where Contabo nginx configs are maintained.
   File suggestion: `keprixai.com.conf`. Keep Keprix product repo docs pointing
   at that path; do not nest Carina under Keprix.
3. Optional implementation in same session if owner says "deploy now":
   - Build/push or build on VPS frontend image.
   - Attach to nginx network.
   - Reload nginx safely.
   - Verify keprixai.com + carinaai.uk.
4. If implementation deferred, sign-off (428) lists origin as OPEN with doc done.

## Acceptance

- [x] Origin runbook exists and is accurate.
- [x] No Caddy-on-Contabo instruction for this host.
- [x] carinaai.uk never-break rule is explicit in the runbook.
- [x] Frontend-only vs full-stack options are both described.

## What was built

- `docs/operations/keprixai-com-origin.md` runbook (DNS, TLS, Options A/B,
  never-break, post-deploy curls).
- Canonical nginx vhost: `carina/02-backends/core.carinaai.uk/docker/nginx/keprixai.com.conf`.
- Marketing compose: `keprix/deploy/contabo/docker-compose.marketing.yml` + README.
- Cross-links from cloud-deploy, readiness, deploy/README.
- **Live Contabo deploy deferred** (owner must say "deploy now"); origin remains OPEN for 428.

## Verification

```bash
test -s docs/operations/keprixai-com-origin.md
rg -n 'carinaai\\.uk|keprixai\\.com|520|Full' docs/operations/keprixai-com-origin.md
# If deployed:
curl -fsS -o /dev/null -w 'keprix %{http_code}\n' https://keprixai.com/ || true
curl -fsS -o /dev/null -w 'carina %{http_code}\n' https://carinaai.uk/
```

## Out of scope

- MX/SPF/DKIM/DMARC (note only).
- Switching Clinicom sidecar profiles.
