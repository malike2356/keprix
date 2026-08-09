# Chat and tools troubleshooting

## Symptom: Chat returns empty or generic provider errors

**Fix:**

1. Settings → LLM / provider keys; test the key.
2. Check quota and rate limits.
3. Confirm backend health and model name.

## Symptom: Agent will not use tools

**Likely cause:** Soft Wall / Tool ACL denial, or tools omitted for that surface.

**Fix:** Review Tool ACL and Soft Wall. For Propreneur-bridged chats, tools must be enabled on the Keprix path (operator configuration). See [Built-in tools](../features/tools.md) and [Soft Wall safety](../features/soft-wall-safety.md).

## Symptom: Agent does not know what Keprix can do

**Fix:** Re-index self-knowledge ([Self-knowledge](self-knowledge.md)). Ask again in a new chat turn.
