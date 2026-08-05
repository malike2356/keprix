"""Tests for computer-use deliverable paths (Prompt 293)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.deliverable_paths import (
    DeliverableIntent,
    DeliverableZone,
    classify_deliverable_intent,
    copy_to_outputs,
    is_presentable,
    list_presented_files,
    resolve_deliverable_layout,
    short_vs_long_strategy,
)
from agent.layers.execution import EXECUTION_LAYER
from agent.skill_first import SkillFirstGate, apply_skill_first_gate
from tools.present_files_tool import present_files_tool


def test_execution_layer_includes_deliverable_contract() -> None:
    assert "Deliverable paths" in EXECUTION_LAYER
    assert "present_files" in EXECUTION_LAYER
    assert "scratch" in EXECUTION_LAYER.lower()
    assert "outputs" in EXECUTION_LAYER.lower()


def test_layout_creates_three_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    layout = resolve_deliverable_layout("sess-a", cwd=tmp_path)
    assert layout.scratch_dir.is_dir()
    assert layout.uploads_dir.is_dir()
    assert layout.outputs_dir.is_dir()
    assert layout.session_id == "sess-a"


def test_scratch_not_presentable(tmp_path: Path) -> None:
    layout = resolve_deliverable_layout("s1", cwd=tmp_path)
    scratch_file = layout.scratch_dir / "draft.md"
    scratch_file.write_text("# draft\n", encoding="utf-8")
    assert layout.zone_for(scratch_file) == DeliverableZone.SCRATCH
    assert not is_presentable(scratch_file, layout)

    result = json.loads(present_files_tool(paths=[str(scratch_file)], session_id="s1"))
    assert result["success"] is False
    assert "scratch" in result["rejected"][0]["reason"]


def test_outputs_presentable_and_indexed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KEPRIX_SESSION_ID", "s2")
    layout = resolve_deliverable_layout("s2", cwd=tmp_path)
    out = layout.outputs_dir / "report.md"
    out.write_text("# Report\n", encoding="utf-8")

    result = json.loads(present_files_tool(path=str(out), session_id="s2", title="Report"))
    assert result["success"] is True
    assert result["paths"] == [str(out.resolve())]
    assert "MEDIA:" in result["media"]
    assert list_presented_files(layout)[0]["path"] == str(out.resolve())


def test_copy_scratch_to_outputs_then_present(tmp_path: Path) -> None:
    layout = resolve_deliverable_layout("s3", cwd=tmp_path)
    draft = layout.scratch_dir / "long.md"
    draft.write_text("x\n" * 120, encoding="utf-8")
    assert short_vs_long_strategy(120) == "long"

    final = copy_to_outputs(draft, layout=layout)
    assert layout.zone_for(final) == DeliverableZone.OUTPUTS
    result = json.loads(present_files_tool(paths=[str(final)], session_id="s3"))
    assert result["success"] is True


def test_classify_deliverable_intent() -> None:
    assert classify_deliverable_intent("Write a blog post about Keprix") == DeliverableIntent.FILE
    assert classify_deliverable_intent("Create a presentation deck") == DeliverableIntent.FILE
    assert classify_deliverable_intent("Brainstorm strategy options") == DeliverableIntent.INLINE
    assert classify_deliverable_intent("Summarize this briefly") == DeliverableIntent.INLINE
    assert classify_deliverable_intent("Please save as a pdf") == DeliverableIntent.FILE


def test_present_files_not_skill_first_gated(tmp_path: Path) -> None:
    from types import SimpleNamespace

    catalog = [
        {
            "name": "pptx",
            "description": "Create PowerPoint presentations",
            "category": "documents",
            "triggers": ["pptx"],
        }
    ]
    gate = SkillFirstGate(profile="standard", skill_catalog=catalog)
    agent = SimpleNamespace(
        _skill_first=True,
        _skill_first_profile="standard",
        _skill_first_config={},
        _skill_first_gate=gate,
    )
    # Creating still gated.
    blocked = apply_skill_first_gate(agent, "write_file", {"path": "deck.pptx"})
    assert blocked is not None
    # Presenting is soft / ungated.
    assert apply_skill_first_gate(agent, "present_files", {"path": "out.md"}) is None
