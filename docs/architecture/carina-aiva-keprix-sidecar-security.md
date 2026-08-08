# Carina/Aiva Keprix sidecar security evidence

**Status:** CAS-14
**Date:** 2026-08-08
**Writing style:** plain ASCII only.

## Gate summary

Automated suite: `tests/product_sidecar/test_carina_aiva_sidecar.py`.

| Control | Evidence |
| --- | --- |
| Unknown node denied | `shell.exec` -> 404 |
| Cross-tenant invoke | token ws-a cannot invoke ws-b |
| Missing grant | enroll without grant -> 403 |
| Soft Wall cannot self-approve | forged approval_id still soft_wall_required |
| Pack/node kill | disable pack/node blocks invoke |
| Event dedupe | same event id -> deduped |
| Job cancel idempotent | double cancel stays cancelled |
| Connector default deny | `/admin/secret` denied |
| Context projection | password/token stripped |
| Shadow no outbound | outreach shadow blocked |
| Retention delete | workspace memory removed |
| Cross-workspace export | denied |

## Residual risks (honest)

1. Legacy shared-token compat still grants `*` until exchange cutover completes.
2. Some CRM enroll paths depend on live CRM store wiring; tests accept deferred enroll detail after Soft Wall.
3. Southbound live HTTP requires `CARINA_PRODUCT_API_URL`; fixture mode used when unset.
4. Prompt-injection beyond Soft Wall self-approve needs ongoing eval set expansion.
5. Contabo marketing health is an ops verify step, not covered by this unit suite.

## No arbitrary code nodes

Catalog does not advertise shell, browser, or arbitrary code nodes for Carina/Aiva.
