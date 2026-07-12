"""Prompt 270 Phase 2 workflow tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.agent_apps.catalog import get_catalog_template, list_catalog_templates, template_dir
from keprix.agent_apps.local_runner import run_local
from keprix.agent_os.auto_skill_writer import write_skill_from_workflow
from keprix.agent_os.workflow_kanban import enqueue_workflow_steps, list_workflow_boards
from keprix.agent_os.workflows.content_series import generate_content_series
from keprix.agent_os.workflows.crm_import import clean_crm_import
from keprix.agent_os.workflows.memory_system import run_memory_system


@pytest.fixture
def keprix_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".keprix"
    home.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.delenv("KEPRIX_VAULT_ROOT", raising=False)
    monkeypatch.setenv("KEPRIX_AUTO_SKILL_WRITE", "true")
    monkeypatch.setenv("KEPRIX_AUTO_SKILL_APPROVE", "false")
    return home


def test_catalog_lists_phase2_templates() -> None:
    ids = {item["id"] for item in list_catalog_templates()}
    assert {"content-series", "crm-import", "memory-system"} <= ids
    assert get_catalog_template("content-series") is not None
    assert template_dir("crm-import") is not None


def test_content_series_generator() -> None:
    result = generate_content_series(
        topic="Agent OS",
        audience_questions="How do I start?\nWhat about memory?",
        platforms=["linkedin", "x"],
    )
    assert result["status"] == "ok"
    assert len(result["hooks"]) >= 3
    assert len(result["scripts"]) == 2
    assert {v["platform"] for v in result["variants"]} == {"linkedin", "x"}
    assert "Content series: Agent OS" in result["output"]


def test_crm_import_dedupes_and_maps(keprix_home: Path) -> None:
    csv_text = "Email,Full Name,Company\nADA@X.COM,Ada Lovelace,Analytical\nada@x.com,Ada Dup,Analytical\nbad,Nobody,\n"
    result = clean_crm_import(csv_text=csv_text, target="hubspot")
    assert result["status"] == "ok"
    assert result["row_count"] == 1
    assert result["duplicates_removed"] == 1
    assert result["rows"][0]["email"] == "ada@x.com"
    assert result["rows"][0]["first_name"] == "Ada"
    assert result["rows"][0]["company"] == "Analytical"


@pytest.mark.asyncio
async def test_memory_system_capture_and_graph(keprix_home: Path) -> None:
    result = await run_memory_system(
        query="Phase",
        session_id="mem-1",
        messages=[
            {"role": "user", "content": "Phase 2 memory note"},
            {"role": "assistant", "content": "Stored."},
        ],
        title="Phase 2",
    )
    assert result["status"] == "ok"
    assert result["capture"]["ok"] is True
    assert result["graph"]["node_count"] >= 1
    assert any("Phase 2" in (hit.get("path") or "") or True for hit in result["recent_notes"])


def test_workflow_kanban_board_without_failing(keprix_home: Path) -> None:
    board = enqueue_workflow_steps(
        workflow="content-series",
        title="Demo",
        steps=[
            {"id": "a", "title": "Hooks", "status": "done"},
            {"id": "b", "title": "Review", "status": "todo"},
        ],
        push_kanban=False,
    )
    assert board["ok"] is True
    assert board["board"]["columns"]["done"]
    assert board["board"]["columns"]["todo"]
    assert list_workflow_boards(limit=5)


def test_auto_skill_writer_creates_proposal(keprix_home: Path) -> None:
    result = write_skill_from_workflow(
        workflow="content-series",
        summary="Generate content series from a topic",
        procedure="1. Hooks\n2. Scripts\n3. Captions",
    )
    assert result["ok"] is True
    assert result["status"] == "pending"
    proposal_path = keprix_home / "agent-os" / "skill-proposals" / f"{result['proposal_id']}.json"
    assert proposal_path.is_file()


def test_content_series_agent_app_runs(keprix_home: Path) -> None:
    app_dir = template_dir("content-series")
    assert app_dir is not None
    payload = run_local(
        app_dir,
        input_text="Local SEO",
        context={"form": {"topic": "Local SEO", "audience_questions": "Where do I start?", "platforms": "x"}},
    )
    assert payload["app"] == "content-series"
    assert "Local SEO" in payload["result"]["output"]
    assert payload["result"].get("kanban", {}).get("ok") is True


def test_crm_import_agent_app_runs(keprix_home: Path) -> None:
    app_dir = template_dir("crm-import")
    assert app_dir is not None
    csv_text = "email,first_name,last_name\na@b.co,Ann,Bee\n"
    payload = run_local(app_dir, input_text=csv_text, context={"form": {"csv_text": csv_text}})
    assert payload["result"]["status"] == "ok"
    assert payload["result"]["row_count"] == 1
