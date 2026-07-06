# Rejected features

Features classified `unsafe_or_private` in `src/keprix/extraction/inventory.yaml`.
Each entry includes a `rejected_reason`; Keprix must not port these capabilities.

| ID | Feature | Source | Reason |
| --- | --- | --- | --- |
| aiva-keys-service | Aiva Keys and keys.carinaai.uk | `hosted/cloudflare-saas.ts` | Remote licence validation is commercial-only and forbidden on Keprix surfaces. |
| carina-trust-attestation | Blockchain trust attestation | `security/behavior-proof.test.ts` | Enterprise attestation chain is not part of MIT self-host scope. |
| carina-ops-secrets | Production ops secrets reload | `ops/secrets-reload.ts` | Internal operational runbooks and live secret reload are not ported. |
| carina-customer-tenant-store | Multi-tenant customer store | `workers/aiva-subscription-store.ts` | Customer data and private tenant records must never be copied into Keprix. |

## Additional never-port list (from Prompt 00a)

- Managed SaaS billing infrastructure
- Multi-tenant white-label hosting
- In-app Aiva upsell on Keprix surfaces
- `keys.carinaai.uk` integration
- Production customer uploads and backup trees

## Scanner exclusions

The extraction scanner skips:

- `.env` and credential key files (`.pem`, `.key`, `.p12`, `.pfx`)
- Customer data directory names (`tenant-data`, `uploads`, `backups`, etc.)
- `node_modules`, `.git`, build artifacts

If a proposed import triggers secret or customer-data findings, stop and document in this file before proceeding.
