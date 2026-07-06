"""Report synthesis for deep research."""

from __future__ import annotations

import time
from typing import Any

from keprix.research.depth import get_depth_config
from keprix.research.errors import ResearchPipelineError
from keprix.research import inference


async def decompose_query(
    query: str,
    count: int,
    model: str | None,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[str]:
    prompt = (
        f"Break this research question into exactly {count} focused sub-questions.\n"
        f"Return one sub-question per line, no numbering.\n\nQuestion: {query}"
    )
    text = await inference.complete_research_prompt(
        prompt,
        model=model,
        user_id=user_id,
        session_id=session_id,
    )
    lines = [line.strip().lstrip("-0123456789.) ") for line in text.splitlines() if line.strip()]
    if not lines:
        raise ResearchPipelineError("LLM did not return any sub-questions for this query.")
    if len(lines) < count:
        raise ResearchPipelineError(
            f"LLM returned {len(lines)} sub-questions; expected at least {count}."
        )
    return lines[:count]


async def synthesize_report(
    *,
    query: str,
    depth: str,
    sub_questions: list[str],
    sources: list[dict[str, Any]],
    model: str | None,
    started_at: float,
    user_id: str | None = None,
    session_id: str | None = None,
) -> tuple[str, int]:
    cfg = get_depth_config(depth)
    citations = "\n".join(
        f"[{i + 1}] {s.get('title', 'Source')} - {s.get('url', '')}"
        for i, s in enumerate(sources)
    )
    excerpts = []
    for i, source in enumerate(sources):
        excerpt = (source.get("excerpt") or source.get("snippet") or "")[:1200]
        excerpts.append(f"[{i + 1}] {source.get('title', 'Source')}\n{excerpt}")
    body_input = "\n\n".join(excerpts)
    prompt = (
        f"Write a markdown research report about: {query}\n"
        f"Target length: about {cfg.target_words} words.\n"
        f"Include an executive summary (3-5 bullets), numbered finding sections, "
        f"inline citations like [1], and a Sources section.\n"
        f"Format for professional export: use ATX headings (##, ###), no HTML, "
        f"put each source on its own line in ## Sources with [n] Title - URL, "
        f"avoid tables unless comparing metrics.\n\n"
        f"Sub-questions investigated:\n"
        + "\n".join(f"- {q}" for q in sub_questions)
        + f"\n\nSource excerpts:\n{body_input}"
    )
    report = await inference.complete_research_prompt(
        prompt,
        model=model,
        user_id=user_id,
        session_id=session_id,
    )
    elapsed = time.time() - started_at
    header = (
        f"<!-- keprix-research words:~{cfg.target_words} elapsed_s:{elapsed:.1f} -->\n"
        f"# Research Report\n\n"
        f"**Query:** {query}\n"
        f"**Depth:** {depth}\n"
        f"**Generated in:** {elapsed:.1f}s\n\n"
    )
    if "## Sources" not in report and "## sources" not in report.lower():
        report = report.rstrip() + f"\n\n## Sources\n\n{citations}\n"
    return header + report, len(prompt.split()) + len(report.split())
