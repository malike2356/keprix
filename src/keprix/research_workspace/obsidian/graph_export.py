"""Export keprix research relationships as Obsidian wiki links."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.research_workspace.obsidian.markdown import wikilink
from keprix.research_workspace.obsidian.templates import note_filename, render_research_note
from keprix.research_workspace.store import ResearchWorkspaceStore


def export_obsidian_vault(store: ResearchWorkspaceStore, project_id: str, dest: Path) -> dict[str, Any]:
    project = store.get_project(project_id)
    if project is None:
        raise ValueError("Project not found")
    dest.mkdir(parents=True, exist_ok=True)
    project_dir = dest / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    trace_id = project.get("trace_id") or project_id

    index_name = "index"
    index_body = (project.get("question") or "").strip()
    index_content = render_research_note(
        "research_summary",
        title=project["title"],
        body=index_body or "Research project index.",
        project_id=project_id,
        trace_id=trace_id,
        extra_meta={"review_status": "approved", "tags": ["research", "keprix", "index"]},
    )
    (project_dir / "index.md").write_text(index_content, encoding="utf-8")

    with store.plane.connect() as conn:
        sources = conn.execute(
            "SELECT * FROM research_sources WHERE project_id = ?", (project_id,)
        ).fetchall()
        claims = conn.execute(
            "SELECT * FROM research_claims WHERE project_id = ?", (project_id,)
        ).fetchall()
        citations = conn.execute(
            "SELECT * FROM research_citations WHERE project_id = ?", (project_id,)
        ).fetchall()

    objects = store.list_objects(project_id)
    datasets = [obj for obj in objects if obj.get("object_type") == "dataset"]
    analysis_runs = [obj for obj in objects if obj.get("object_type") == "analysis_run"]
    reports = [obj for obj in objects if obj.get("object_type") == "report"]

    source_names: dict[str, str] = {}
    for row in sources:
        source = dict(row)
        source_id = source["source_id"]
        name = note_filename("source", source_id).removesuffix(".md")
        source_names[source_id] = name
        metadata = json.loads(source["metadata_json"] or "{}")
        body = (
            f"- kind: {source['kind']}\n"
            f"- ref: {source['ref']}\n"
            + (f"- title: {metadata.get('title')}\n" if metadata.get("title") else "")
        )
        content = render_research_note(
            "source",
            title=metadata.get("title") or f"Source {source_id}",
            body=body,
            project_id=project_id,
            trace_id=source.get("trace_id") or trace_id,
            source_id=source_id,
            backlinks=[index_name],
        )
        (project_dir / note_filename("source", source_id)).write_text(content, encoding="utf-8")

    claim_names: dict[str, str] = {}
    for row in claims:
        claim = dict(row)
        claim_id = claim["claim_id"]
        name = note_filename("claim", claim_id).removesuffix(".md")
        claim_names[claim_id] = name
        backlinks = [index_name]
        if claim["source_id"] and claim["source_id"] in source_names:
            backlinks.append(source_names[claim["source_id"]])
        content = render_research_note(
            "claim",
            title=f"Claim {claim_id}",
            body=claim["text"],
            project_id=project_id,
            trace_id=claim.get("trace_id") or trace_id,
            source_id=claim.get("source_id"),
            backlinks=backlinks,
        )
        (project_dir / note_filename("claim", claim_id)).write_text(content, encoding="utf-8")

    for row in citations:
        citation = dict(row)
        cite_id = citation["citation_id"]
        backlinks = [index_name]
        if citation["source_id"] and citation["source_id"] in source_names:
            backlinks.append(source_names[citation["source_id"]])
        for claim_id, claim_name in claim_names.items():
            claim_row = next((c for c in claims if c["claim_id"] == claim_id), None)
            if claim_row and claim_row["source_id"] == citation["source_id"]:
                backlinks.append(claim_name)
        body = f"Citation label: {citation['label']}"
        content = render_research_note(
            "literature",
            title=citation["label"],
            body=body,
            project_id=project_id,
            trace_id=trace_id,
            source_id=citation.get("source_id"),
            backlinks=backlinks,
        )
        (project_dir / note_filename("literature", cite_id)).write_text(content, encoding="utf-8")

    dataset_names: dict[str, str] = {}
    for dataset in datasets:
        object_id = dataset["object_id"]
        name = note_filename("dataset", object_id).removesuffix(".md")
        dataset_names[object_id] = name
        payload = dataset.get("payload") or {}
        body = f"- path: {payload.get('path', dataset.get('source_ref'))}\n- format: {payload.get('format', 'unknown')}"
        content = render_research_note(
            "dataset",
            title=payload.get("name") or f"Dataset {object_id}",
            body=body,
            project_id=project_id,
            trace_id=dataset.get("trace_id") or trace_id,
            source_id=dataset.get("source_ref"),
            backlinks=[index_name],
        )
        (project_dir / note_filename("dataset", object_id)).write_text(content, encoding="utf-8")

    for run in analysis_runs:
        object_id = run["object_id"]
        payload = run.get("payload") or {}
        backlinks = [index_name]
        dataset_id = payload.get("dataset_id")
        if dataset_id and dataset_id in dataset_names:
            backlinks.append(dataset_names[dataset_id])
        body = f"- tool: {payload.get('tool')}\n- status: {payload.get('status', 'queued')}"
        content = render_research_note(
            "field",
            title=f"Analysis {object_id}",
            body=body,
            project_id=project_id,
            trace_id=run.get("trace_id") or trace_id,
            backlinks=backlinks,
        )
        (project_dir / note_filename("field", object_id)).write_text(content, encoding="utf-8")

    for report in reports:
        object_id = report["object_id"]
        payload = report.get("payload") or {}
        backlinks = [index_name]
        for run in analysis_runs:
            backlinks.append(note_filename("field", run["object_id"]).removesuffix(".md"))
        body = f"- path: {payload.get('path', report.get('source_ref'))}"
        content = render_research_note(
            "research_summary",
            title=payload.get("title") or f"Report {object_id}",
            body=body,
            project_id=project_id,
            trace_id=report.get("trace_id") or trace_id,
            backlinks=backlinks,
        )
        (project_dir / note_filename("research_summary", object_id)).write_text(content, encoding="utf-8")

    graph_path = project_dir / "graph-links.md"
    graph_lines = ["# Graph links", ""]
    for row in claims:
        claim = dict(row)
        if claim["source_id"] and claim["source_id"] in source_names:
            graph_lines.append(
                f"- {wikilink(source_names[claim['source_id']])} -> {wikilink(claim_names[claim['claim_id']])}"
            )
    for row in citations:
        citation = dict(row)
        if citation["source_id"] and citation["source_id"] in source_names:
            graph_lines.append(
                f"- {wikilink(source_names[citation['source_id']])} -> {wikilink(note_filename('literature', citation['citation_id']).removesuffix('.md'))}"
            )
    for dataset in datasets:
        object_id = dataset["object_id"]
        for run in analysis_runs:
            if (run.get("payload") or {}).get("dataset_id") == object_id:
                graph_lines.append(
                    f"- {wikilink(dataset_names[object_id])} -> {wikilink(note_filename('field', run['object_id']).removesuffix('.md'))}"
                )
    for report in reports:
        for run in analysis_runs:
            graph_lines.append(
                f"- {wikilink(note_filename('field', run['object_id']).removesuffix('.md'))} -> {wikilink(note_filename('research_summary', report['object_id']).removesuffix('.md'))}"
            )
    graph_path.write_text("\n".join(graph_lines) + "\n", encoding="utf-8")

    return {"path": str(project_dir), "files": len(list(project_dir.glob("*.md")))}
