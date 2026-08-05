---
name: configure-provider
description: BotFather-style conversational setup for LLM provider API keys and default models.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [providers, byok, configuration, conversational-ops]
    related_skills: [list-providers, configure-channel, configure-scout]
---

# Configure Provider

Use when the operator says add/set/configure an API key, OpenAI, Anthropic, Claude,
DeepSeek, Groq, OpenRouter, Ollama, default model, or BYOK.

## Flow

1. Call `provider_config` action `collect` with the provider alias.
2. Ask using `next_field.ask` (one field at a time).
3. When they answer, call `collect` again with only that field.
4. Never repeat API keys. On voice, prefer typed input for secrets.
5. Optionally `set_default` after a successful configure.
6. Forbidden: "Go to Settings and paste your key."
