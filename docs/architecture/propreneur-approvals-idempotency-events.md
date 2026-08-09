# Propreneur Soft Wall, idempotency, events, and reconciliation

Prompt 641 control-plane notes (2026-08-09).

## Soft Wall ownership

One durable `ApprovalStore` under `KEPRIX_DATA_DIR/product_sidecar/approvals.json` is the Soft Wall bus for both `/v1/products/propreneur/invoke` and the chat tool adapter.

Lifecycle: `pending` → `approved` | `rejected` | `expired` | `revoked`.

- Same product/workspace/node/`input_hash` reuses one pending approval (no duplicate Soft Walls).
- Digest excludes control keys (`approval_id`, `idempotency_key`, `etag`/`if_match`, correlation).
- Deep link: `/propreneur/soft-wall?approval_id=...&kind=...`
- Status API: `GET /v1/products/propreneur/approvals/{id}?workspace_id=...`
- Decide / revoke / expire: `POST .../decision|revoke|expire`

Elevated mutate/archive/propose nodes remain Soft Wall gated via pack `soft_wall` flags.

## Idempotency

`IdempotencyLedger` is tenant-scoped: key = `product:workspace_id:Idempotency-Key`.

Fingerprint stores operation + actor + workspace + input hash. Reuse with a different fingerprint returns `conflict` / `idempotency_fingerprint_mismatch` with safe retry guidance. Matching reuse replays the stored envelope (no second upstream write).

## Optimistic concurrency

`TrustedExecutionContext.if_match` forwards as `If-Match`. Conflicts map to envelope `status=conflict` with retry guidance to refresh etag.

## Events and echo suppression

`POST /v1/products/{product}/events` remains the Keprix inbox. Events with `causation_id` starting `keprix:` (or `echo_of_keprix_mutation=true`) are accepted as echo-suppressed and not projected again. `POST .../events/{id}/ack` marks acknowledgement. Dedup is by `(product, deployment, event_id)`.

Keprix mutations stamp `causation_id=keprix:{correlation}:{node}` on a control-plane event and on the execution receipt.

## Drift detection

`POST /v1/products/{product}/projections/drift` compares contract-visible records to Keprix projections and returns repair actions only. `silent_overwrite` is always false; Propreneur remains source of truth.

## Execution receipts

Redacted receipts in `execution_receipts.json` link workspace, node, approval, record id, correlation/conversation, path/method, and result summary. Listed at `GET /v1/products/{product}/receipts?workspace_id=...`.

## Tests

`keprix/tests/product_sidecar/test_propreneur_approvals_idempotency_events.py` covers approve, reject, expire, revoke, retry, duplicate callback, duplicate event, echo suppress, conflict, and drift.
