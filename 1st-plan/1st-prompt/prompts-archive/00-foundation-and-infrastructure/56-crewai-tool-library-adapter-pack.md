# keprix - Prompt 56: CrewAI-Style Tool Library Adapter Pack

> **Status (2026-07-05):** Returned from `completed/` to `pending-prompts/`. `ToolAdapter.run()` still returns dry-run placeholders. Wire to agent runtime before re-archiving.

## Context

Adopt the useful tool categories visible in CrewAI's tool library into keprix as native or optional adapters.

Do not blindly vendor third-party code. Build keprix-compatible adapters with clear optional dependencies, setup instructions, feature gates, and approval policies.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/crewai/lib/crewai-tools/src/crewai_tools/tools
```

## Files To Create

```text
backend/tools/adapters/
  __init__.py
  search.py
  scraping.py
  rag_documents.py
  databases.py
  vector_stores.py
  media.py
  code_search.py
  automation.py
  sandboxes.py
  evaluation.py
  registry.py
tests/tools/test_adapter_registry.py
tests/tools/test_search_adapters.py
tests/tools/test_scraping_safety.py
tests/tools/test_database_adapters.py
```

## Tool Categories

### Search

Adapters:

- Brave.
- SerpAPI.
- Serper.
- Serply.
- Tavily.
- Exa.
- Linkup.

Use for:

- Deep research.
- Opportunity discovery.
- Competitor research.
- Citation finding.

### Web Scraping

Adapters:

- Firecrawl.
- Jina.
- ScrapeGraph.
- Scrapfly.
- Spider.
- Selenium.
- Stagehand.
- BrightData.
- Oxylabs.

Guardrails:

- Respect robots and terms where detectable.
- No login bypass.
- No private account scraping.
- Rate limit by domain.
- Store citations and scrape metadata.

### Documents And RAG

Adapters:

- PDF.
- DOCX.
- TXT.
- CSV.
- JSON.
- XML.
- MDX.
- Website search.

Use for:

- Workspace knowledge.
- Domain packs.
- Research reports.

### Databases

Adapters:

- MySQL.
- Snowflake.
- Databricks.
- Couchbase.
- SingleStore.

Default to read-only. Write operations require approval.

### Vector Stores

Adapters:

- Qdrant.
- Weaviate.
- MongoDB vector search.

### Media

Adapters:

- OCR.
- Vision.
- YouTube video search.
- YouTube channel search.
- Image generation bridge.

### Code And Docs Search

Adapters:

- GitHub search.
- Code docs search.
- Directory search.

### Automation

Adapters:

- Zapier action bridge.
- keprix automation generation.
- keprix automation invocation.

Every action bridge must default to dry run unless approved.

### Sandboxes

Adapters:

- E2B.
- Daytona.

Use for:

- Code execution.
- Browser tasks.
- Isolated experiments.

### Evaluation

Adapters:

- Patronus-style eval wrapper.
- Internal keprix eval runner.

## Adapter Interface

Every adapter must declare:

- Name.
- Category.
- Required env vars.
- Risk level.
- Supports dry run.
- Requires approval for write actions.
- Cost estimate support.
- Citation support.

## Acceptance Criteria

- Adapter registry lists all categories.
- Missing optional dependencies produce setup guidance, not crashes.
- Search adapters return citation-ready results.
- Scraping adapters enforce safety policy.
- Database adapters are read-only by default.
- Automation adapters require approval for writes.
- Tests cover setup guidance, risk levels, dry run, and citation metadata.

