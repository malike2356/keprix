# Prompt KSF-00: Product-pack registry and runtime boundary

**Status:** PENDING
**Depends on:** shared product-sidecar contract
**Blocks:** KSF-01 through KSF-04 and all product queues

## Build

1. Extend the existing domain-pack system, not a second plugin framework. Define
   `ProductPackManifest`, compatibility, migrations, signature/checksum, nodes,
   tools, playbooks, events, connector, policies, memory namespaces and health.
2. Stable product keys: `petraclus`, `abbis`, `xeclone`, `fleetz`, `clinicom`,
   plus `carina` and `aiva` for the platform shell queue
   (`keprix-sidecar-carina-aiva/`). Aiva is a soft-separated surface on Carina,
   not a second runtime.
3. Registry supports install, validate, enable, disable, upgrade, rollback, list,
   inspect and health. Invalid/incompatible packs do not partially register.
4. Separate shared runtime services from product code. No product imports another
   product's handlers, schemas, memory or secrets.
5. One request context carries product, deployment, tenant/workspace, actor,
   grants, purpose, correlation, policy and budget through every layer.
6. Capability graph shows product nodes but cannot compose across products unless
   a future explicit federation grant exists. Default is absolute separation.
7. Add config and feature inventory without exposing secrets or hidden live tools.

## Acceptance

- [ ] Five fixture packs coexist without namespace collision
- [ ] Failed pack activation rolls back atomically
- [ ] Disable/kill switch removes invocation immediately
- [ ] Cross-product composition fails closed
