"""Prompt 275 level-up service tests."""

from __future__ import annotations

from pathlib import Path

from keprix.agent_os.level_up_service import LevelUpService
from keprix.agent_os.maturity_audit_service import MaturityAuditService


def test_generate_plan_from_maturity_audit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    audit = MaturityAuditService().run(workspace_id="demo", workspace_path=str(workspace))

    plan = LevelUpService().generate(audit_id=audit.audit_id, workspace_path=str(workspace))

    assert len(plan.actions) >= 3
    assert plan.actions[0].leverage in {"high", "medium"}


def test_safe_stubs_create_only_workspace_files_and_reaudit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    service = LevelUpService()
    audit = MaturityAuditService().run(workspace_id="demo", workspace_path=str(workspace))
    plan = service.generate(audit_id=audit.audit_id, workspace_path=str(workspace))

    result = service.apply_safe_stubs(plan.plan_id)
    re_audit = service.re_audit(plan.plan_id)["audit"]

    assert all(str(path).startswith(str(workspace)) for path in result["written"])
    assert (workspace / "connections.md").is_file()
    assert re_audit["total_score"] >= audit.total_score


def test_complete_action_marks_done(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    audit = MaturityAuditService().run(workspace_id="demo", workspace_path=str(workspace))
    plan = LevelUpService().generate(audit_id=audit.audit_id, workspace_path=str(workspace))

    updated = LevelUpService().complete_action(plan.plan_id, plan.actions[0].id)

    assert updated.actions[0].completed is True
