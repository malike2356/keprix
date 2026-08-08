# Keprix multi-product sidecar foundation

**Status:** PENDING
**Contract:** `../ref-keprix-product-sidecar-contract.md`

Build once before product packs depend on it:

1. `00-product-pack-registry-and-runtime-boundary.md`
2. `01-northbound-http-capability-and-node-api.md`
3. `02-southbound-connectors-identity-and-grants.md`
4. `03-provisioning-events-jobs-resilience-and-operations.md`
5. `04-security-isolation-contract-tests-and-release.md`

This is platform plumbing only. Product-specific schemas, data, personas, tools,
policy and deployment decisions remain in the separate product queues
(including `keprix-sidecar-carina-aiva/` for Carina/Aiva full-capability consumption).
