# LLM providers

Keprix routes inference through pluggable providers. Prefer the **GUI** on a
running instance; `.env` / CLI remain valid for automation.

## GUI (recommended)

1. Open your **local** workspace (`keprix dashboard` → `http://127.0.0.1:9120/home`, or Compose at `http://127.0.0.1:3000`).
2. Open **Admin → Settings** (`/dashboard/settings`).
3. Tab **LLM Providers** → paste an API key → Save.
4. Optionally **Set as default**, then **Test**.
5. Keys persist under `KEPRIX_HOME/.env` (Docker: `/home/keprix/.keprix/.env`).

Do not put LLM keys only in the host compose `.env` and expect GUI edits to
update that file; the GUI SoT is `KEPRIX_HOME/.env` (and `KEPRIX_ENV_FILE` when set).

## Cloud providers

| Provider | Environment variable |
| --- | --- |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| Groq | `GROQ_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Together | `TOGETHER_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |

## Local models

| Backend | URL variable |
| --- | --- |
| Ollama | `OLLAMA_BASE_URL` (default `http://host.docker.internal:11434/v1`) |
| LM Studio | `LM_STUDIO_URL` |
| Custom OpenAI-compatible | `CUSTOM_LLM_BASE_URL` + `CUSTOM_LLM_API_KEY` |

## Default selection

```bash
KEPRIX_DEFAULT_PROVIDER=auto
```

CLI:

```bash
python3 -m keprix.keprix_cli.main model
```

## Docker note

Containers reach host Ollama via `host.docker.internal` (configured in Compose `extra_hosts`).
