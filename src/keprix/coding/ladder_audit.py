"""Repository-wide Ponytail audit."""

from __future__ import annotations

from pathlib import Path


def audit_repo(root: str | Path, *, limit: int = 50) -> dict:
    base = Path(root)
    findings: list[dict[str, object]] = []
    for path in sorted(base.rglob("*.py")):
        if any(part in {".git", ".venv", "__pycache__", "node_modules"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "ponytail:" in text:
            findings.append({"tag": "debt", "path": str(path), "message": "Contains deferred simplification marker.", "estimated_lines": 5})
        if "class " in text and text.count("pass\n") >= 3:
            findings.append({"tag": "yagni", "path": str(path), "message": "Several placeholder classes; verify they are still needed.", "estimated_lines": 20})
        if len(findings) >= limit:
            break
    return {"findings": findings, "estimated_lines_removable": sum(int(item["estimated_lines"]) for item in findings)}
