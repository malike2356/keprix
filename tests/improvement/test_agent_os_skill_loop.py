"""Prompt 257 Agent OS skill proposal loop tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.improvement.session_pattern_detector import detect_session_patterns
from keprix.improvement.skill_improvement_loop import SkillRunRecord, propose_skill_improvements, record_skill_run
from keprix.improvement.skill_packager import package_skill
from keprix.improvement.skill_proposer import SkillProposalStore
from keprix.improvement.skill_review_reporter import generate_weekly_review


@pytest.fixture
def agent_os_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / ".keprix"
    root.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    return root


def test_import_from_workflow_audit_queue(agent_os_home: Path) -> None:
    queue = agent_os_home / "agent-os" / "skill-proposals-pending.json"
    queue.parent.mkdir(parents=True)
    queue.write_text(
        json.dumps(
            [
                {
                    "proposal_id": "p1",
                    "source": "audit",
                    "origin": "workflow_audit",
                    "slug": "daily-brief",
                    "name": "Daily brief",
                    "description": "Write daily brief from calendar and tasks",
                    "evidence_sessions": ["s1"],
                    "status": "pending",
                }
            ]
        ),
        encoding="utf-8",
    )

    imported = SkillProposalStore().import_pending_queue()

    assert len(imported) == 1
    assert imported[0].source == "audit"
    assert imported[0].evidence_sessions == ["s1"]
    assert not queue.exists()


def test_session_pattern_detector_uses_real_session_rows(agent_os_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]

    monkeypatch.setattr("keprix.improvement.session_pattern_detector.workspace_repo.list_sessions", lambda user, limit, offset: sessions)
    monkeypatch.setattr(
        "keprix.improvement.session_pattern_detector.workspace_repo.get_session",
        lambda user, session_id: {
            "messages": [
                {"role": "user", "content": "Prepare weekly sales pipeline report"},
                {"role": "assistant", "tool_calls": [{"name": "search_docs"}]},
            ]
        },
    )

    repeated = detect_session_patterns({"id": "u1"}, session_count=10, min_occurrences=3)

    assert len(repeated) == 1
    assert repeated[0].occurrence_count == 3
    assert repeated[0].sessions == ["s1", "s2", "s3"]


def test_package_skill_writes_valid_skill_md(agent_os_home: Path) -> None:
    store = SkillProposalStore()
    proposal = store.import_pending_queue()
    assert proposal == []
    saved = store.save(
        store.create_from_repeated_task(
            type(
                "Task",
                (),
                {
                    "description": "Prepare weekly sales pipeline report",
                    "sessions": ["s1", "s2", "s3"],
                    "tools_used": ["search_docs"],
                    "occurrence_count": 3,
                    "confidence": 0.85,
                    "estimated_tokens_per_run": 120,
                },
            )()
        )
    )

    approved = package_skill(saved.proposal_id, store=store)
    skill_md = Path(approved.skill_path or "") / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    frontmatter = content.split("---", 2)[1]
    parsed = yaml.safe_load(frontmatter)

    assert approved.status == "approved"
    assert parsed["name"] == approved.slug
    assert parsed["description"]
    assert "Procedure" in content


def test_skill_improvement_loop_creates_followup_proposal(agent_os_home: Path) -> None:
    for index in range(3):
        record_skill_run(
            SkillRunRecord(
                run_id=f"r{index}",
                skill_slug="daily-brief",
                follow_up_action="also send this to the leadership channel",
                session_id=f"s{index}",
            )
        )

    proposals = propose_skill_improvements()

    assert len(proposals) == 1
    assert proposals[0].source == "improvement_loop"
    assert proposals[0].occurrence_count == 3


def test_review_report_groups_proposals(agent_os_home: Path) -> None:
    store = SkillProposalStore()
    proposal = store.create_from_repeated_task(
        type(
            "Task",
            (),
            {
                "description": "Prepare weekly sales pipeline report",
                "sessions": ["s1", "s2", "s3"],
                "tools_used": [],
                "occurrence_count": 3,
                "confidence": 0.85,
                "estimated_tokens_per_run": 120,
            },
        )()
    )
    store.reject(proposal.proposal_id)

    report = generate_weekly_review(store)

    assert len(report["rejected"]) == 1
    assert report["pending"] == []


def test_skill_proposal_routes_import_and_approve(agent_os_home: Path) -> None:
    queue = agent_os_home / "agent-os" / "skill-proposals-pending.json"
    queue.parent.mkdir(parents=True)
    queue.write_text(
        json.dumps(
            [
                {
                    "proposal_id": "p-route",
                    "source": "audit",
                    "slug": "support-triage",
                    "name": "Support triage",
                    "description": "Triage support queue every morning",
                    "evidence_sessions": [],
                    "status": "pending",
                }
            ]
        ),
        encoding="utf-8",
    )
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    imported = client.post("/api/agent-os/skill-proposals/import")
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1

    approved = client.post("/api/agent-os/skill-proposals/p-route/approve")
    assert approved.status_code == 200
    assert approved.json()["proposal"]["status"] == "approved"
    assert (agent_os_home / "skills" / "support-triage" / "SKILL.md").is_file()
