from pathlib import Path

import pytest

from keprix.agent.ladder import PONYTAIL_LADDER_PROMPT, build_coding_prompt, bundled_ladder_path
from keprix.agent.ladder_mode import get_ladder_mode, set_ladder_mode


def test_ladder_prompt_and_bundle_exist() -> None:
    assert "Before writing any code" in PONYTAIL_LADDER_PROMPT
    assert "YAGNI" in build_coding_prompt("base")
    assert bundled_ladder_path().is_file()


def test_ladder_mode_defaults_and_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    assert get_ladder_mode().mode == "full"
    assert set_ladder_mode("lite").mode == "lite"
    assert get_ladder_mode().mode == "lite"

    with pytest.raises(ValueError):
        set_ladder_mode("invalid")
