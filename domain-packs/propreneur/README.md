# Keprix Propreneur sidecar pack

UK property MIS pack for Propreneur. Propreneur remains authorization and data
authority. Keprix/Aiva expose versioned tools, event inbox/outbox sync, and
high-risk approval digests.

## Contracts

- `contracts/propreneur-aiva-tools.v1.json` (tool registry)
- `contracts/propreneur-action-risk.v1.json` (shared with Carina + Propreneur PHP)

## Docs

- `docs/propreneur-aiva-capability-guidance.md`
- `docs/propreneur-event-catalogue.md`
- `docs/propreneur-conflict-rules.md`
- Capability honesty self-doc: `keprix/docs/self-knowledge/propreneur-product-pack-honesty.md`
- Operator readiness: `GET /v1/products/propreneur/readiness`

## Product sidecar nodes

Node catalog lives in `src/keprix/product_sidecar/packs/propreneur.py` and is
registered by `ProductPackRegistry`. HTTP-backed CRUD handlers live in
`packs/propreneur_ops.py`. Propreneur remains source of truth at
`/opt/lampp/htdocs/verlox/propreneur`.

## Local check

```bash
cd /opt/lampp/htdocs/verlox/keprix
python3 -m pytest domain-packs/propreneur/tests/test_contract_load.py -q
```
