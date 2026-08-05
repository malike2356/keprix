"""Anthropic-style structured thinking before tool calls."""

THINKING_BLOCK_INSTRUCTION = """
Before calling a tool, briefly think about what you are about to do. This
thinking is NOT shown to the user. It is for your own reasoning.

For each tool call, wrap your reasoning in <thinking> tags:

<thinking>
1. What does the user actually need? (restate in your own words)
2. Which tool can provide this? (name the specific tool)
3. What parameters does it need? (list them with values)
4. What could go wrong? (one risk and how you will handle it)
5. Is there a simpler way? (ponytail-ladder check)
</thinking>

Then call the tool. Do not show the thinking block to the user.

After the tool returns, briefly verify before responding:
- Did the tool return what you expected?
- Is the result valid and complete?
- If no, try an alternative or ask the user.
""".strip()


def thinking_block_enabled(agent) -> bool:
    return bool(getattr(agent, "_thinking_block", True))


def get_thinking_block_instruction(agent=None) -> str:
    if agent is not None and not thinking_block_enabled(agent):
        return ""
    return THINKING_BLOCK_INSTRUCTION
