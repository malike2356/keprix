# Prompt KUS-04: Configured project API connectors and authorised access

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-01, KUS-03, foundation connector prompt
**Blocks:** KUS-05 through KUS-12

## What was built

- Default-deny `ProjectConnector` with operation keys only
- DNS/IP SSRF blocks, idempotent apply, circuit/rate limits

## Goal

Allow Keprix to read or propose actions through declared project APIs without
direct database access, arbitrary HTTP, credential leakage or confused-deputy bugs.

## Must-haves

1. Generic connector compiles only manifest-declared operation keys. A node calls
   `project.read("order.get", params)` rather than supplying method/path/URL.
2. Resolve relative paths against provisioned base URL. Validate scheme/host/port,
   DNS, redirect chain and IP on every connection; block metadata, link-local,
   loopback and private ranges unless explicitly safe for the deployment network.
3. Operation templates have typed parameters and safe encoding. No path traversal,
   query injection, header override, host override or templated authentication.
4. Authentication adapters: bearer/token exchange, OAuth client credentials, mTLS,
   HMAC request signing and custom static header through vault references. No raw
   secret returned to nodes or model prompts.
5. Bounded pagination, projections, time ranges, response bytes, decompression,
   content types and schema validation. Reject unexpected/malformed responses.
6. Separate read, preview/propose and apply operations. Writes require product
   validation, idempotency, current versions and approval evidence where declared.
7. Safe retry matrix by method/operation; circuit breaker; rate/concurrency limits;
   caching only when sensitivity and tenant key permit; correlation and audit.
8. Reverse-connect/agent-pull mode for projects behind NAT: project polls signed
   work requests or holds outbound mTLS stream. It receives no broader grant than
   direct mode and must preserve ordering/idempotency.
9. Provide local mock project server and contract recorder that redacts values and
   generates candidate schemas/config, always requiring human review before apply.
10. Direct SQL, ORM import, admin UI scraping and arbitrary GraphQL query strings
    are out of scope. GraphQL uses named persisted operations if supported later.

## Acceptance

- [x] Model cannot cause undeclared URL or operation call
- [x] Redirect/DNS tests cannot reach metadata or blocked networks
- [x] Read schema mismatch fails without passing content to model
- [x] Write retry cannot duplicate the project action
