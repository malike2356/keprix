# Task / ticket demo (synthetic)

End-to-end flow using synthetic data only:

**read -> summarise -> propose -> approve -> job -> callback**

## Synthetic dataset

| Id | Type | Fields |
| --- | --- | --- |
| `tkt_9001` | support ticket | subject "Refund request", status open, order_id `ord_1001` |
| `ord_1001` | order | status paid, total 42.50 GBP |

## Steps

1. Start `mock-project/server.py` on `:8099` and a Universal Sidecar on `:3360`.
2. Register a manifest based on `read-plus-propose.yaml` plus async job callbacks
   (see `manifest/examples/`).
3. Pair the product (`POST /sidecar/v1/pair/bootstrap`).
4. **Read**: connector `order.get` for `ord_1001`.
5. **Summarise**: `POST .../invoke` node `summarise` with the projected order
   and ticket subject as context.
6. **Propose**: `proposal.prepare` builds a refund proposal (no side effect).
7. **Approve**: product UI (or curl) posts
   `POST .../approvals/{id}/decision` with `decision=approve`.
8. **Job**: `POST .../jobs` runs an async apply/preview step with idempotency
   key `refund-ord_1001`.
9. **Callback**: sidecar posts signed webhook / event to
   `POST /api/keprix/v1/events/ack` on the mock product.

## Notes

- No production credentials.
- Fail closed if approval TTL expires or inputs change.
- Product remains usable if the sidecar is stopped mid-job; resume or dead-
  letter according to job policy.
