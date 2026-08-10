"""Conveyor audit tests."""

from __future__ import annotations

from pathlib import Path

from keprix.conveyor import generate_fixes_for_report, run_full_audit, run_pipeline


def test_audit_runs_13_layers(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / ".gitignore").write_text("node_modules\n")
    (tmp_path / "src" / "config.js").write_text("const API_KEY = 'sk-test-hardcoded-secret-value';\n")
    (tmp_path / "src" / "api.js").write_text('res.json({stack: err.stack})\n')
    (tmp_path / ".env").write_text("DATABASE_URL=postgres://localhost/shared\n")
    report = run_full_audit(tmp_path)
    assert len(report["layers"]) == 13
    assert report["passed"] is False
    fixes = generate_fixes_for_report(report)
    assert fixes and all(f["requiresHumanApproval"] is True for f in fixes)
    result = run_pipeline(tmp_path, "staging", human_approval=False)
    assert result["status"]["state"] == "failed"


def test_pipeline_awaits_approval_when_passing(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".env\nnode_modules\n")
    (tmp_path / ".env.example").write_text("DATABASE_URL=\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "server.py").write_text(
        "import helmet\n"  # noqa: not real
        "rateLimit\n"
        "session maxAge cookie\n"
        "revokeSession\n"
        "logger.info\n"
        "/health\n"
        "publicError\n"
        "backup disaster recovery pg_dump restore\n"
        "gdpr privacy consent\n"
        "cache redis\n"
        "cors helmet\n"
        "get_current_user\n"
    )
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: ci\n")
    (tmp_path / "deploy-atomic.sh").write_text("rollback blue-green\n")
    report = run_full_audit(tmp_path)
    assert report["passed"] is True
    waiting = run_pipeline(tmp_path, "staging", human_approval=False)
    assert waiting["status"]["state"] == "awaiting_approval"
