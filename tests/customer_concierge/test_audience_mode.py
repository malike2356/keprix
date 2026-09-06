from __future__ import annotations

from keprix.customer_concierge import audience_mode


def test_audience_mode_defaults_to_team_and_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audience_mode, "get_keprix_home", lambda: tmp_path)
    assert audience_mode.get_audience_mode("ws") == "team"
    saved = audience_mode.set_audience_mode("ws", "both")
    assert saved["mode"] == "both"
    assert saved["publicConciergeEnabled"] is True
    assert saved["internalWorkspaceEnabled"] is True


def test_invalid_audience_mode_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audience_mode, "get_keprix_home", lambda: tmp_path)
    try:
        audience_mode.set_audience_mode("ws", "everyone")
    except ValueError as exc:
        assert "mode" in str(exc)
    else:
        raise AssertionError("invalid mode was accepted")


def test_mode_is_explicit_only_after_owner_choice(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audience_mode, "get_keprix_home", lambda: tmp_path)
    assert audience_mode.audience_mode_is_explicit("ws") is False
    audience_mode.set_audience_mode("ws", "team")
    assert audience_mode.audience_mode_is_explicit("ws") is True
