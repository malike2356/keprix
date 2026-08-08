# Build order: Carina/Aiva consume full Keprix capabilities (516-531)

**Series:** CAS / prompts 516-531
**Status: COMPLETED 2026-08-08**
**Writing style:** plain ASCII only.

## Parallelism rules

1. Do not start CAS-01 until KSF-00 pack registry boundary exists (or land a
   minimal pack registry stub only if foundation is blocked and mark it temporary).
2. CAS-03 and CAS-04 can parallel after CAS-02.
3. CAS-05 requires CAS-02 + CAS-04.
4. CAS-07..09 can parallel after CAS-05 shadow path works; gate live side effects
   behind Soft Wall and feature flags.
5. CAS-15 archives only when core DoD passes; leave Nice/deferred items explicit.

## Recommended sequence

| Wave | Prompts | Outcome |
| --- | --- | --- |
| 0 | 516 | Boundary locked; inventory of existing bridge vs gaps |
| 1 | 517-518 | Pack + northbound contract; legacy bridge remains compatible |
| 2 | 519-520 | Product API + tokens/grants |
| 3 | 521-522 | Chat dual-run then default engine with fallback |
| 4 | 523-525 | Full capability catalog exposed as nodes |
| 5 | 526-527 | Soft Wall UI ownership + memory/events authority |
| 6 | 528-529 | Aiva wrappers + OPS honesty |
| 7 | 530-531 | Security proof, pilot, READY/NOT READY, archive |

## Dependency edges

```
KSF foundation ----\
                    +--> 516 --> 517 --> 518 --> 519
universal sidecar -/                         \
                                              +--> 520 --> 521 --> 522
                                              |
                          523 -- 524 -- 525 --+--> 526 --> 527
                                              |
                                              +--> 528 --> 529 --> 530 --> 531
```

## Contabo note

If any Contabo deploy is touched, verify `https://carinaai.uk/` returns HTTP 200
before ending the session. Prefer product-scoped deploys over full-stack.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
