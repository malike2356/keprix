"""Integration smoke test for Research Workspace (Prompt 83)."""

from __future__ import annotations

import csv
import json
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals" / "research"


@pytest.fixture
def research_store(tmp_path, monkeypatch):
    from keprix.data_architecture.data_plane import WorkspaceDataPlane
    from keprix.research_workspace.store import ResearchWorkspaceStore

    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    store = ResearchWorkspaceStore(workspace_id=plane.workspace_id)
    store.plane = plane
    monkeypatch.setattr(
        "keprix.research_workspace.store.get_workspace_data_plane",
        lambda workspace_id="default": plane,
    )
    return store


@pytest.mark.asyncio
async def test_research_workspace_smoke(research_store, tmp_path: Path) -> None:
    """End-to-end research workflow: source, citation, note, dataset, PSPP, report, bundle."""
    sys.path.insert(0, str(EVALS))
    from validators import validate_report_claims

    from keprix.research_workspace.citations.bibtex import parse_bibtex
    from keprix.research_workspace.citations.bibliography import export_bibliography
    from keprix.research_workspace.citations.registry import CitationLibrary
    from keprix.research_workspace.datasets.dataset import DatasetManager
    from keprix.research_workspace.evidence import EvidenceService
    from keprix.research_workspace.obsidian.frontmatter import dump_frontmatter, parse_frontmatter
    from keprix.research_workspace.obsidian.markdown import analyze_markdown
    from keprix.research_workspace.obsidian.tags import tags_from_note
    from keprix.research_workspace.project import ResearchProjectService
    from keprix.research_workspace.source import ResearchSourceService
    from keprix.research_workspace.stats.pspp.output_parser import parse_text_tables
    from keprix.research_workspace.stats.pspp.syntax import generate_analysis_syntax
    from keprix.research_workspace.datasets.codebook import Codebook

    fixture = json.loads((EVALS / "citation-fixtures.json").read_text(encoding="utf-8"))
    dataset_fixture = json.loads((EVALS / "dataset-fixtures.json").read_text(encoding="utf-8"))
    pspp_fixture = json.loads((EVALS / "pspp-fixtures.json").read_text(encoding="utf-8"))
    report_fixture = json.loads((EVALS / "report-fixtures.json").read_text(encoding="utf-8"))

    projects = ResearchProjectService(research_store)
    sources = ResearchSourceService(research_store)
    evidence = EvidenceService(research_store)
    datasets = DatasetManager(research_store)
    citations = CitationLibrary(research_store)

    # 1. Create research project.
    project = projects.create(title="Smoke study", question="Does demand rise in Q1?", owner="smoke-user")
    assert project.project_id

    # 2. Import one source.
    source = sources.add(
        project.project_id,
        kind="url",
        ref="https://example.org/hydro-report",
        owner="smoke-user",
    )
    assert source.source_id

    # 3. Import BibTeX fixture.
    records = parse_bibtex(fixture["bibtex_sample"])
    saved = citations.save_records(project.project_id, records)
    assert saved
    assert records[0].citation_key == fixture["expected"]["citation_key"]

    # 4. Create Obsidian-style note.
    note_text = dump_frontmatter(
        {
            "title": "Field note",
            "tags": ["research", "literature"],
            "keprix_trace_id": project.trace_id,
        },
        "# Field note\n\nLinked source [[%s]].\n" % source.source_id,
    )
    note = analyze_markdown(note_text)
    meta, body = parse_frontmatter(note_text)
    tags = tags_from_note(meta, body)
    assert source.source_id in note.wikilinks
    assert "research" in tags

    # 5. Import one dataset.
    csv_path = tmp_path / "sample.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(dataset_fixture["csv_header"])
        writer.writerows(dataset_fixture["csv_rows"])
    imported = datasets.import_file(
        project.project_id,
        source_path=csv_path,
        name="smoke-dataset",
        owner="smoke-user",
    )
    assert imported["dataset_id"]

    # 6. Generate / verify codebook.
    codebook = datasets.load_codebook(imported["dataset_id"], 1)
    assert codebook is not None
    assert len(codebook.variables) == dataset_fixture["expected"]["column_count"]

    # 7. Generate PSPP syntax.
    data_path = research_store.plane.root / "datasets" / "derived" / imported["dataset_id"] / "v1" / "data.csv"
    workspace_root = research_store.plane.root
    syntax = generate_analysis_syntax(
        codebook=Codebook.from_dict(imported["codebook"]),
        data_path=data_path,
        workspace_root=workspace_root,
        procedures=pspp_fixture["procedures"],
    )
    assert "FREQUENCIES" in syntax

    # 8. Mocked statistical output.
    tables = parse_text_tables(pspp_fixture["mock_output_text"])
    assert tables

    # 9. Generate report with bibliography and cited claim.
    bibliography = export_bibliography(records, "report")
    report_body = "\n".join(
        [
            "# Smoke report",
            "",
            report_fixture["cited_claim"],
            "",
            bibliography,
        ]
    )
    assert "## Bibliography" in report_body
    assert not validate_report_claims(report_body, citation_keys=[records[0].citation_key])

    claim = evidence.add_claim(
        project.project_id,
        text="Demand increased in Q1",
        source_id=source.source_id,
        owner="smoke-user",
        approved=True,
    )
    assert claim["claim_id"]

    # 10. Export evidence bundle.
    bundle = evidence.build_bundle(project.project_id, label="smoke bundle", owner="smoke-user")
    chain = evidence.trace_lineage(project.project_id, claim["claim_id"])
    assert bundle.trace_id
    assert bundle.members
    assert chain
