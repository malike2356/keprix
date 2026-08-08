# keprix - Prompt 04: LLM Providers and Routing

## Context

Source: `hermes-agent/agent/` (provider adapters), `hermes-agent/providers/`
Source supplement: `core.carinaai.uk/src/brain/` (LLM router, task classifier)
Output: `keprix/backend/providers/`

This prompt ports the complete multi-provider LLM routing layer. keprix must
support at least 23 providers, credential pooling, prompt caching awareness,
and the task classifier from Aiva (commercial).

## Provider Adapters to Port from Hermes

Port every file verbatim, then apply the standard renames from Prompt 03:

```
agent/anthropic_adapter.py         -> backend/providers/anthropic_adapter.py
agent/azure_identity_adapter.py    -> backend/providers/azure_identity_adapter.py
agent/bedrock_adapter.py           -> backend/providers/bedrock_adapter.py
agent/codex_responses_adapter.py   -> backend/providers/codex_responses_adapter.py
agent/codex_runtime.py             -> backend/providers/codex_runtime.py
agent/gemini_cloudcode_adapter.py  -> backend/providers/gemini_cloudcode_adapter.py
agent/gemini_native_adapter.py     -> backend/providers/gemini_native_adapter.py
agent/gemini_schema.py             -> backend/providers/gemini_schema.py
agent/google_code_assist.py        -> backend/providers/google_code_assist.py
agent/google_oauth.py              -> backend/providers/google_oauth.py
agent/lmstudio_reasoning.py        -> backend/providers/lmstudio_reasoning.py
agent/moonshot_schema.py           -> backend/providers/moonshot_schema.py
agent/plugin_llm.py                -> backend/providers/plugin_llm.py
agent/model_metadata.py            -> backend/providers/model_metadata.py
agent/models_dev.py                -> backend/providers/models_dev.py
agent/credential_persistence.py    -> backend/providers/credential_persistence.py
agent/credential_pool.py           -> backend/providers/credential_pool.py
agent/credential_sources.py        -> backend/providers/credential_sources.py
agent/nous_rate_guard.py           -> backend/providers/nous_rate_guard.py
agent/account_usage.py             -> backend/providers/account_usage.py
agent/credits_tracker.py           -> backend/providers/credits_tracker.py
agent/auxiliary_client.py          -> backend/providers/auxiliary_client.py
agent/jiter_preload.py             -> backend/providers/jiter_preload.py
agent/image_gen_provider.py        -> backend/providers/image_gen_provider.py
agent/image_gen_registry.py        -> backend/providers/image_gen_registry.py
agent/image_routing.py             -> backend/providers/image_routing.py
agent/transcription_provider.py    -> backend/providers/transcription_provider.py
agent/transcription_registry.py    -> backend/providers/transcription_registry.py
agent/browser_provider.py          -> backend/providers/browser_provider.py
agent/browser_registry.py          -> backend/providers/browser_registry.py
agent/chat_completion_helpers.py   -> backend/providers/chat_completion_helpers.py
providers/ (full directory)        -> backend/providers/upstream/
```

## Transport Layer

```
agent/transports/anthropic.py             -> backend/providers/transports/anthropic.py
agent/transports/base.py                  -> backend/providers/transports/base.py
agent/transports/bedrock.py               -> backend/providers/transports/bedrock.py
agent/transports/chat_completions.py      -> backend/providers/transports/chat_completions.py
agent/transports/codex_app_server.py      -> backend/providers/transports/codex_app_server.py
agent/transports/codex_app_server_session.py -> backend/providers/transports/codex_app_server_session.py
agent/transports/codex_event_projector.py -> backend/providers/transports/codex_event_projector.py
agent/transports/codex.py                 -> backend/providers/transports/codex.py
agent/transports/hermes_tools_mcp_server.py -> backend/providers/transports/carina_tools_mcp_server.py
agent/transports/types.py                 -> backend/providers/transports/types.py
```

## Task Classifier from Aiva (commercial)

Read `core.carinaai.uk/src/brain/` and implement a Python equivalent of the
task classifier in `backend/providers/task_classifier.py`. The classifier must:
- Accept a user message string
- Return a routing hint: `{ "complexity": "low|medium|high", "domain": str, "suggested_provider": str }`
- Use keyword heuristics (no LLM call) for speed
- Be used by `credential_pool.py` to pick the cheapest capable provider

## Supported Providers List

The following 23 providers must be supported. Each needs a transport, credential
entry, and model list. Carry these over from Hermes provider files:

1. Anthropic (Claude family)
2. OpenAI (GPT family + o-series)
3. OpenAI Codex (Codex app server protocol)
4. Google Gemini (native + Cloud Code)
5. Google Cloud Code Assist
6. AWS Bedrock (Anthropic + Titan on Bedrock)
7. Azure OpenAI
8. DeepSeek (deepseek-chat, deepseek-reasoner, deepseek-v4-pro, deepseek-v4-flash)
9. Groq
10. Mistral
11. Cohere
12. Together AI
13. Fireworks AI
14. Perplexity
15. xAI (Grok)
16. Ollama (local)
17. LM Studio (local)
18. NVIDIA NIM
19. OpenRouter
20. Nous Research
21. Kimi / Moonshot
22. Z.AI / GLM
23. Hugging Face Inference

For any provider in Aiva (commercial) `src/brain/provider-registry.ts` that is
NOT in the list above, add it. Read that file and reconcile.

## Credential Pool Logic

`backend/providers/credential_pool.py` must implement:
- Round-robin across multiple API keys for the same provider
- Per-key rate limit tracking using `rate_limit_tracker.py`
- Automatic failover: if key A returns 429 or 401, try key B
- Priority ordering: DeepSeek > Groq > OpenAI > Anthropic (cost-ascending default)
- Priority is user-configurable via `config.yaml` under `providers.priority`

## Image Generation Providers

Carry over from Hermes:
- FAL.ai (text-to-image, supported models list from `image_gen_provider.py`)
- Replicate
- OpenAI DALL-E 3
- Stability AI

## STT / TTS

From Hermes:
- STT: faster-whisper (local), Groq Whisper, OpenAI Whisper, ElevenLabs
- TTS: OpenAI TTS, ElevenLabs, macOS MLX TTS (from OpenClaw `apps/macos-mlx-tts/`)

Port the macOS MLX TTS bridge from OpenClaw at:
`openclaw/apps/macos-mlx-tts/` -> `keprix/backend/providers/macos_mlx_tts/`

## Renames

Apply standard Prompt 03 renames. Additionally:
- `hermes_tools_mcp_server` -> `carina_tools_mcp_server` in all imports

## Acceptance Criteria

- `from backend.providers.credential_pool import CredentialPool` imports clean
- `from backend.providers.anthropic_adapter import AnthropicAdapter` imports clean
- `from backend.providers.task_classifier import TaskClassifier` imports clean
- `CredentialPool` correctly round-robins across two test keys for the same provider
- `TaskClassifier("write a poem").domain` returns a non-empty string
