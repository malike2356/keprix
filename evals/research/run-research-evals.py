#!/usr/bin/env python3
"""Research workspace eval runner (Prompt 83)."""

from __future__ import annotations

import csv
import json
import re
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.citations.better_bibtex import parse_better_bibtex
from keprix.research_workspace.citations.bibtex import parse_bibtex
from keprix.research_workspace.citations.bibliography import export_bibliography
from keprix.research_workspace.datasets.codebook import Codebook, VariableDefinition
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.errors import ProvenanceError
from keprix.research_workspace.evidence import EvidenceService
from keprix.research_workspace.obsidian.markdown import analyze_markdown
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.source import ResearchSourceService
from keprix.research_workspace.stats.pspp.output_parser import parse_text_tables
from keprix.research_workspace.stats.pspp.syntax import generate_analysis_syntax
from keprix.research_workspace.store import ResearchWorkspaceStore

EVALS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS_DIR))
from validators import validate_report_claims  # noqa: E402


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((EVALS_DIR / name).read_text(encoding="utf-8"))


def _score(name: str, passed: bool, detail: str = "") -> tuple[str, int, str]:
    return name, 2 if passed else 0, detail


def eval_citation_accuracy() -> tuple[str, int, str]:
    fixture = _load_json("citation-fixtures.json")
    records = parse_bibtex(fixture["bibtex_sample"])
    bbt = parse_better_bibtex(fixture["better_bibtex_sample"])
    expected = fixture["expected"]
    record = records[0]
    report = export_bibliography(records, "report")
    ok = (
        record.citation_key == expected["citation_key"]
        and len(record.authors) == expected["author_count"]
        and record.authors[0] == expected["first_author"]
        and record.year == expected["year"]
        and record.doi == expected["doi"]
        and bbt[0].citation_key == expected["citation_key"]
        and expected["report_contains"] in report
    )
    return _score("citation_accuracy", ok)


def eval_source_attribution(store: ResearchWorkspaceStore) -> tuple[str, int, str]:
    projects = ResearchProjectService(store)
    evidence = EvidenceService(store)
    project = projects.create(title="Eval attribution", owner="eval")
    try:
        evidence.add_claim(project.project_id, text="Uncited fact", source_id="missing", owner="eval")
        return _score("source_attribution", False, "expected ProvenanceError")
    except ProvenanceError:
        return _score("source_attribution", True)


def eval_claim_to_evidence_linking(store: ResearchWorkspaceStore) -> tuple[str, int, str]:
    projects = ResearchProjectService(store)
    sources = ResearchSourceService(store)
    evidence = EvidenceService(store)
    project = projects.create(title="Eval evidence", owner="eval")
    source = sources.add(project.project_id, kind="url", ref="https://example.org/paper", owner="eval")
    claim = evidence.add_claim(
        project.project_id,
        text="Supported finding",
        source_id=source.source_id,
        owner="eval",
        approved=True,
    )
    bundle = evidence.build_bundle(project.project_id, label="eval bundle", owner="eval")
    ok = source.source_id in bundle.members or claim["claim_id"] in bundle.members
    return _score("claim_to_evidence_linking", ok)


def eval_dataset_and_codebook(store: ResearchWorkspaceStore) -> tuple[str, int, str]:
    fixture = _load_json("dataset-fixtures.json")
    projects = ResearchProjectService(store)
    project = projects.create(title="Eval dataset", owner="eval")
    manager = DatasetManager(store)
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fixture["csv_header"])
        writer.writerows(fixture["csv_rows"])
        csv_path = Path(handle.name)
    try:
        imported = manager.import_file(
            project.project_id,
            source_path=csv_path,
            name="eval-sample",
            owner="eval",
        )
        codebook = manager.load_codebook(imported["dataset_id"], 1)
        expected = fixture["expected"]
        ok = (
            codebook is not None
            and len(codebook.variables) == expected["column_count"]
            and {variable.name for variable in codebook.variables} == set(expected["variables"])
            and imported["meta"].get("row_count") == expected["row_count"]
        )
        return _score("dataset_import_correctness", ok) if ok else _score("dataset_import_correctness", False)
    finally:
        csv_path.unlink(missing_ok=True)


def eval_codebook_preservation(store: ResearchWorkspaceStore) -> tuple[str, int, str]:
    fixture = _load_json("dataset-fixtures.json")
    codebook = Codebook(
        dataset_id="ds-eval",
        version_id="ds-eval-v1",
        variables=[
            VariableDefinition(
                name="age",
                label="Age in years",
                value_labels={"99": "Missing"},
                missing_codes=["99"],
            )
        ],
    )
    manager = DatasetManager(store)
    manager.save_codebook(codebook)
    loaded = manager.load_codebook("ds-eval", 1)
    ok = (
        loaded is not None
        and loaded.get_variable("age") is not None
        and loaded.get_variable("age").label == "Age in years"
        and loaded.get_variable("age").value_labels.get("99") == "Missing"
        and "99" in loaded.get_variable("age").missing_codes
        and len(fixture["csv_header"]) == 3
    )
    return _score("codebook_preservation", ok)


def eval_pspp_syntax_generation() -> tuple[str, int, str]:
    fixture = _load_json("pspp-fixtures.json")
    variables = [VariableDefinition.from_dict(item) for item in fixture["variables"]]
    codebook = Codebook(dataset_id="ds-pspp", version_id="ds-pspp-v1", variables=variables)
    with tempfile.TemporaryDirectory() as tmp:
        workspace_root = Path(tmp) / "workspace"
        data_path = workspace_root / "datasets" / "derived" / "ds-pspp" / "v1" / "data.csv"
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text("age,region\n30,north\n", encoding="utf-8")
        syntax = generate_analysis_syntax(
            codebook=codebook,
            data_path=data_path,
            workspace_root=workspace_root,
            procedures=fixture["procedures"],
        )
        ok = all(fragment in syntax for fragment in fixture["expected_syntax_fragments"])
        return _score("pspp_syntax_generation", ok)


def eval_statistical_result_preservation() -> tuple[str, int, str]:
    fixture = _load_json("pspp-fixtures.json")
    tables = parse_text_tables(fixture["mock_output_text"])
    ok = bool(tables) and any("33.33" in " ".join(cell for row in table["rows"] for cell in row) for table in tables)
    return _score("statistical_result_preservation", ok)


def eval_report_bibliography_generation() -> tuple[str, int, str]:
    fixture = _load_json("citation-fixtures.json")
    records = parse_bibtex(fixture["bibtex_sample"])
    report = export_bibliography(records, "report")
    ok = "## Bibliography" in report and "Smith, John" in report
    return _score("report_bibliography_generation", ok)


def eval_obsidian_note_safety() -> tuple[str, int, str]:
    fixture = _load_json("report-fixtures.json")
    safe_body = "# Literature\n\nSee [[source-1]] and #research tag.\n"
    safe = analyze_markdown(safe_body)
    unsafe_hits = []
    for pattern in fixture["unsafe_note_patterns"]:
        if pattern.lower() in safe_body.lower():
            unsafe_hits.append(pattern)
    traversal = any(link.startswith("../") for link in safe.wikilinks)
    ok = not unsafe_hits and not traversal and "source-1" in safe.wikilinks
    return _score("obsidian_note_safety", ok)


def eval_reproducibility_bundle_export(store: ResearchWorkspaceStore) -> tuple[str, int, str]:
    projects = ResearchProjectService(store)
    sources = ResearchSourceService(store)
    evidence = EvidenceService(store)
    project = projects.create(title="Eval reproducibility", owner="eval")
    source = sources.add(project.project_id, kind="file", ref="fixture.csv", owner="eval")
    claim = evidence.add_claim(
        project.project_id,
        text="Recorded finding",
        source_id=source.source_id,
        owner="eval",
        approved=True,
    )
    bundle = evidence.build_bundle(project.project_id, label="repro bundle", owner="eval")
    chain = evidence.trace_lineage(project.project_id, claim["claim_id"])
    ok = bool(bundle.trace_id) and bool(bundle.members) and bool(chain)
    return _score("reproducibility_bundle_export", ok)


def eval_uncited_claim_gate() -> tuple[str, int, str]:
    fixture = _load_json("report-fixtures.json")
    key = fixture["citation_key"]
    cited_issues = validate_report_claims(fixture["cited_claim"], citation_keys=[key])
    uncited_issues = validate_report_claims(fixture["uncited_factual_claim"], citation_keys=[key])
    opinion_issues = validate_report_claims(fixture["marked_opinion"], citation_keys=[key])
    ok = not cited_issues and bool(uncited_issues) and not opinion_issues
    return _score("uncited_claim_gate", ok)


def _research_store(tmp_root: Path) -> ResearchWorkspaceStore:
    plane = WorkspaceDataPlane(workspace_id=f"ws-eval-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_root
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    store = ResearchWorkspaceStore(workspace_id=plane.workspace_id)
    store.plane = plane
    return store


def main() -> int:
    results: list[tuple[str, int, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        store = _research_store(Path(tmp))
        results.extend(
            [
                eval_citation_accuracy(),
                eval_source_attribution(store),
                eval_claim_to_evidence_linking(store),
                eval_dataset_and_codebook(store),
                eval_codebook_preservation(store),
                eval_pspp_syntax_generation(),
                eval_statistical_result_preservation(),
                eval_report_bibliography_generation(),
                eval_obsidian_note_safety(),
                eval_reproducibility_bundle_export(store),
                eval_uncited_claim_gate(),
            ]
        )

    failed = [row for row in results if row[1] < 2]
    print("Research workspace eval results")
    print("-" * 40)
    for name, score, detail in results:
        status = "PASS" if score == 2 else "FAIL"
        suffix = f" ({detail})" if detail else ""
        print(f"{status:4} {name}{suffix}")
    print("-" * 40)
    print(f"Passed {len(results) - len(failed)}/{len(results)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
