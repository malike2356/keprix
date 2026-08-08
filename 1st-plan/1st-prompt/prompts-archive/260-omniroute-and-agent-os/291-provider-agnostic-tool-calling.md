# Keprix - Prompt 291: Provider-agnostic tool calling

**Status:** Shipped (`agent/tool_schema.py`, `tool_description.py`, `thinking_block.py`, `provider_normaliser.py`, `tool_audit.py`, `tools/registry.get_tool_schemas()`, thinking block in `layers/tools.py`, audit hook in `tool_executor.py`, `tests/agent/test_tool_*.py`). Deferred: transport rewiring to `ProviderNormaliser`; per-tool `*_SCHEMA` constants (registry auto-converts OpenAI-style defs).

---

# keprix - Prompt: Provider-Agnostic Tool Calling (Adopting Best Patterns from Leaks)

## Purpose

The system prompt leaks reveal how Anthropic, OpenAI, and Google each format tool calls differently. Anthropic uses XML-structured function calls with explicit thinking tags. OpenAI uses JSON function calling with strict schemas. Google uses a hybrid approach with natural language tool descriptions.

keprix currently uses a single tool-calling format inherited from Hermes. This prompt builds a provider-agnostic abstraction layer that normalises tool calls across providers and adopts the best pattern from each: Anthropic's structured thinking, OpenAI's strict schema validation, and Google's natural language tool descriptions.

## What already exists (do not rebuild)

- `agent/transports/` -- provider-specific transports (anthropic.py, chat_completions.py, codex.py, bedrock.py)
- `agent/tool_executor.py` -- tool dispatch
- `agent/tool_dispatch_helpers.py` -- dispatch helpers
- `agent/model_tools.py` -- tool discovery
- `tools/registry.py` -- central tool registry

## What to build

### 1. Provider-Agnostic Tool Schema

A unified tool schema that normalises across providers:

```python
# agent/tool_schema.py

@dataclass
class ToolSchema:
    """Provider-agnostic tool definition."""

    name: str                       # unique tool name
    description: str                # what the tool does, in natural language
    parameters: dict[str, ParameterSchema]  # typed parameters
    returns: ReturnSchema           # what the tool returns
    examples: list[ToolExample]     # natural language usage examples

    def to_anthropic(self) -> dict:
        """Convert to Anthropic's XML tool format."""

    def to_openai(self) -> dict:
        """Convert to OpenAI's JSON function calling format."""

    def to_google(self) -> dict:
        """Convert to Google's tool format."""

    def to_generic(self) -> str:
        """Convert to natural language tool description for generic LLMs."""


@dataclass
class ParameterSchema:
    name: str
    type: str                      # string, number, boolean, array, object
    description: str               # what this parameter does, in plain language
    required: bool = True
    default: Any = None
    enum: list[str] | None = None  # allowed values if constrained

    def to_json_schema(self) -> dict:
        """OpenAI-style JSON Schema."""
        schema = {"type": self.type, "description": self.description}
        if self.enum:
            schema["enum"] = self.enum
        return schema


@dataclass
class ToolExample:
    """Natural language usage examples for the tool."""
    description: str               # "Check the balance of a Tide bank account"
    parameters: dict               # {"account": "business"}
    result_summary: str            # "Returns account balance and recent transactions"


@dataclass
class ReturnSchema:
    type: str                      # json, file, stream, void
    description: str               # what the return value contains
    schema: dict | None = None     # JSON Schema for structured returns
```

### 2. Tool Schema Adoption -- Retrofit All 60+ Tools

Every existing tool gets a `ToolSchema` definition alongside its implementation:

```python
# tools/stripe_tool.py

STRIPE_TOOL_SCHEMA = ToolSchema(
    name="stripe.create_payment",
    description="Create a payment intent in Stripe. Use this when the user "
                "wants to charge a customer or set up a payment.",
    parameters={
        "amount": ParameterSchema(
            name="amount",
            type="number",
            description="The amount to charge, in the smallest currency unit "
                        "(e.g., pence for GBP, cents for USD). 5000 = £50.00.",
        ),
        "currency": ParameterSchema(
            name="currency",
            type="string",
            description="Three-letter ISO currency code.",
            enum=["gbp", "usd", "eur"],
            default="gbp",
        ),
        "customer_id": ParameterSchema(
            name="customer_id",
            type="string",
            description="Stripe customer ID. If not provided, ask the user.",
            required=False,
        ),
    },
    returns=ReturnSchema(
        type="json",
        description="The created payment intent with client secret and status.",
    ),
    examples=[
        ToolExample(
            description="Charge a customer £50 for a cleaning service",
            parameters={"amount": 5000, "currency": "gbp", "customer_id": "cus_abc123"},
            result_summary="Payment intent created. Status: requires_confirmation.",
        ),
    ],
)
```

### 3. Tool Description Generator

Auto-generate natural language tool descriptions from the schema, adopting Google's pattern:

```python
# agent/tool_description.py

def generate_natural_description(tool: ToolSchema) -> str:
    """Generate a natural language tool description (Google pattern)."""

    param_descriptions = []
    for name, param in tool.parameters.items():
        required = "required" if param.required else "optional"
        enum_hint = ""
        if param.enum:
            enum_hint = f" Must be one of: {', '.join(param.enum)}."
        param_descriptions.append(
            f"  - {name} ({param.type}, {required}): {param.description}{enum_hint}"
        )

    example_text = ""
    if tool.examples:
        ex = tool.examples[0]
        example_text = f"\n\nExample: "{ex.description}". Call with "
        example_text += ", ".join(f"{k}={v}" for k, v in ex.parameters.items())
        example_text += f". Returns: {ex.result_summary}."

    return f"""{tool.name}: {tool.description}

Parameters:
{chr(10).join(param_descriptions)}

Returns: {tool.returns.description}{example_text}
"""
```

### 4. Thinking Block Pattern (Adopting Anthropic's Structured Reasoning)

Anthropic's Fable 5 uses explicit `<thinking>` blocks before tool calls. Adopt this pattern:

```python
# agent/thinking_block.py

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
"""
```

### 5. Provider Normalisation Layer

A middleware that converts tool definitions and tool calls between provider formats:

```python
# agent/provider_normaliser.py

class ProviderNormaliser:
    """Converts tool schemas and calls between provider formats."""

    def __init__(self, provider: str, tools: list[ToolSchema]):
        self.provider = provider
        self.tools = tools

    def get_tool_definitions(self) -> list[dict]:
        """Return tool definitions in the provider's native format."""
        if self.provider == "anthropic":
            return [t.to_anthropic() for t in self.tools]
        elif self.provider in ("openai", "deepseek", "groq", "together"):
            return [t.to_openai() for t in self.tools]
        elif self.provider == "google":
            return [t.to_google() for t in self.tools]
        else:
            # Generic: natural language descriptions
            return [generate_natural_description(t) for t in self.tools]

    def parse_tool_call(self, raw_call: dict) -> ToolCall:
        """Parse a provider-specific tool call into a keprix ToolCall."""
        if self.provider == "anthropic":
            return self._parse_anthropic_tool_call(raw_call)
        elif self.provider in ("openai", "deepseek", "groq", "together"):
            return self._parse_openai_tool_call(raw_call)
        elif self.provider == "google":
            return self._parse_google_tool_call(raw_call)
        else:
            return self._parse_generic_tool_call(raw_call)

    def format_tool_result(self, result: ToolResult) -> dict:
        """Format a tool result in the provider's expected format."""
        if self.provider == "anthropic":
            return self._format_anthropic_result(result)
        elif self.provider in ("openai", "deepseek", "groq", "together"):
            return self._format_openai_result(result)
        elif self.provider == "google":
            return self._format_google_result(result)
        else:
            return self._format_generic_result(result)
```

### 6. Tool Call Audit and Quality

Every tool call is audited against the schema:

```python
# agent/tool_audit.py

class ToolCallAuditor:
    """Validates tool calls against their schema and tracks quality."""

    async def validate_call(self, call: ToolCall, schema: ToolSchema) -> AuditResult:
        """Check that the call matches the schema."""
        errors = []

        # Check required parameters
        for name, param in schema.parameters.items():
            if param.required and name not in call.parameters:
                errors.append(f"Missing required parameter: {name}")
            if name in call.parameters and param.enum:
                if call.parameters[name] not in param.enum:
                    errors.append(
                        f"Invalid value for {name}: {call.parameters[name]}. "
                        f"Must be one of: {param.enum}"
                    )

        # Check for hallucinated parameters
        for name in call.parameters:
            if name not in schema.parameters:
                errors.append(f"Unknown parameter: {name}. Schema has: "
                              f"{list(schema.parameters.keys())}")

        return AuditResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=self._check_best_practices(call, schema),
        )

    async def track_quality(self, call: ToolCall, result: ToolResult):
        """Track tool call quality for improvement loop."""
        # Was the call valid? Did it succeed? Were parameters optimal?
        # Feed into the improvement loop (Prompt 246).
        ...
```

## Files to create

```
src/keprix/agent/
  tool_schema.py               - ToolSchema, ParameterSchema, ReturnSchema
  tool_description.py          - natural language description generator
  thinking_block.py            - Anthropic-style thinking block pattern
  provider_normaliser.py       - multi-provider tool format conversion
  tool_audit.py                - tool call validation and quality tracking

src/keprix/tools/
  # Retrofit ALL existing tools with ToolSchema definitions:
  # Each tool file gets a *_SCHEMA constant alongside its implementation.

tests/agent/
  test_tool_schema.py
  test_tool_description.py
  test_provider_normaliser.py
  test_tool_audit.py
  test_thinking_block.py
```

## Acceptance criteria

- Every tool (60+) has a `ToolSchema` definition with typed parameters, natural language description, and examples.
- Tool definitions convert correctly to Anthropic, OpenAI, and Google formats. A single `ToolSchema` produces valid output for all three.
- The thinking block pattern is injected before tool calls: restate, select tool, list params, check risk, ponytail-ladder.
- The provider normaliser correctly parses tool calls from all supported providers back into keprix `ToolCall` objects.
- Hallucinated parameters (parameters not in the schema) are detected and logged. Required missing parameters are flagged.
- Natural language tool descriptions (Google pattern) are auto-generated from the schema and tested against real model responses.
