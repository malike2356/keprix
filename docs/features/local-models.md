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

## Running Keprix fully locally (Ollama, no API key)

Measured on a laptop with an RTX 3050 (4 GB VRAM) and 14 GB RAM. Adjust to taste.

1. Install [Ollama](https://ollama.com). Without `sudo`, unpack the Linux archive
   into `~/.local` (`tar --zstd -xf ollama-linux-amd64.tar.zst -C ~/.local`).
2. Start it with a compact KV cache and a context Keprix can afford:

   ```bash
   OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_CONTEXT_LENGTH=32768 ollama serve
   ```

3. Pull a **non-thinking** model: `ollama pull qwen3:4b-instruct-2507-q4_K_M`.
   Avoid the plain `qwen3:4b` tag for agent use: it spends 1,000+ tokens
   reasoning about a one-line question, which at laptop speeds means 60 to 80
   seconds per model call (the instruct variant answered the same question in
   under a second).
4. Give the local model its own profile so your cloud default stays untouched.
   A profile is a separate `KEPRIX_HOME`:

   ```bash
   keprix profile create local --no-alias --description "Local Ollama model"
   H=~/.keprix/profiles/local
   KEPRIX_HOME=$H keprix config set model.default qwen3:4b-instruct-2507-q4_K_M
   KEPRIX_HOME=$H keprix config set model.provider custom
   KEPRIX_HOME=$H keprix config set model.base_url http://127.0.0.1:11434/v1
   KEPRIX_HOME=$H keprix config set agent.prompt_profile compact
   KEPRIX_HOME=$H keprix -z "In two sentences, what is a mutex?"
   ```

   The wrapper that `keprix profile alias` generates runs `keprix -p <name>`;
   in 0.16.0 that flag is rejected, so use the `KEPRIX_HOME=...` form (or a
   two-line shell script that sets it).

What to expect on that hardware: about 22 tok/s on short prompts, about 7 tok/s
with an 8K-token prompt and about 2 tok/s with a nearly full 28K context;
follow-up turns reuse Ollama's prompt cache (about 8 s each with an ~8K prefix).
The model plus a 32K context takes about 5.4 GB and is split between GPU and CPU.
A plain question through Keprix took about 23 s end to end.

!!! note "Tool tasks"
    In 0.16.0 the standalone CLI's product tool ACL rejects built-in tool calls
    (`[tool_acl_denied] ... not_listed`) whichever model is used, so a local
    profile is reliable for chat and drafting today, while tasks that need
    tools depend on that being resolved.

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
