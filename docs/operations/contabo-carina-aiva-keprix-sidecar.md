# Contabo: enable Keprix as Carina/Aiva sidecar + OPS control

**Audience:** Contabo operators  
**Date:** 2026-08-08  
**Writing style:** plain ASCII only.

## Scope

Wire **Carina / Aiva** agent brain to Contabo Keprix (`keprix-backend` on the
shared `proxy` network). Control and monitor from **Carina OPS** Agent Engine GUI.

**Out of scope:** Clinicom. Leave `CLINICOM_SIDECAR_PROFILE=carina` unless the
owner explicitly runs Clinicom `switch-sidecar.sh keprix`.

## GUI (preferred day-2)

| Task | Where |
| --- | --- |
| Login Keprix admin | https://app.keprixai.com/auth/login |
| Connect Scout | Keprix Settings > Governance |
| Switch Carina/Aiva brain | https://ops.carinaai.uk/agent-engine (Global engine = keprix) |
| Set Keprix URL | Same OPS page (Keprix URL field); prefer `http://keprix-backend:3333` |
| Emergency rollback | OPS Agent Engine > type `SWITCH_ALL_TO_CARINA` |
| Sidecar project kill | Keprix Settings > Sidecars |

Shared token for OPS probes still lives in Contabo env once (operator set-and-forget).
After that, engine flips are GUI-only.

## One-time Contabo wiring

1. Shared token on Keprix `.env` and Carina core `.env` (same value):
   - `CARINA_KEPRIX_SHARED_TOKEN=...`
   - `KEPRIX_CARINA_SHARED_TOKEN=...` (Keprix twin)
2. Carina: `CARINA_KEPRIX_URL=http://keprix-backend:3333`
3. Recreate/reload Carina web/ops containers that read those env vars.
4. Sync nginx `app.keprixai.com.conf` (includes `/v1/`) and reload nginx.
5. OPS: set Global engine `keprix`, Save; confirm health `healthy` and
   `keprix_primary_invoke_ok`.

## Verify

```bash
curl -fsS -o /dev/null -w 'carinaai.uk %{http_code}\n' https://carinaai.uk/
curl -fsS -o /dev/null -w 'app %{http_code}\n' https://app.keprixai.com/api/health
curl -fsS -o /dev/null -w 'v1-carina %{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  https://app.keprixai.com/v1/products/carina/health
curl -fsS -o /dev/null -w 'v1-aiva %{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  https://app.keprixai.com/v1/products/aiva/health
curl -fsS https://clinicomai.com/api/health   # expect provider.profile=carina
```

Live Contabo check (2026-08-08): OPS `/api/ops/agent-engine/health` returns
`engine=keprix`, `status=healthy`, `keprix_primary_invoke_ok=true`. Public `/v1`
for carina and aiva returns 200. Clinicom stays on Carina.

## Rollback (Carina/Aiva only)

OPS emergency rollback, or set Global engine to `carina`. Do not run Clinicom
switch scripts as part of this rollback.
