"""End-to-end smoke test for Phase 14 expanded agent DNA (prompt 73)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "keprix"
DOCS = ROOT / "docs"


@pytest.mark.asyncio
async def test_expanded_agent_dna_smoke(tmp_path: Path) -> None:
    """Exercise shipped Phase 14 surfaces in one deterministic fixture run."""
    run_id = "dna-smoke-run"
    user_id = "dna-smoke-user"

    # 1. Typed agent DI + schema export (prompt 66).
    from keprix.typed_agents.deps_factory import build_support_dependencies
    from keprix.typed_agents.agent import create_support_agent
    from keprix.typed_agents.schemas import AgentRunContext

    deps = await build_support_dependencies(workspace_id="dna-smoke", user_id=user_id)
    agent = create_support_agent()
    schemas = agent.export_schemas(AgentRunContext(workspace_id="dna-smoke", user_id=user_id))
    assert schemas["agent_name"] == "support-agent"
    result = await agent.run(
        deps=deps,
        context=AgentRunContext(workspace_id="dna-smoke", user_id=user_id, trace_id=run_id),
        tool_calls=[{"name": "lookup_ticket", "arguments": {"ticket_id": "TCK-001"}}],
        raw_output={"ticket_id": "TCK-001", "resolution": "Reset cache", "cited_policy": "support-v1"},
        auto_approve=True,
    )
    assert result.output.ticket_id == "TCK-001"

    # 2. Mount one kernel plugin and invoke it.
    from keprix.kernel.function_contract import FunctionContract, InvocationKind, clear_invocation_traces, get_invocation_traces, invoke_function
    from keprix.kernel.plugin_contract import KernelPlugin, get_plugin_registry

    clear_invocation_traces()
    registry = get_plugin_registry()

    def echo_handler(arguments: dict, _context: dict) -> dict:
        return {"echo": arguments.get("text", "")}

    plugin = KernelPlugin(
        name="dna-smoke-plugin",
        version="0.1.0",
        functions=[
            FunctionContract(
                name="echo",
                description="Echo text",
                input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                invocation=InvocationKind.NATIVE,
                handler=echo_handler,
            )
        ],
    )
    registry.register(plugin)
    echo_fn = plugin.get_function("echo")
    assert echo_fn is not None
    invoke_function(plugin.name, echo_fn, {"text": "phase-14"})
    traces = get_invocation_traces()
    assert traces
    assert traces[-1]["function_name"] == "echo"

    # 3. Build one RAG pipeline ingest + query.
    from keprix.rag_pipeline.pipeline import RagPipeline

    rag = RagPipeline("dna-smoke-rag", store_kind="memory")
    await rag.ingest(
        user_id=user_id,
        source_type="plaintext",
        source_id="dna-doc",
        content="Building 3 HVAC maintenance occurs every Monday morning.",
    )
    rag_result = await rag.query(user_id=user_id, question="What happens on Monday in Building 3?")
    assert rag_result.context.citations or rag_result.context.answer

    # 4. Document query with citations.
    from keprix.documents.index_manager import DocumentIndexManager
    from keprix.documents.query_engine import DocumentQueryEngine
    from keprix.memory.rag.indexer import RagIndexer

    indexer = RagIndexer()
    manager = DocumentIndexManager(indexer=indexer, store_path=tmp_path / "dna-indexes.json")
    index = manager.create_index(user_id=user_id, name="DNA")
    await manager.add_document(
        index.index_id,
        source_id="dna-note.md",
        source_type="markdown",
        content="Building 3 requires weekly HVAC inspection.",
    )
    doc_result = await DocumentQueryEngine(indexer=indexer).query(
        user_id,
        "What does Building 3 require?",
        evidence_first=True,
    )
    assert doc_result.citations
    assert doc_result.answer

    # 5. Browser dry run skill.
    from keprix.browser.browser_profile import ProfileKind, get_profile_store
    from keprix.browser.browser_skill import run_skill
    from keprix.browser.harness import get_harness_manager

    profile = get_profile_store().create(
        workspace_id="dna-smoke",
        name="disposable",
        kind=ProfileKind.DISPOSABLE,
    )
    harness, _record = get_harness_manager().open_session(
        workspace_id="dna-smoke",
        objective="checkout dry run",
        profile_id=profile.id,
    )
    browser_result = run_skill("checkout_dry_run", harness, {"approved": True})
    assert browser_result.get("dry_run") is True

    # 6. Coding dry run.
    from keprix.coding.issue_runner import IssueRunRequest, run_issue

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# DNA smoke\n", encoding="utf-8")
    coding_result = run_issue(
        IssueRunRequest(
            issue="Update README title to DNA smoke repo",
            repo_path=repo,
            dry_run=True,
            human_approved=True,
        )
    )
    assert coding_result.test_summary == "dry run"

    # 7. Hand off to one specialist agent via crew delegation.
    from keprix.teams.agent_role import AgentRole
    from keprix.teams.crew import Crew
    from keprix.teams.task import TeamTask

    coordinator = AgentRole(
        name="coordinator",
        goal="Coordinate work",
        delegation_policy="allowed",
    )
    crew = Crew(
        name="dna-smoke-crew",
        roles={
            "coordinator": coordinator,
            "qa_reviewer": AgentRole(name="qa_reviewer", goal="Review outputs"),
        },
        tasks=[
            TeamTask(
                id="review-task",
                description="Prepare draft for review sign-off",
                role="coordinator",
                allow_delegation=True,
                expected_output="review.md",
            )
        ],
    )
    crew_state = await crew.run("Ship DNA smoke path", initial_state={})
    delegated = crew_state["task_results"]["review-task"]
    assert delegated["delegated_to"] == "qa_reviewer"

    # 8. Trace already created by kernel invoke; assert playbook trace from RAG.
    assert rag_result.playbook_run_id

    # 9. Improvement proposal from a recorded run.
    from keprix.improvement.run_analyzer import RunAnalyzer, RunRecord

    analyzer = RunAnalyzer()
    record = RunRecord(
        run_id=run_id,
        agent_id="dna-smoke-agent",
        ok=False,
        steps=[{"name": "retrieve", "ok": False}],
        metadata={"task": "dna smoke"},
    )
    analyzer.save_run(record)
    proposals = analyzer.analyze(record)
    assert proposals

    # 10. Export run as artifact bundle.
    from keprix.agent_apps.app_manifest import load_manifest
    from keprix.agent_apps.deployment_bundle import build_deployment_bundle
    from keprix.agent_apps.registry import sample_app_dir

    sample_dir = sample_app_dir()
    manifest = load_manifest(sample_dir)
    bundle_path = tmp_path / "hello-agent.zip"
    bundle = build_deployment_bundle(sample_dir, bundle_path)
    assert bundle_path.exists()
    assert bundle["app"] == manifest.name


def test_phase_14_docs_link_prompts_60_through_73() -> None:
    release_map = (DOCS / "expanded-reference-agent-release-map.md").read_text(encoding="utf-8")
    build_order = (DOCS / "phase-14-build-order.md").read_text(encoding="utf-8")
    capability_map = (DOCS / "agent-dna-capability-map.md").read_text(encoding="utf-8")

    for prompt in range(60, 74):
        token = str(prompt)
        assert token in release_map or token in build_order or token in capability_map

    assert "51" in build_order
    assert "59" in build_order


def test_expanded_adoption_matrix_covers_twelve_reference_agents() -> None:
    capability_map = (DOCS / "agent-dna-capability-map.md").read_text(encoding="utf-8")
    references = [
        "OpenHands",
        "Aider",
        "browser-use",
        "smolagents",
        "OpenAI Agents SDK",
        "Pydantic AI",
        "Google ADK",
        "Semantic Kernel",
        "LlamaIndex",
        "Mastra",
        "Agno",
        "Haystack",
    ]
    for name in references:
        assert name in capability_map
    assert capability_map.count("- [x]") >= 12


def test_boundary_checks_no_carina_branding_in_workspace_nav() -> None:
    navigation = (ROOT / "frontend" / "src" / "lib" / "navigation.ts").read_text(encoding="utf-8")
    assert "carina" not in navigation.lower()


def test_boundary_checks_phase14_modules_avoid_recipe_terminology() -> None:
    modules = [
        SRC / "rag_pipeline",
        SRC / "kernel",
        SRC / "agent_apps",
        SRC / "documents",
    ]
    pattern = re.compile(r"\brecipe\b", re.IGNORECASE)
    for module in modules:
        if not module.exists():
            continue
        for path in module.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert not pattern.search(text), f"recipe terminology found in {path}"


def test_phase_14_docs_have_no_dash_violations() -> None:
    forbidden = ("\u2014", "\u2013")
    for rel in (
        "expanded-reference-agent-release-map.md",
        "agent-dna-capability-map.md",
        "phase-14-build-order.md",
    ):
        content = (DOCS / rel).read_text(encoding="utf-8")
        for char in forbidden:
            assert char not in content, f"forbidden dash in {rel}"
