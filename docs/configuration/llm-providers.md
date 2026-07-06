# LLM providers

Keprix routes inference through pluggable providers. Set keys in `.env` or via `keprix model`.

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
