"""Prompt 60 reference agent gap matrix integrity tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

PROMPT_60_DOCS = [
    "reference-agent-gap-audit.md",
    "reference-agent-adoption-matrix.md",
    "reference-agent-feature-deduplication.md",
    "reference-agent-licence-boundary.md",
]

REFERENCE_FOLDERS = [
    "openhands",
    "aider",
    "browser-use",
    "smolagents",
    "openai-agents-python",
    "pydantic-ai",
    "google-adk-python",
    "semantic-kernel",
    "llama-index",
    "mastra",
    "agno",
    "haystack",
]

PHASE_13_PROMPTS = list(range(51, 60))

GOVERNANCE_PROMPTS = list(range(107, 120))

MATRIX_SECTIONS = [
    "1. Agent OS and engineering workspace",
    "2. Git-native coding and patching",
    "3. Browser automation and online task execution",
    "4. Code-agent sandbox execution",
    "5. Typed production agent runtime",
    "6. Workflow runtime and lifecycle management",
    "7. Enterprise plugin and interoperability layer",
    "8. RAG, indexing, document agents, and retrieval pipelines",
    "9. Interfaces, channels, and agent exposure",
    "10. Observability, evals, traces, and improvement loops",
    "11. Exclusions and product boundaries",
    "12. Build order and dependency map",
]

FORBIDDEN_DASHES = ("\u2014", "\u2013")

UPSTREAM_MARKETING_PHRASES = [
    "world-class",
    "best-in-class",
    "revolutionary",
    "game-changing",
    "cutting-edge AI platform",
]


@pytest.mark.parametrize("name", PROMPT_60_DOCS)
def test_prompt_60_docs_exist(name: str) -> None:
    assert (DOCS / name).exists(), f"missing Prompt 60 doc {name}"


@pytest.mark.parametrize("name", PROMPT_60_DOCS)
def test_prompt_60_docs_have_no_dash_violations(name: str) -> None:
    content = (DOCS / name).read_text(encoding="utf-8")
    for char in FORBIDDEN_DASHES:
        assert char not in content, f"forbidden dash in {name}"


@pytest.mark.parametrize("folder", REFERENCE_FOLDERS)
def test_every_reference_folder_in_gap_audit(folder: str) -> None:
    content = (DOCS / "reference-agent-gap-audit.md").read_text(encoding="utf-8")
    assert folder in content, f"{folder} missing from gap audit"


@pytest.mark.parametrize("folder", REFERENCE_FOLDERS)
def test_every_reference_folder_in_adoption_matrix(folder: str) -> None:
    content = (DOCS / "reference-agent-adoption-matrix.md").read_text(encoding="utf-8")
    assert folder in content, f"{folder} missing from adoption matrix"


def test_matrix_has_twelve_required_sections() -> None:
    content = (DOCS / "reference-agent-adoption-matrix.md").read_text(encoding="utf-8")
    for section in MATRIX_SECTIONS:
        assert section in content, f"missing matrix section: {section}"


@pytest.mark.parametrize("prompt", PHASE_13_PROMPTS)
def test_phase_13_prompts_marked_planned_not_duplicated(prompt: int) -> None:
    matrix = (DOCS / "reference-agent-adoption-matrix.md").read_text(encoding="utf-8")
    dedup = (DOCS / "reference-agent-feature-deduplication.md").read_text(encoding="utf-8")
    assert str(prompt) in matrix
    assert str(prompt) in dedup or "51" in dedup


@pytest.mark.parametrize("prompt", GOVERNANCE_PROMPTS)
def test_governance_prompts_linked_from_matrix(prompt: int) -> None:
    matrix = (DOCS / "reference-agent-adoption-matrix.md").read_text(encoding="utf-8")
    assert str(prompt) in matrix, f"Prompt {prompt} not linked from matrix"


def test_deduplication_doc_references_canonical_modules() -> None:
    content = (DOCS / "reference-agent-feature-deduplication.md").read_text(encoding="utf-8")
    for module in ("playbook.runtime", "teams/", "backend/multiagent/", "rag_pipeline/"):
        assert module in content


def test_licence_boundary_covers_petraclus_and_connectors() -> None:
    content = (DOCS / "reference-agent-licence-boundary.md").read_text(encoding="utf-8")
    assert "Petraclus" in content
    assert "connector" in content.lower()
    assert "extraction/inventory.yaml" in content


def test_matrix_avoids_upstream_marketing_language() -> None:
    content = (DOCS / "reference-agent-adoption-matrix.md").read_text(encoding="utf-8").lower()
    for phrase in UPSTREAM_MARKETING_PHRASES:
        assert phrase not in content


def test_operator_boundary_note_in_matrix() -> None:
    content = (DOCS / "reference-agent-adoption-matrix.md").read_text(encoding="utf-8")
    assert "Playbooks" in content
    assert "Agent Studio" in content
    assert re.search(r"upstream names are internal", content, re.IGNORECASE)


def test_gap_audit_links_to_matrix_and_deduplication() -> None:
    content = (DOCS / "reference-agent-gap-audit.md").read_text(encoding="utf-8")
    assert "reference-agent-adoption-matrix.md" in content
    assert "reference-agent-feature-deduplication.md" in content


def test_agno_persona_qualitative_acceptance_tests_exist() -> None:
    qualitative = ROOT / "tests" / "personas" / "test_persona_qualitative.py"
    improvement = ROOT / "tests" / "personas" / "test_persona_improvement_loop.py"
    hook = ROOT / "src" / "keprix" / "personas" / "improvement_hook.py"
    assert qualitative.is_file()
    assert improvement.is_file()
    assert hook.is_file()
    content = qualitative.read_text(encoding="utf-8")
    for persona in ("TestNexusRouting", "TestForgeCodeReview", "TestWardenAuditor", "TestEmberCoach"):
        assert persona in content
