# Machine-readable product discovery

Keprix publishes structured product data so AI agents can discover, filter, and
install the product without scraping HTML.

## Source of truth

`src/keprix/product_discovery/spec.py` feeds:

| Artifact | URL (marketing / app) |
| --- | --- |
| Product spec | `https://keprixai.com/productSpec.json` |
| Install manifest | `https://keprixai.com/install.json` |
| JSON-LD schema | `https://app.keprixai.com/api/product-schema.json` |
| llms.txt | `https://keprixai.com/llms.txt` |
| Well-known card | `https://keprixai.com/.well-known/keprix.json` |

Regenerate static marketing files after pricing/feature changes:

```bash
python -m keprix.product_discovery.export_static
```

## Agent filter API

`POST /api/discovery/evaluate` with JSON criteria such as:

```json
{
  "maxMonthlyAmountMajor": 50,
  "currency": "GBP",
  "requireSso": false,
  "requireCompliance": ["GDPR"]
}
```

Pricing uses numeric `amountMajor` / `amountMinor` fields only.

## LLM visibility auditor

```bash
# dry-run (default): no provider spend
curl -X POST 'https://app.keprixai.com/api/discovery/llm-audit?dry_run=true'

# live probes (needs OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY)
curl -X POST 'https://app.keprixai.com/api/discovery/llm-audit?dry_run=false'
```

Run monthly and archive reports under `docs/operations/discovery-reports/`.

## Rules

See `src/keprix/product_discovery/AGENTS.md`.
