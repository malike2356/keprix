# Petraclus Keprix module

Product key: `petraclus`. Contract `1.0.0`. Pack `0.1.0`. Port **3362**.

**Status:** Petraclus was merged into Keprix on 2026-08-31 by owner decision.
This directory is the active runtime module and domain pack. Former standalone
planning, prompts, academy, legal, and purple material now lives at
`keprix/apps-on-keprix/petraclus/`.

## Boundary

- **Petraclus module owns:** targets, authorisation evidence, finding truth,
  workflows, licences, UI, academy material, and legal/product policy.
- **Keprix owns:** agent runtime, reasoning, grounded explanation, proposed
  prioritisation, playbooks, policy-gated tools, domain pack loading, and module
  operations.
- Licence authority: `keys.petraclus.uk` (product-side). Keprix never mints or unlocks licences.

## Run locally

```bash
bash scripts/provision-local.sh
bash scripts/start-petraclus-sidecar.sh
curl -s http://127.0.0.1:3362/v1/products/petraclus/health
```

Fixture product API: `/fixture-product/api/keprix/v1/*`.

## Tests

```bash
cd <workspace-root>/keprix
.venv/bin/python -m pytest domain-packs/petraclus/tests -q
```

## Hard denies

No shell, arbitrary HTTP, free-form nmap, exploit-run, credential-read, unrestricted file-read, or remediation-execute nodes. Exploit automation is off.
