"""Natural language to Keprix playbook YAML (Prompt 208)."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

import yaml
from pydantic import BaseModel, Field

from keprix.playbook.graph_catalog import get_graph_template
from keprix.playbook.yaml_compiler import compile_playbook_document

ALLOWED_DOC_STEP_TYPES = frozenset(
    {
        "agent_task",
        "http",
        "condition",
        "human_approval",
        "playbook",
        "code",
        "wait",
    }
)

SYSTEM_PROMPT = """You are a Keprix playbook authoring assistant.

Output ONLY valid playbook YAML. No markdown fences, no prose before or after the YAML.

Rules:
1. Include top-level keys: id, name, description, steps, edges
2. Prefer step types agent_task, http, condition, and human_approval
3. Use Keprix template references like {{ steps.<step_id>.output }} for cross-step data
4. Never use n8n expressions such as ={{ $json }} or n8n-nodes-base types
5. If the user implies a schedule, add a YAML comment pointing to Keprix cron admin
6. Never invent tool names; when unsure use tools: [] and add a step comment
7. Use the word playbook in the name and description, not workflow or recipe
8. Step ids must be snake_case and stable for edge references
9. Every non-trivial playbook needs at least one edge unless there is only one step
"""


class PlaybookDraftRequest(BaseModel):
    prompt: str = Field(..., min_length=3)
    workspace_id: str = "default"
    template_hint: str | None = None


class PlaybookDraftResult(BaseModel):
    yaml_text: str
    playbook_id: str
    warnings: list[str] = Field(default_factory=list)
    model_id: str
    run_spec: dict[str, Any] = Field(default_factory=dict)


LlmCompleteFn = Callable[..., Awaitable[tuple[str, str]]]


async def generate_playbook_yaml(
    request: PlaybookDraftRequest,
    *,
    llm_complete: LlmCompleteFn | None = None,
    model_id: str | None = None,
) -> PlaybookDraftResult:
    """Generate editable playbook YAML from a natural language prompt."""
    prompt = request.prompt.strip()
    if not prompt:
        raise ValueError("Prompt is required")

    user_message = _build_user_message(prompt, request.template_hint)
    if llm_complete is None:
        raw_text, resolved_model = await _default_llm_complete(user_message, model_id=model_id)
    else:
        raw_text, resolved_model = await llm_complete(user_message, model_id=model_id)

    yaml_text = extract_yaml_text(raw_text)
    warnings: list[str] = []
    try:
        parsed = parse_playbook_yaml(yaml_text)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    warnings.extend(validate_playbook_document(parsed, yaml_text))
    playbook_id = str(parsed.get("id") or _slugify_playbook_id(str(parsed.get("name") or "playbook")))
    parsed["id"] = playbook_id
    normalized_yaml = yaml.safe_dump(parsed, sort_keys=False, allow_unicode=True, default_flow_style=False)
    run_spec = draft_to_run_spec(parsed)

    return PlaybookDraftResult(
        yaml_text=normalized_yaml.rstrip() + "\n",
        playbook_id=playbook_id,
        warnings=warnings,
        model_id=resolved_model,
        run_spec=run_spec,
    )


def _build_user_message(prompt: str, template_hint: str | None) -> str:
    parts = [f"Describe this automation as Keprix playbook YAML:\n{prompt}"]
    if template_hint:
        template = get_graph_template(template_hint)
        if template is not None:
            parts.append(
                "Extend this existing template shape where helpful:\n"
                + yaml.safe_dump(
                    {
                        "graph_id": template.get("graph_id"),
                        "steps": template.get("steps") or [],
                        "edges": template.get("edges") or [],
                        "entry": template.get("entry"),
                    },
                    sort_keys=False,
                    default_flow_style=False,
                )
            )
    return "\n\n".join(parts)


async def _default_llm_complete(user_message: str, *, model_id: str | None) -> tuple[str, str]:
    from keprix.api.chat_inference import complete_chat_completion

    completion = await complete_chat_completion(
        user_text=user_message,
        model_id=model_id,
        history=[{"role": "system", "content": SYSTEM_PROMPT}],
        channel="playbook_nl_builder",
        include_codebase_context=False,
    )
    resolved = f"{completion.provider}:{completion.model}"
    return completion.text, resolved


def extract_yaml_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Model returned empty YAML")
    fence = re.search(r"```(?:yaml|yml)?\s*\n([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    return text


def parse_playbook_yaml(yaml_text: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Generated YAML is not valid: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Generated YAML must be a mapping")
    if not isinstance(parsed.get("steps"), list) or not parsed["steps"]:
        raise ValueError("Generated YAML must include a non-empty steps list")
    if not isinstance(parsed.get("edges"), list):
        parsed["edges"] = []
    return parsed


def validate_playbook_document(parsed: dict[str, Any], yaml_text: str) -> list[str]:
    warnings: list[str] = []
    if "n8n-nodes-base" in yaml_text or "={{ $" in yaml_text:
        warnings.append("Output contains n8n-specific syntax; edit before running.")
    if re.search(r"\bworkflow\b|\brecipe\b", yaml_text, re.IGNORECASE):
        warnings.append('Prefer the term "playbook" instead of workflow/recipe in copy.')

    for step in parsed.get("steps") or []:
        if not isinstance(step, dict):
            warnings.append("Encountered a non-object step entry.")
            continue
        step_type = str(step.get("type") or "")
        if step_type and step_type not in ALLOWED_DOC_STEP_TYPES:
            warnings.append(f"Step '{step.get('id')}' uses uncommon type '{step_type}'.")
        if step_type == "agent_task" and not step.get("prompt"):
            warnings.append(f"Step '{step.get('id')}' is missing a prompt.")
    if "{{ steps." not in yaml_text and len(parsed.get("steps") or []) > 1:
        warnings.append("Multi-step playbook has no {{ steps.* }} references.")
    return warnings


def draft_to_run_spec(parsed: dict[str, Any]) -> dict[str, Any]:
    """Map docs-style playbook YAML to a runnable runtime spec."""
    _graph = compile_playbook_document(parsed)
    compiled = _graph.compile()
    spec: dict[str, Any] = {
        "graph_id": compiled.graph_id,
        "steps": [],
        "edges": [],
    }
    if parsed.get("entry"):
        spec["entry"] = str(parsed["entry"])
    # Preserve a portable spec snapshot for API clients; execution uses compile_playbook_document.
    for step in parsed.get("steps") or []:
        if isinstance(step, dict) and step.get("id"):
            spec["steps"].append(dict(step))
    for edge in parsed.get("edges") or []:
        if isinstance(edge, dict):
            spec["edges"].append(dict(edge))
    return spec


def _step_summary_message(step: dict[str, Any]) -> str:
    step_type = str(step.get("type") or "agent_task")
    step_id = str(step.get("id") or "step")
    if step_type == "agent_task":
        return str(step.get("prompt") or f"Agent task for {step_id}")
    if step_type == "http":
        method = str(step.get("method") or "GET").upper()
        url = str(step.get("url") or "")
        return f"HTTP {method} {url}".strip()
    if step_type == "code":
        return f"Code step {step_id}"
    if step_type == "wait":
        return f"Wait step {step_id}"
    return f"Playbook step {step_id} ({step_type})"


def _slugify_playbook_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "generated-playbook")[:48]
