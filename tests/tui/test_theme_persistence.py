import json

from keprix.tui.preferences import load_theme_preference, save_busy_input_override, save_theme_preference


def test_theme_preference_persists_under_keprix_home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))

    assert load_theme_preference() == "Keprix Matrix"
    assert save_theme_preference("operator dark") == "Operator Dark"
    assert load_theme_preference() == "Operator Dark"

    payload = json.loads((tmp_path / "tui.json").read_text(encoding="utf-8"))
    assert payload["theme"] == "Operator Dark"


def test_theme_preference_preserves_other_preferences(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))

    save_busy_input_override("queue")
    save_theme_preference("Focus Light")

    payload = json.loads((tmp_path / "tui.json").read_text(encoding="utf-8"))
    assert payload["busy_input_mode"] == "queue"
    assert payload["theme"] == "Focus Light"
