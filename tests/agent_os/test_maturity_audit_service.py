"""Prompt 274 maturity audit service tests."""

from __future__ import annotations

from pathlib import Path

from keprix.agent_os.maturity_audit_service import MaturityAuditService


def test_maturity_total_is_sum_of_four_scores(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    (workspace / "context").mkdir(parents=True)
    (workspace / "context" / "about-business.md").write_text("We sell analytics to schools. ICP ops.", encoding="utf-8")
    (workspace / "context" / "about-me.md").write_text("Pains", encoding="utf-8")
    (workspace / "context" / "priorities.md").write_text("90-day priorities\n- retention", encoding="utf-8")
    (workspace / "context" / "writing-samples.md").write_text("sample", encoding="utf-8")
    (workspace / "connections.md").write_text("revenue\nstatus: live\ncalendar\nstatus: live\n", encoding="utf-8")

    result = MaturityAuditService().run(workspace_id="demo", workspace_path=str(workspace))

    assert result.total_score == round(sum(score.score for score in result.scores), 2)
    assert next(score for score in result.scores if score.dimension == "context").score >= 15
    assert result.top_gaps


def test_export_to_level_up_schema(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    service = MaturityAuditService()
    result = service.run(workspace_id="demo", workspace_path=str(workspace))

    payload = service.export_to_level_up(result.audit_id)

    assert payload["schema"] == "keprix.level_up.input.v1"
    assert payload["audit_id"] == result.audit_id
