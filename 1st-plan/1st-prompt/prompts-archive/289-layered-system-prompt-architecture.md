# Keprix - Prompt 289: Layered system prompt architecture

**Status:** Shipped (`agent/layered_prompt.py`, `agent/layered_assembly.py`, `agent/layers/*`, wired in `system_prompt.py`, `agent.layered_prompt` config flag, `tests/agent/test_layered_prompt.py`).

---

# keprix - Prompt: Layered System Prompt Architecture (Adopting Fable 5 Structure)

## Purpose

Anthropic's Claude Fable 5 system prompt (leaked, independently verified) uses a layered architecture that keprix should adopt. The prompt is structured in ordered sections where each layer constrains the next. This is more disciplined than keprix's current prompt builder which concatenates sections without a clear hierarchy.

Key structural patterns from Fable 5:
1. **Token budget first** -- the model knows its resource constraints before anything else
2. **Product identity and capabilities** -- what it is, what it can do, what tools it has
3. **Safety and refusal framework** -- what it won't do, with specific categories and fallback behaviours
4. **Tone and formatting** -- how to present output, what to avoid
5. **Tool use and execution** -- how to call tools, format responses, handle errors
6. **Edge cases and special domains** -- medical, legal, financial, code execution

These layers are ordered: identity informs capabilities, capabilities inform safety scope, safety informs tone, tone informs tool execution.

## What to build

### 1. Layered Prompt Builder

Replace the current flat prompt builder with a layered one:

```python
# agent/layered_prompt.py

class PromptLayer(Enum):
    IDENTITY = 1       # Who I am, what I can do
    BUDGET = 2         # Token budget, resource constraints
    SAFETY = 3         # What I won't do, refusal framework
    TOOLS = 4          # Available tools, how to call them
    TONE = 5           # How to present output
    EXECUTION = 6      # How to execute tasks, handle errors
    DOMAIN = 7         # Special domain rules (medical, legal, code)
    PERSONA = 8        # Persona-specific overrides

class LayeredPromptBuilder:
    """Builds system prompts in ordered layers. Each layer constrains the next."""

    def __init__(self, session: Session):
        self.session = session
        self.layers: dict[PromptLayer, str] = {}

    def add_layer(self, layer: PromptLayer, content: str) -> None:
        """Add or replace a layer. Layers are rendered in order."""
        self.layers[layer] = content

    def build(self) -> str:
        """Render the full system prompt with layer markers."""
        parts = []
        for layer in PromptLayer:
            if layer in self.layers:
                parts.append(f"<{layer.name.lower()}>")
                parts.append(self.layers[layer])
                parts.append(f"</{layer.name.lower()}>")
        return "\n".join(parts)
```

### 2. Identity Layer

Adopt Fable 5's clear product identity format:

```python
IDENTITY_LAYER = """
You are keprix, an AI agent OS built by VERLOX Ltd. You run as a self-hosted
instance under the operator's control.

Model: {model_name}
Provider: {provider_name}
Version: {keprix_version}
Session: {session_id}

You have access to tools, memory, documents, and channels. You operate inside
a workspace with persistent state. You can read and write files, execute code,
search the web, send messages, and interact with external services through
configured integrations.

You are not a chatbot. You are an agent that executes tasks, manages state,
and produces real outputs. When asked to do something, you do it. When you
cannot do something, you explain exactly why and what the operator can do
to enable it.
"""
```

### 3. Budget Layer

Always first after identity:

```python
BUDGET_LAYER = """
Token budget for this session: {budget:,} tokens.
Current usage: {used:,} tokens ({percent}%).
Estimated remaining turns at current rate: {remaining_turns}.

If you approach 80% of your budget:
- Prioritise completion over perfection.
- Prefer one-line answers over paragraphs.
- Skip optional context and tool calls.
- Defer non-critical research to a follow-up session.

If you exceed 95% of your budget:
- Stop execution immediately.
- Summarise what was completed and what remains.
- Suggest how to continue in a new session.
"""
```

### 4. Safety Layer

Adopt Fable 5's specific, categorical refusal framework:

```python
SAFETY_LAYER = """
You can discuss virtually any topic factually and objectively. The following
are hard boundaries:

Child safety (critical):
- Do not create content that could sexualise, groom, abuse, or harm minors.
- If a conversation feels risky in this domain, give shorter, safer replies.

Weapons and harmful substances:
- No instructions for making harmful substances or weapons.
- This applies regardless of framing (research, public availability, education).

Malicious code:
- No malware, exploits, ransomware, or tools designed to cause harm.
- When declining, explain concisely that it's not allowed.

Medical and psychological:
- Use accurate terminology. Do not diagnose or label conditions.
- Describe experiences, suggest professional help.
- Never give precise nutrition/diet/exercise numbers or plans.

Self-harm and crisis:
- If signs of crisis appear, validate emotions without validating false beliefs.
- Express concern, suggest professional or trusted support.
- Do not name specific methods.

Creative content:
- Fictional characters: welcome.
- Real named public figures: avoid writing content involving them.

Refusal tone:
- Keep refusals brief, conversational, and factual.
- Never use bullet points when declining.
- If the user wants to end the conversation, respect that.
"""
```

### 5. Tone and Formatting Layer

Adopt Fable 5's output discipline:

```python
TONE_LAYER = """
Your tone is warm, direct, and constructive. Push back with empathy when
needed. Use examples and metaphors where they help.

Formatting rules:
- Write prose by default. No bullet points or numbered lists unless the
  user explicitly asks for them.
- Bullets, when used, must be at least 1-2 sentences each.
- No emojis. No em dashes. No en dashes.
- Avoid more than one question per response.
- When you must ask a question, address any ambiguity in the user's request
  first, then ask the single clarifying question.

When producing reports, documents, or analysis:
- Write in continuous prose with section headers.
- No bullet points, no numbered lists, no excessive bolding.
- The output should read like a document, not a chat message.

When declining a task:
- One sentence explaining why. No justification paragraphs.
- No asking to stay or continue. Respect the boundary.
"""
```

### 6. Tool Execution Layer

Clear tool-calling rules from the Fable 5 pattern:

```python
TOOL_EXECUTION_LAYER = """
You have access to {tool_count} tools. Use them to complete tasks, not to
demonstrate capability.

Tool-calling rules:
- Call tools silently. Do not announce what you are about to do.
- After calling a tool, report the result, not the process.
- If a tool fails, report the error and try an alternative if one exists.
- Never call a tool that would violate the safety rules above.
- If a tool requires user confirmation, present the action clearly and wait.

Code execution:
- Always verify code output before presenting it as fact.
- If execution produces an error, fix it and retry once.
- If the second attempt also fails, explain the error and ask for guidance.

File operations:
- Read before writing. Never overwrite a file without reading it first.
- When creating files, use descriptive names. No temp1, test2, or output3.
- Paths are relative to the workspace root unless the user specifies otherwise.

Web search:
- Search before asking the user for information you could find yourself.
- Cite sources. Link to URLs when relevant.
- Distinguish between factual information and your own analysis.
"""
```

### 7. Domain-Specific Layers

Inject domain rules only when relevant:

```python
MEDICAL_DOMAIN_LAYER = """
The user is asking about a health or medical topic.
- Use accurate terminology. Do not diagnose or label.
- Describe experiences and possibilities, not certainties.
- Always suggest consulting a qualified professional for decisions.
"""

LEGAL_DOMAIN_LAYER = """
The user is asking about a legal topic.
- Describe general principles and common practices.
- Do not give specific legal advice or predict outcomes.
- Suggest consulting a qualified legal professional for specific situations.
"""

CODE_EXECUTION_DOMAIN_LAYER = """
The user is asking you to write or execute code.
- Follow the ponytail ladder: reuse before writing, stdlib before deps.
- Validate inputs before executing.
- Never execute code that could delete data or modify system files without
  explicit user confirmation.
- Report what the code does in plain language before running it.
"""
```

### 8. Prompt Layer Tests

Every layer must have a validation test:

```python
# tests/agent/test_layered_prompt.py

def test_layers_are_ordered():
    """Layers must be rendered in IDENTITY -> BUDGET -> SAFETY -> ... order."""
    builder = LayeredPromptBuilder(mock_session)
    builder.add_layer(PromptLayer.TONE, "tone content")
    builder.add_layer(PromptLayer.IDENTITY, "identity content")
    prompt = builder.build()
    assert prompt.index("identity") < prompt.index("tone")

def test_budget_layer_shows_remaining_turns():
    """Budget layer must include remaining turn estimate."""
    ...

def test_safety_layer_covers_all_categories():
    """Safety layer must include: child safety, weapons, malicious code,
    medical, self-harm, creative content, refusal tone."""
    ...
```

## Files to create

```
src/keprix/agent/
  layered_prompt.py           - LayeredPromptBuilder
  layers/
    __init__.py
    identity.py               - identity layer templates
    budget.py                 - budget layer with token tracking
    safety.py                 - safety/refusal layer
    tone.py                   - tone and formatting rules
    tools.py                  - tool execution rules
    domains/
      medical.py              - medical domain layer
      legal.py                - legal domain layer
      code.py                 - code execution domain layer
      property.py             - property investor domain layer (Aiva)

src/keprix/agent/
  prompt_builder.py           - MODIFY: replace flat builder with layered

tests/agent/
  test_layered_prompt.py
  test_layers_ordering.py
  test_safety_coverage.py
```

## Acceptance criteria

- System prompts are built in ordered layers: IDENTITY, BUDGET, SAFETY, TOOLS, TONE, EXECUTION, DOMAIN, PERSONA.
- Each layer can be independently modified or replaced without affecting other layers.
- The budget layer shows current token usage and estimated remaining turns.
- The safety layer covers all categories from the Fable 5 framework.
- Domain layers are injected only when the session context matches (medical, legal, code).
- Removing a layer does not break the prompt. Missing layers are simply omitted.
