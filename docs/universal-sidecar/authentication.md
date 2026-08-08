# Authentication

## Pairing

1. Operator creates a one-time pairing code bound to `project_key` and requested
   scopes (UI: Settings > Sidecars, or admin API).
2. Product calls `POST /sidecar/v1/pair/bootstrap` with the code and its
   workload identity metadata.
3. Sidecar returns a bootstrap receipt and short-lived credentials. Bootstrap
   secrets live in the Keprix vault, never in manifests or product rows.
4. Product exchanges bootstrap for short-lived workload tokens before each
   session or batch of invokes.

## Workload tokens

Claims include: product/project, deployment, environment, tenant, actor, grants,
purpose, session, audience, issue/expiry, key id (`kid`).

Validate: issuer, audience (`keprix-universal-sidecar`), signature, expiry,
revocation, and replay (`jti`).

## Auth profiles (manifest)

| Profile | Use |
| --- | --- |
| `bearer` | `Authorization: Bearer` with vault/env ref |
| `oauth_client_credentials` | Client credentials exchange |
| `mtls` | Mutual TLS between product and sidecar |
| `hmac` | Signed requests |
| `static_header` | Named header from vault ref |

## Scopes

Catalog includes: `discover`, `jobs`, `events`, `approvals`, `metrics`,
`files`, `administration`, plus patterns `invoke:{node}`, `connector:{op}`,
`memory:{ns/action}`.

High-risk scopes (administration, files, apply connectors, shell/network/code
invoke) require explicit grants and often approvals.

## Headers on every request

- `Authorization`
- Correlation id
- Tenant / workspace id
- Actor id
- Purpose
- Requested capability (when invoking)
