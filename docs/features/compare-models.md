# Compare models

Blind A/B model comparison at `/compare` for quality evaluation without provider bias.

## Workflow

1. Choose two configured models or enable random selection from your provider catalog
2. Submit the same prompt to both models (labels hidden until you vote)
3. Vote for the better response (A, tie, or B)
4. Reveal model identities and latency after voting
5. Review pair rankings, per-model win rates, and history over time

## Providers

Comparisons use the same configured LLM providers as workspace chat (`/api/models/available`). Add API keys in **Settings > LLM providers** before running comparisons. At least two configured models are required.

## Persistence

Comparison sessions are stored in PostgreSQL when `DATABASE_URL` is set, otherwise in a local SQLite file under your Keprix data directory. History and leaderboards survive API restarts.

Usage events are recorded with channel `compare` for cost and latency analytics.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/compare/models` | List configured models for comparison |
| `POST` | `/api/compare/start` | Start blind comparison (`prompt`, optional `model_a` / `model_b`, `random_models`) |
| `POST` | `/api/compare/{id}/vote` | Record vote (`winner`: `a`, `b`, or `tie`) |
| `GET` | `/api/compare/history` | User comparison history |
| `GET` | `/api/compare/leaderboard` | Pair and per-model rankings |

See [API reference](../reference/api.md).

## Related

- [LLM providers](../configuration/llm-providers.md)
- [Evals](evals.md)
- [Local models](local-models.md)
