# Machine-readable product discovery rules

1. Every public marketing page must include JSON-LD (`SoftwareApplication` at
   minimum) via the shared product discovery graph.
2. `productSpec.json` is the single source of truth for agent filters. Update
   `keprix.product_discovery.spec` whenever features or pricing change, then
   regenerate static files with `python -m keprix.product_discovery.export_static`.
3. Pricing in structured data must use numeric `amountMajor` / `amountMinor`
   fields. Never rely on HTML copy for agent buy decisions.
4. Do not claim security certifications (for example SOC 2) unless Verlox has
   an active attestation on file.
5. Run the LLM auditor monthly (`POST /api/discovery/llm-audit?dry_run=false`
   with provider keys) and store the visibility report under
   `docs/operations/discovery-reports/`.
6. Keep `install.json`, `llms.txt`, and `/.well-known/keprix.json` in sync with
   the Python builders.
