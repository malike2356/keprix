"""Interview-mode helper for workflow audits."""

from __future__ import annotations

import json
import re
from typing import Any

INTERVIEW_SYSTEM = """You are helping a Keprix operator run a workflow audit.
Ask one concise follow-up question at a time about blind spots in their day/week work.
When they signal they are done, respond with JSON only:
{"done": true, "tasks": [{"domain": "...", "description": "...", "frequency": "daily|weekly|ad_hoc", "desired_output": "...", "propose_skill": true}]}
Do not include markdown fences in the JSON response."""


FOLLOW_UPS = [
    "What tasks do you repeat every week that still feel manual?",
    "Which outputs do you need on a predictable schedule (briefs, reports, triage)?",
    "What tools or integrations do those tasks usually touch?",
]


async def interview_reply(transcript: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]] | None]:
    """Return assistant message and optional parsed tasks when interview completes."""
    user_turns = [item["content"] for item in transcript if item.get("role") == "user"]
    if user_turns and user_turns[-1].strip().lower() in {"done", "finish", "complete"}:
        tasks = _heuristic_tasks_from_transcript(transcript)
        return "Thanks. I captured your workflow tasks below.", tasks

    try:
        from agent.auxiliary_client import async_call_llm, extract_content_or_reasoning

        messages = [{"role": "system", "content": INTERVIEW_SYSTEM}]
        for item in transcript:
            messages.append({"role": item["role"], "content": item["content"]})
        response = await async_call_llm(messages=messages, max_tokens=600, task="workflow_audit_interview")
        text = extract_content_or_reasoning(response) or ""
        parsed = _try_parse_tasks(text)
        if parsed is not None:
            return "I captured your workflow tasks from the interview.", parsed
        if text.strip():
            return text.strip(), None
    except Exception:
        pass

    index = min(len(user_turns), len(FOLLOW_UPS) - 1)
    return FOLLOW_UPS[index], None


def _try_parse_tasks(text: str) -> list[dict[str, Any]] | None:
    text = text.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not payload.get("done"):
        return None
    tasks = payload.get("tasks")
    return tasks if isinstance(tasks, list) else None


def _heuristic_tasks_from_transcript(transcript: list[dict[str, str]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for item in transcript:
        if item.get("role") != "user":
            continue
        for line in item["content"].splitlines():
            line = line.strip(" -•\t")
            if len(line) < 16:
                continue
            if line.lower() in {"done", "finish", "complete"}:
                continue
            tasks.append(
                {
                    "domain": "general",
                    "description": line,
                    "frequency": "weekly",
                    "desired_output": f"Consistent output for: {line[:100]}",
                    "propose_skill": True,
                }
            )
    return tasks[:20]
