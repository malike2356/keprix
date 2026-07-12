"""Prompt 274 maturity scorer tests."""

from __future__ import annotations

from pathlib import Path

from keprix.agent_os.maturity_scorers import score_connections, score_context


def test_empty_workspace_has_low_context_score(tmp_path: Path) -> None:
    score = score_context(tmp_path)

    assert score.score == 0
    assert "context/about-business.md" in score.gaps[0]


def test_context_files_from_onboard_score_at_least_15(tmp_path: Path) -> None:
    context = tmp_path / "context"
    context.mkdir()
    (context / "about-business.md").write_text("We sell automation. ICP is agencies.", encoding="utf-8")
    (context / "about-me.md").write_text("Founder with reporting pains.", encoding="utf-8")
    (context / "priorities.md").write_text("90 day priorities\n- launch", encoding="utf-8")
    (context / "writing-samples.md").write_text("Sample", encoding="utf-8")

    score = score_context(tmp_path)

    assert score.score >= 15


def test_connections_with_two_live_domains_scores(tmp_path: Path) -> None:
    root = tmp_path
    (root / "connections.md").write_text(
        "revenue\nstatus: live\n\ncalendar\nstatus: live\n\ncustomer\nstatus: draft\n",
        encoding="utf-8",
    )

    score, missing = score_connections(root)

    assert score.score == 8.5
    assert "customer" in missing
