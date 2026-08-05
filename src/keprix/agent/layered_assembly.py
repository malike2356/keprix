"""Assemble layered stable-tier content from agent runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.layered_prompt import LayeredPromptBuilder, PromptLayer, PromptSessionContext
from agent.layers.budget import render_budget_layer
from agent.layers.domains import detect_domains, render_domain_layers
from agent.layers.execution import EXECUTION_LAYER
from agent.layers.identity import render_identity_layer
from agent.layers.memory_continuity import MEMORY_CONTINUITY_LAYER
from agent.layers.safety import render_safety_layer
from agent.layers.tone import TONE_LAYER
from agent.layers.tools import render_tools_layer


@dataclass
class LayeredStableInput:
    """Pre-collected stable-tier blocks from system_prompt assembly."""

    identity_body: str = ""
    tool_guidance_blocks: list[str] = field(default_factory=list)
    skills_prompt: str = ""
    execution_blocks: list[str] = field(default_factory=list)
    persona_prompt: str = ""
    domain_context_text: str = ""


def assemble_layered_stable(agent: Any, blocks: LayeredStableInput) -> str:
    """Render stable tier as ordered prompt layers."""
    ctx = PromptSessionContext.from_agent(agent)
    builder = LayeredPromptBuilder(ctx)

    identity = render_identity_layer(ctx)
    if blocks.identity_body.strip():
        identity = f"{identity}\n\n{blocks.identity_body.strip()}"
    builder.add_layer(PromptLayer.IDENTITY, identity)
    builder.add_layer(PromptLayer.BUDGET, render_budget_layer(agent))
    builder.add_layer(PromptLayer.SAFETY, render_safety_layer(agent))

    tools = render_tools_layer(ctx, agent)
    tool_extras = [block.strip() for block in blocks.tool_guidance_blocks if block and block.strip()]
    if blocks.skills_prompt.strip():
        tool_extras.append(blocks.skills_prompt.strip())
    if tool_extras:
        tools = f"{tools}\n\n" + "\n\n".join(tool_extras)
    builder.add_layer(PromptLayer.TOOLS, tools)
    builder.add_layer(PromptLayer.TONE, TONE_LAYER)
    builder.add_layer(PromptLayer.MEMORY, MEMORY_CONTINUITY_LAYER)

    execution_parts = [EXECUTION_LAYER]
    execution_parts.extend(block.strip() for block in blocks.execution_blocks if block and block.strip())
    builder.add_layer(PromptLayer.EXECUTION, "\n\n".join(execution_parts))

    domain_keys = detect_domains(blocks.domain_context_text)
    if domain_keys:
        builder.add_layer(PromptLayer.DOMAIN, render_domain_layers(domain_keys))
    if blocks.persona_prompt.strip():
        builder.add_layer(PromptLayer.PERSONA, blocks.persona_prompt.strip())

    # ── Product prompt layers ──
    # Product modules register additional layers via registries.product_hooks.
    # These render after core layers and the persona layer.  The operator can
    # opt out of specific layers via KEPRIX_DISABLED_PROMPT_LAYERS.
    from registries.product_hooks import iter_product_prompt_layers
    for layer in iter_product_prompt_layers():
        try:
            content = layer.render()
            if content and content.strip():
                builder.add_layer(PromptLayer.PRODUCT, content.strip())
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Product prompt layer '%s' (product=%s) failed to render",
                layer.name, layer.product,
            )

    return builder.build()


def layered_prompt_enabled(agent: Any) -> bool:
    return bool(getattr(agent, "_layered_prompt", True))


__all__ = [
    "LayeredStableInput",
    "assemble_layered_stable",
    "layered_prompt_enabled",
]
