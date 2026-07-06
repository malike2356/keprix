"""Prompt 59 reference adoption release smoke tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
DOCS_INTERNAL = DOCS / "internal"


def _doc_path(name: str) -> Path:
    for base in (DOCS_INTERNAL, DOCS):
        candidate = base / name
        if candidate.exists():
            return candidate
    return DOCS / name


def _doc_glob(pattern: str) -> list[Path]:
    seen: dict[str, Path] = {}
    for base in (DOCS_INTERNAL, DOCS):
        for path in base.glob(pattern):
            seen.setdefault(path.name, path)
    return list(seen.values())


FRONTEND_NAV = ROOT / "frontend" / "src" / "lib" / "navigation.ts"
BACKEND_NAV = ROOT / "src" / "keprix" / "ui_contract" / "navigation.py"


@pytest.mark.asyncio
async def test_reference_adoption_smoke(tmp_path: Path) -> None:
  from keprix.playbook.adoption_release import run_reference_adoption_smoke

  result = await run_reference_adoption_smoke(workspace_id="adoption-smoke", repo_root=tmp_path)
  assert result["playbook_run_id"]
  assert result["playbook_status"] in {"completed", "running", "paused"}
  assert result["crew"]["name"] == "adoption-smoke-crew"
  assert result["browser"].get("dry_run") is True
  assert result["analytics"]["ok"] is True
  assert result["analytics"]["verification_allowed"] is True
  assert result["eval"]["eval_id"]
  assert result["eval"]["pipeline_id"] == "reference-adoption-smoke"


def test_reference_adoption_docs_exist() -> None:
  required = [
    "reference-agent-gap-audit.md",
    "reference-agent-adoption-matrix.md",
    "reference-agent-feature-deduplication.md",
    "reference-agent-licence-boundary.md",
    "reference-agent-adoption-map.md",
    "keprix-playbook-runtime.md",
    "keprix-agent-teams.md",
    "keprix-browser-engine.md",
    "keprix-analytics-workspace.md",
    "keprix-self-coding.md",
    "keprix-tool-adapters.md",
    "keprix-evals-observability.md",
    "keprix-agent-studio.md",
    "reference-agent-adoption-release-checklist.md",
  ]
  for name in required:
    assert _doc_path(name).exists(), f"missing doc {name}"


def test_reference_adoption_map_links_prompts_51_through_58() -> None:
  content = _doc_path("reference-agent-adoption-map.md").read_text(encoding="utf-8")
  for prompt in range(51, 59):
    assert str(prompt) in content
  for project in ("LangGraph", "CrewAI", "LaVague", "TaskWeaver", "SWE-agent", "AutoGen"):
    assert project in content


def test_unified_navigation_includes_adoption_surfaces() -> None:
  nav = FRONTEND_NAV.read_text(encoding="utf-8")
  backend = BACKEND_NAV.read_text(encoding="utf-8")
  labels = [
    "Playbooks",
    "Agent Teams",
    "Browser",
    "Analytics",
    "Coding",
    "Tools",
    "Evals",
    "Agent Studio",
  ]
  for label in labels:
    assert label in nav, f"missing frontend nav label {label}"
    assert label in backend, f"missing backend nav label {label}"


def test_adoption_docs_avoid_recipe_terminology() -> None:
  pattern = re.compile(r"\brecipe\b", re.IGNORECASE)
  for path in _doc_glob("keprix-*.md"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    assert not pattern.search(text), f"recipe terminology in {path.name}"
  checklist = _doc_path("reference-agent-adoption-release-checklist.md").read_text(encoding="utf-8")
  assert not pattern.search(checklist)


def test_adoption_docs_have_no_dash_violations() -> None:
  forbidden = ("\u2014", "\u2013")
  for name in (
    "reference-agent-adoption-map.md",
    "reference-agent-adoption-release-checklist.md",
    "keprix-playbook-runtime.md",
  ):
    content = _doc_path(name).read_text(encoding="utf-8")
    for char in forbidden:
      assert char not in content, f"forbidden dash in {name}"
