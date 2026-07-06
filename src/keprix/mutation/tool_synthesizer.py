"""LLM-based tool synthesis for mutation gaps (Prompt 150)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from keprix.improvement.tool_gap_detector import ToolGapProposal
from keprix.mutation.schema_inference import InferredSchema, infer_handler_schema
from keprix.mutation.tool_sandbox import SandboxResult, validate_tool_in_sandbox

logger = logging.getLogger(__name__)

TOOL_SYNTHESIS_SYSTEM_PROMPT = """
You are a Keprix tool engineer. Write a single Python tool module that Keprix loads into its live registry.

Requirements:
1. Import `from tools.registry import registry, tool_result, tool_error` at the top.
2. Define exactly one handler function named `{tool_name}_handler` with signature:
   def {tool_name}_handler(args, **kwargs):
       ...
   The handler receives a dict of arguments and must return a JSON string via tool_result/tool_error.
3. Call registry.register() at module level (not inside a function):
   registry.register(
       name="{tool_name}",
       toolset="generated",
       schema={{
           "name": "{tool_name}",
           "description": "...",
           "parameters": {{
               "type": "object",
               "properties": {{ ... }},
               "required": [...],
           }},
       }},
       handler={tool_name}_handler,
   )
4. Use only Python standard library and packages in the keprix virtualenv.
5. Handle all error cases. Never raise from the handler.
6. The module must be self-contained with no side effects on import.
7. No hardcoded secrets. Use os.environ.get() when needed.

Write ONLY Python source. No markdown, no explanation, no code fences.
""".strip()


@dataclass
class SynthesisResult:
    success: bool
    tool_name: str
    source_code: str
    inferred_schema: InferredSchema | None
    sandbox_result: SandboxResult | None
    error: str | None
    attempts: int
    tokens_used: int


async def synthesize_tool(
    proposal: ToolGapProposal,
    workspace_id: str,
    max_attempts: int = 3,
    model: str | None = None,
) -> SynthesisResult:
    """Generate Python tool source for a gap proposal. Never raises."""
    _ = workspace_id
    tool_name = _normalize_tool_name(proposal.tool_name)
    rewrite_hint: str | None = None
    tokens_used = 0
    last_error = "synthesis did not start"

    for attempt in range(1, max_attempts + 1):
        try:
            source_code, used_tokens = await _generate_source(
                proposal=proposal,
                tool_name=tool_name,
                rewrite_hint=rewrite_hint,
                model=model,
            )
            tokens_used += used_tokens
        except Exception as exc:
            last_error = str(exc)
            logger.warning("tool synthesis LLM failed attempt %s: %s", attempt, exc)
            continue

        inferred = infer_handler_schema(source_code, tool_name)
        sandbox = validate_tool_in_sandbox(source_code, tool_name)
        if sandbox.passed:
            return SynthesisResult(
                success=True,
                tool_name=tool_name,
                source_code=source_code,
                inferred_schema=inferred if not inferred.errors else None,
                sandbox_result=sandbox,
                error=None,
                attempts=attempt,
                tokens_used=tokens_used,
            )

        last_error = sandbox.error or "sandbox validation failed"
        rewrite_hint = last_error

    return SynthesisResult(
        success=False,
        tool_name=tool_name,
        source_code="",
        inferred_schema=None,
        sandbox_result=None,
        error=last_error,
        attempts=max_attempts,
        tokens_used=tokens_used,
    )


async def _generate_source(
    *,
    proposal: ToolGapProposal,
    tool_name: str,
    rewrite_hint: str | None,
    model: str | None,
) -> tuple[str, int]:
    from agent.auxiliary_client import async_call_llm, extract_content_or_reasoning

    system_prompt = TOOL_SYNTHESIS_SYSTEM_PROMPT.format(tool_name=tool_name)
    user_prompt = _build_synthesis_user_prompt(proposal, rewrite_hint=rewrite_hint)
    response = await async_call_llm(
        task="mutation_tool_synthesis",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=6000,
        model=model,
    )
    raw = extract_content_or_reasoning(response).strip()
    if not raw:
        raise RuntimeError("LLM returned empty synthesis response")
    tokens = 0
    usage = getattr(response, "usage", None)
    if usage is not None:
        tokens = int(getattr(usage, "total_tokens", 0) or 0)
    return _extract_source_from_response(raw), tokens


def _build_synthesis_user_prompt(proposal: ToolGapProposal, *, rewrite_hint: str | None = None) -> str:
    lines = [
        f"Tool name: {proposal.tool_name}",
        f"Description: {proposal.description}",
        f"Confidence: {proposal.confidence}",
        f"Proposal id: {proposal.proposal_id}",
    ]
    if rewrite_hint:
        lines.append(f"Previous attempt failed sandbox validation: {rewrite_hint}")
        lines.append("Fix the code and return a corrected module.")
    return "\n".join(lines)


def _extract_source_from_response(llm_response: str) -> str:
    text = llm_response.strip()
    fence = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fence:
        return fence.group(1).strip() + "\n"
    return text + ("\n" if not text.endswith("\n") else "")


def _normalize_tool_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", (name or "generated_tool").strip().lower())
    cleaned = cleaned.strip("_") or "generated_tool"
    if cleaned[0].isdigit():
        cleaned = f"tool_{cleaned}"
    return cleaned
