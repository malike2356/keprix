"""Optional Pandoc adapter for HTML, PDF, and DOCX export."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from keprix.research_workspace.reports.schemas import OutputFormat, RenderResult

PANDOC_SETUP = (
    "Install Pandoc to export HTML, PDF, or DOCX reports. "
    "See https://pandoc.org/installing.html"
)


def pandoc_available() -> bool:
    return shutil.which("pandoc") is not None


def render_with_pandoc(
    markdown: str,
    *,
    output_format: OutputFormat,
    workdir: Path | None = None,
    citation_keys: list[str] | None = None,
    evidence_links: list[dict[str, Any]] | None = None,
) -> RenderResult:
    if output_format == "markdown":
        return RenderResult(
            format="markdown",
            markdown=markdown,
            renderer="markdown",
            citation_keys=citation_keys or [],
            evidence_links=evidence_links or [],
        )

    if not pandoc_available():
        return RenderResult(
            format="markdown",
            markdown=markdown,
            renderer="markdown",
            setup_instructions=PANDOC_SETUP,
            citation_keys=citation_keys or [],
            evidence_links=evidence_links or [],
        )

    ext_map = {"html": ".html", "pdf": ".pdf", "docx": ".docx"}
    extension = ext_map.get(output_format)
    if extension is None:
        raise ValueError(f"Unsupported Pandoc output format: {output_format}")

    base_dir = workdir or Path.cwd() / ".keprix-reports"
    base_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex[:10]
    md_path = base_dir / f"report-{token}.md"
    out_path = base_dir / f"report-{token}{extension}"
    md_path.write_text(markdown, encoding="utf-8")

    command = ["pandoc", str(md_path), "-o", str(out_path)]
    if output_format == "pdf":
        command.extend(["--pdf-engine=pdflatex"])

    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return RenderResult(
            format="markdown",
            markdown=markdown,
            renderer="markdown",
            setup_instructions=f"Pandoc render failed: {exc}. {PANDOC_SETUP}",
            citation_keys=citation_keys or [],
            evidence_links=evidence_links or [],
        )

    return RenderResult(
        format=output_format,
        markdown=markdown,
        output_path=str(out_path),
        renderer="pandoc",
        citation_keys=citation_keys or [],
        evidence_links=evidence_links or [],
    )
