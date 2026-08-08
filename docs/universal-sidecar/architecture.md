# Architecture

## Ownership

| Owner | Responsibilities |
| --- | --- |
| **Project (product)** | Users, tenancy, entitlements, business records, UI, side effects |
| **Keprix** | Agent execution, configured capabilities, memory, jobs, policy, approvals, audit |

Keprix never receives unrestricted SQL access and never scrapes product UI routes.

## Deployment modes

1. **personal_os** - single operator, local loopback.
2. **mounted** - sidecar routes on existing Keprix backend (`127.0.0.1:3333`).
3. **sidecar_only** - reduced process on `127.0.0.1:3360`.
4. **dedicated_per_project** - preferred production: one Keprix process per product deployment.
5. **shared_hard_isolated** - shared runtime only after isolation tests prove no cross-project enumeration.

## Identifiers

project, deployment, environment, tenant, actor, session, subject, capability,
run, job, approval, event, artifact.

## Non-goals

- Arbitrary database introspection or SQL passthrough
- UI scraping or browser automation via project manifest
- Anonymous public agent endpoint
- Unrestricted tool proxy or free-form HTTP from the model
- Automatic write authority without declared apply + approval evidence
- Secret values embedded in project manifests
- Inline Python/JavaScript/shell/templates as capability definitions

## Degradation

On Keprix outage the project continues independently. Callbacks queue with a
bounded TTL. Product shutdown must not block on sidecar drain. Readiness is
false while draining.

## Config trust

The manifest *requests* capabilities. Installed runtime policy is the upper
bound. Unknown or denied nodes fail validation honestly.
