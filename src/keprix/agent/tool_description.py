"""Natural language tool descriptions (Google-style pattern)."""

from __future__ import annotations

from agent.tool_schema import ToolSchema


def generate_natural_description(tool: ToolSchema) -> str:
    """Generate a natural language tool description."""
    param_descriptions: list[str] = []
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
        example_text = (
            f'\n\nExample: "{ex.description}". Call with '
            + ", ".join(f"{k}={v!r}" for k, v in ex.parameters.items())
            + f". Returns: {ex.result_summary}."
        )

    params_block = "\n".join(param_descriptions) if param_descriptions else "  (none)"
    return (
        f"{tool.name}: {tool.description}\n\n"
        f"Parameters:\n{params_block}\n\n"
        f"Returns: {tool.returns.description}{example_text}"
    )
