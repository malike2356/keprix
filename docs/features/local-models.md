# Local models

**Local models** (`/playbook`) manages on-machine LLM runtimes: hardware scan, model download, and Ollama integration.

!!! note "Naming"
    **Local models** (`/playbook`) is not the same as **Playbooks** (`/playbooks`), which are YAML automation workflows. See [Playbooks](playbooks.md).

## Web UI (`/playbook`)

- Scan CPU, RAM, GPU, and disk
- List recommended models for your hardware
- Pull and run models via Ollama (when installed)
- Point Keprix providers at `http://localhost:11434/v1`

## Configure as provider

1. Install [Ollama](https://ollama.com)
2. Pull a model: `ollama pull llama3.2`
3. In **Dashboard > Settings > LLM Providers**, add Ollama or a custom provider with base URL `http://localhost:11434/v1`
4. Select the model in chat

## API

| Action | Endpoint |
| --- | --- |
| Hardware scan | `POST /api/playbook/scan` |
| List models | `GET /api/playbook/models` |

## Environment

```bash
OLLAMA_HOST=http://127.0.0.1:11434
```

## Related

- [LLM providers](../configuration/llm-providers.md)
- [Compare models](compare-models.md)
