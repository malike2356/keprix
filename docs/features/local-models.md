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

## Small machines: the compact profile

Keprix's default prompt (tool schemas + skills index + guidance) is roughly
19K tokens before you type anything, and it insists on a 64K context window.
That is comfortable for cloud models but too much for a laptop with a small
GPU and limited RAM, where the KV cache for a long context can cost more
memory than the model itself.

Set the **compact** profile to shrink it:

```yaml
# ~/.keprix/config.yaml
agent:
  prompt_profile: compact
```

or `KEPRIX_PROMPT_PROFILE=compact` in the environment. Compact mode:

- keeps a core tool set (terminal, process, file read/write/patch/search, web,
  todo, clarify, memory, skill loading) plus any MCP tools, and drops heavy or
  admin-only tools (delegation, session search, skill authoring, `*_config`,
  kanban, browser automation, TTS, image generation, business tools);
- renders the skills index names-only with a short preamble;
- lowers the minimum context window from 64,000 to 16,384 tokens;
- caps the context requested from Ollama (which otherwise asks for the model's
  *maximum* window, often 40K to 256K+) at 32,768 tokens, and points the
  compressor at that window so compaction fires before Ollama would truncate.

In a measured session (31 tools loaded) the fixed prefix dropped from about
19.0K to 8.8K tokens.

| Setting (`agent.*`) | Env var | Default | Purpose |
| --- | --- | --- | --- |
| `prompt_profile` | `KEPRIX_PROMPT_PROFILE` | `full` | `full` or `compact` |
| `compact_tools` | | `[]` | Extra tool names to keep in compact mode |
| `compact_context_cap` | | `32768` | Ceiling for the auto-detected Ollama window in compact mode; `0` disables the cap |
| `min_context_length` | `KEPRIX_MIN_CONTEXT_LENGTH` | `64000` (`16384` in compact) | Minimum window Keprix accepts; clamped to at least 8192; `0` warns instead of rejecting |

Explicit `model.context_length` and `model.ollama_num_ctx` settings always win
over the automatic cap. The default `full` profile is unchanged.

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
