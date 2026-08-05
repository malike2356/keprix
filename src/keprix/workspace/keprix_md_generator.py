"""Generate KEPRIX.md workspace navigation guides."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keprix.workspace.template_presets import WorkspaceTemplate


PURPOSES = {
    "raw": "Unstructured source material. Read `raw/index.md` before opening files.",
    "wiki": "Structured knowledge articles. Start with `wiki/index.md` for topic lookup.",
    "outputs": "Deliverables, reports, drafts, and exports.",
    "context": "Stable business, personal, priorities, writing, and guardrail context.",
    "deals": "Property deal records and underwriting notes.",
    "tenants": "Tenant operations and communication notes.",
    "compliance": "Compliance files and obligations.",
    "reports": "Property and operating reports.",
    "specs": "Product or engineering specs.",
    "architecture": "Architecture decisions and diagrams.",
    "releases": "Release notes and rollout plans.",
    "reviews": "Review notes and quality gates.",
    "clients": "Client-specific briefs and context.",
    "deliverables": "Client-facing deliverables.",
    "feedback": "Client feedback and follow-ups.",
}


def render_keprix_md(root: str | Path, template: WorkspaceTemplate) -> str:
    root = Path(root)
    folders = template.folders
    lines = [
        "# KEPRIX.md -- Workspace Navigation Guide",
        "",
        f"Template: {template.name}",
        "",
        "## Structure",
    ]
    if folders:
        for folder in folders:
            lines.append(f"- `/{folder}/` -- {PURPOSES.get(folder, 'Workspace folder. Read index.md first.')}")
    else:
        lines.append("- Custom workspace. Add folders as needed and regenerate indexes.")
    lines.extend(
        [
            "",
            "## Navigation pattern",
            "",
            "1. Read the nearest `index.md` before opening individual files.",
            "2. Use `/wiki/index.md` for structured knowledge when it exists.",
            "3. Use `/raw/index.md` for unprocessed sources when wiki coverage is missing.",
            "4. Write deliverables to `/outputs/` or the closest template-specific output folder.",
            "5. Regenerate indexes after creating, editing, or deleting files.",
            "",
            "## Reading strategy",
            "",
            "- If `wiki/hot.md` exists and hot cache is enabled, read it first.",
            "- Prefer index files for orientation before broad search.",
            "- Load only files that match the current task.",
            "- Check `context/` first when it exists.",
            "- If `wiki/hot.md` exists, read it before deeper wiki traversal.",
            "",
            "## Writing strategy",
            "",
            "- Add raw source material to `raw/` when present.",
            "- Convert durable knowledge into `wiki/` articles.",
            "- Keep outputs linked to their source files.",
            "- When a `runs/` folder exists, log execution notes there.",
            "",
            f"Workspace root: `{root}`",
            "",
        ]
    )
    return "\n".join(lines)
