# Propreneur sidecar release-candidate manifest (template)

**Programme:** keprix-propreneur-aiva-three-way (Prompt 10 RC template)
**Contract version:** 1.0.0
**Fill before any Contabo or production cutover.**

## Identity

| Field | Value |
| --- | --- |
| Product | propreneur |
| Keprix pack id | propreneur-sidecar |
| Pack version | 0.1.0 (update per release) |
| Contract version | 1.0.0 |
| Feature flag | product.propreneur.sidecar |
| Memory namespace | product:propreneur |
| Release date | YYYY-MM-DD |
| Owner | |

## Git pins (no dirty worktree)

| Repo / root | Branch | SHA | Notes |
| --- | --- | --- | --- |
| keprix/ | | | Product pack + foundation only |
| propreneur/propreneur-v2/ | | | Bridge / routes / migrations only |
| Contabo deployed SHA | | | Must match push |

Never rsync a dirty workstation tree. Never ship `.env`, credentials, logs,
caches, databases, uploads, or dependency directories.

## Topology

| Environment | Keprix URL | Propreneur API | Notes |
| --- | --- | --- | --- |
| Local | http://127.0.0.1:3333 | PROPRENEUR_PRODUCT_API_URL | Docker compose |
| Contabo | http://127.0.0.1:13333 | host Laravel | Loopback only |

## Configuration keys (names only)

- `PROPRENEUR_PRODUCT_API_URL`
- `KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET`
- Bootstrap shared token alias (document product name; value in vault)
- Soft-wall / engine selection keys as used by Propreneur bridge
- Compatibility aliases for legacy `CARINA_*` names and removal path

## Migrations

List additive Propreneur migrations included in this RC:

1.
2.

## Routes and middleware

List sidecar endpoints and required middleware (auth, CSRF, rate limit):

1.
2.

## Build and test commands

```bash
# Keprix
cd /opt/lampp/htdocs/verlox/keprix
python -m pytest tests/product_sidecar/test_propreneur_pack.py tests/product_sidecar/test_sidecar_foundation.py -q --tb=short

# Propreneur (fill exact filters used for the RC)
cd /opt/lampp/htdocs/verlox/propreneur/propreneur-v2
php artisan test --filter=Keprix
```

## Expected smoke

- [ ] Keprix `/v1/products/propreneur/health` 200
- [ ] Capabilities list includes property/contact/tenancy/deal/task/note/ask_portfolio
- [ ] Provision dry_run plans without mutation
- [ ] Cross-product compose denied
- [ ] Disabling Keprix restores native Propreneur engine path
- [ ] Contabo: https://carinaai.uk/ returns 200 after deploy

## Classification report (attach)

| Path | Class | Include in RC? |
| --- | --- | --- |
| | required / optional / obsolete / generated / secret / runtime / unrelated | yes/no |

## Remaining owner configuration

-
-

## Sign-off

Extracted by ___; reviewed by ___; date ___
