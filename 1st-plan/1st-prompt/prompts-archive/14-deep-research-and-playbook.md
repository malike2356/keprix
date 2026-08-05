# keprix - Prompt 14: Deep Research and Local Model Playbook

**Status:** Completed. Implementation in `src/keprix/research/`, `src/keprix/playbook/`,
`src/keprix/compare/`, wired frontend pages, and `tests/{research,playbook,compare}/`.

## Context

Sources:
- `odysseus/routes/research_routes.py` - Deep Research
- `odysseus/routes/search_routes.py` - web search
- `odysseus/routes/compare_routes.py` - blind model comparison
- `odysseus/routes/playbook_routes.py`, `playbook_helpers.py`, `playbook_output.py`
- `odysseus/routes/model_routes.py` - model management
- `odysseus/routes/hwfit_routes.py` - hardware fitness
- `core.carinaai.uk/src/research/` - Aiva (commercial) research module
Output: `keprix/backend/research/`, `keprix/backend/playbook/`

## Deep Research

Deep Research is a multi-step autonomous research pipeline. The agent:
1. Decomposes the user's question into 5-10 sub-questions
2. Searches the web for each sub-question (SearXNG or configured search backend)
3. Fetches and reads the top 3 sources per sub-question
4. Synthesizes findings across all sources
5. Generates a structured report with citations

### Port from Odysseus

```
routes/research_routes.py     -> backend/research/routes.py
routes/search_routes.py       -> backend/research/search_routes.py
```

### API Endpoints

```
POST   /api/research/start           - start a deep research job
       Body: { "query": str, "depth": "quick|standard|deep", "model": str? }
       Returns: { "job_id": str, "status": "running" }

GET    /api/research/jobs/{id}        - get job status + partial results
GET    /api/research/jobs             - list past research jobs
GET    /api/research/jobs/{id}/report - get final report (Markdown)
DELETE /api/research/jobs/{id}        - cancel/delete job

POST   /api/search                    - single web search (not multi-step)
       Body: { "query": str, "backend": "searxng|exa|parallel|firecrawl|tavily" }
```

### Research Job Schema

```sql
CREATE TABLE research_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    depth TEXT NOT NULL DEFAULT 'standard',
    status TEXT NOT NULL DEFAULT 'running',
    sub_questions JSONB DEFAULT '[]',
    sources JSONB DEFAULT '[]',
    report_markdown TEXT,
    model_used TEXT,
    tokens_used INT DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX ON research_jobs (user_id, started_at DESC);
```

### Research Depths

- `quick`: 5 sub-questions, top 2 sources each, ~500-word report
- `standard`: 8 sub-questions, top 3 sources each, ~1500-word report
- `deep`: 12 sub-questions, top 5 sources each, ~3000-word report with sections

From Odysseus ROADMAP, also implement:
- Hardware-aware model presets for Deep Research (small/medium/large local setup)
- Per-depth model recommendations shown in the UI before starting

### Source Reading

For each search result URL:
1. Fetch via `web_fetch` tool (with SSRF protection from Prompt 05)
2. Extract text using `trafilatura` (preferred) or `beautifulsoup4` fallback
3. Truncate to first 4000 tokens
4. Feed to the synthesis LLM with citation tag

### Streaming Progress

Research jobs stream progress via Server-Sent Events:
- `GET /api/research/jobs/{id}/stream` - SSE endpoint
- Events: `sub_question_start`, `source_fetched`, `source_read`, `synthesis_chunk`, `complete`
- Frontend subscribes and shows real-time progress bar

### Report Format

Final report is Markdown with:
- Executive summary (3-5 bullet points)
- Numbered sections for each major finding
- Inline citations: `[1]`, `[2]` etc.
- Sources list at the bottom
- Word count and generation time metadata header

## Blind Model Comparison

From `odysseus/routes/compare_routes.py`:

The Compare feature lets users test two models side-by-side with the same prompt,
without knowing which model is which, then vote on the better response.

```
POST   /api/compare/start            - start comparison
       Body: { "prompt": str, "model_a": str?, "model_b": str? }
       If models not specified, pick two randomly from configured providers.
       Returns: { "comparison_id": str, "response_a": str, "response_b": str }

POST   /api/compare/{id}/vote        - record vote
       Body: { "winner": "a" | "b" | "tie" }

GET    /api/compare/history           - past comparisons with outcomes
GET    /api/compare/leaderboard       - model win rates across all comparisons
```

```sql
CREATE TABLE model_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    model_a TEXT NOT NULL,
    model_b TEXT NOT NULL,
    response_a TEXT NOT NULL,
    response_b TEXT NOT NULL,
    winner TEXT CHECK (winner IN ('a','b','tie')),
    voted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Local Model Playbook

The Playbook helps users discover, download, and run local models (Ollama, LM Studio,
SGLang). Ported from Odysseus, this is a hardware-aware recommendation system.

### Port from Odysseus

```
routes/playbook_routes.py     -> backend/playbook/routes.py
routes/playbook_helpers.py    -> backend/playbook/helpers.py
routes/playbook_output.py     -> backend/playbook/output.py
routes/hwfit_routes.py        -> backend/playbook/hwfit.py
routes/model_routes.py        -> backend/playbook/model_routes.py
```

### API Endpoints

```
GET    /api/playbook/scan                - scan hardware (RAM, VRAM, CPU cores)
GET    /api/playbook/models              - list available models with fit scores
GET    /api/playbook/models/{id}         - model details (size, quant, benchmark)
POST   /api/playbook/models/{id}/download - start download (Ollama pull)
GET    /api/playbook/models/{id}/download/status - download progress SSE
POST   /api/playbook/models/{id}/serve   - start serving (Ollama/LM Studio/SGLang)
POST   /api/playbook/models/{id}/stop    - stop serving
GET    /api/playbook/serving             - list currently serving models with ports
POST   /api/playbook/benchmark           - run quick latency benchmark on a model
```

### Hardware Scan

`backend/playbook/hwfit.py` must detect:
- Total RAM (GB)
- VRAM per GPU (GB, per card), GPU vendor (NVIDIA/AMD/Apple Silicon)
- CPU cores and architecture
- Storage free space for model downloads
- OS platform

From this, compute for each model a `fit_score` (0.0-1.0):
- 1.0 = fits comfortably in VRAM
- 0.7 = fits with quantization
- 0.4 = CPU-only, will be slow
- 0.1 = probably too large

From Odysseus ROADMAP: "Prioritize newer architectures and better hardware-fit
models... ranking should account for architecture age, quant format, VRAM/RAM fit,
backend support, vision/mmproj requirements."

### Model Database

`backend/playbook/model_catalog.py` - static catalog of known-good models:
- Include at minimum: Llama 3.3, Llama 3.1, Qwen 2.5, Mistral, Phi-4,
  Gemma 3, DeepSeek-R1, DeepSeek-V3, Falcon 3, SmolLM, CodeGemma
- Each entry: name, model_id, family, sizes (7B/13B/70B), quantizations,
  VRAM requirements, context length, benchmark scores, vision_capable flag
- Source model list from Ollama library API at startup (cached for 24h)

### Serving Backends

Support all three serving backends:
- **Ollama**: `POST /api/playbook/models/{id}/serve` calls `ollama pull + ollama run`
- **LM Studio**: detect if LM Studio is running on local port, register model
- **SGLang**: `python -m sglang.launch_server` - implement for Linux/NVIDIA/AMD
  Per Odysseus ROADMAP: "Make SGLang setup/serve work predictably on Linux,
  Windows/WSL, macOS where possible, Docker, and common NVIDIA/AMD hardware."

### Error Feedback

Per Odysseus ROADMAP: "Failed downloads, dependency installs, preflights, and
serve jobs should show the actual command/output/error in the UI, with copyable
logs and clear next steps instead of just 'crashed'."

Implement: when a serve/download job fails, store the full stderr in the job
record and return it via `GET /api/playbook/jobs/{id}/logs`.

### Research Model Presets

From Odysseus ROADMAP: "Deep Research model presets by hardware."
`GET /api/playbook/research-presets` returns:
```json
{
  "small": { "model": "phi-4", "note": "4GB VRAM minimum" },
  "medium": { "model": "llama3.1:8b", "note": "8GB VRAM" },
  "large": { "model": "llama3.3:70b-q4", "note": "24GB+ VRAM or dual GPU" }
}
```
These are shown in the Deep Research UI before starting a job when local models
are available.

## Playbook Schema

```sql
CREATE TABLE playbook_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    job_type TEXT NOT NULL CHECK (job_type IN ('download','serve','benchmark','stop')),
    model_id TEXT NOT NULL,
    backend TEXT NOT NULL DEFAULT 'ollama',
    status TEXT NOT NULL DEFAULT 'pending',
    progress_pct INT DEFAULT 0,
    logs TEXT DEFAULT '',
    result JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

## Acceptance Criteria

- `POST /api/research/start` with a query returns a job_id and status "running"
- SSE stream emits at least "sub_question_start" and "complete" events
- Final report contains at least 3 sections and a citations list
- `GET /api/playbook/scan` returns hardware info without error on Linux
- `GET /api/playbook/models` returns at least 10 model entries with fit_score
- `POST /api/compare/start` returns two different model responses for the same prompt
- Leaderboard endpoint returns win rates summing to 100% per model pair
