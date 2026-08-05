"""First-message onboarding on the HTTP conversation path."""

from __future__ import annotations

import yaml

from keprix.agent.onboarding_hooks import first_message_system_suffix, is_first_user_message


def test_is_first_user_message_empty_history():
    assert is_first_user_message([]) is True
    assert is_first_user_message([{"role": "assistant", "content": "hi"}]) is True


def test_is_first_user_message_after_user_turn():
    history = [{"role": "user", "content": "hello"}]
    assert is_first_user_message(history) is False


def test_first_message_directive_once(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cfg_path = home / "config.yaml"
    cfg_path.write_text(yaml.safe_dump({"onboarding": {"profile_build": "ask"}}), encoding="utf-8")
    monkeypatch.setenv("KEPRIX_HOME", str(home))

    suffix = first_message_system_suffix(history=[], config_path=cfg_path)
    assert "first message ever" in suffix.lower()
    assert "OFFER" in suffix

    loaded = yaml.safe_load(cfg_path.read_text())
    assert loaded["onboarding"]["seen"]["profile_build_offered"] is True

    again = first_message_system_suffix(history=[], config_path=cfg_path)
    assert again == ""


def test_first_message_skipped_when_not_first_turn(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cfg_path = home / "config.yaml"
    cfg_path.write_text("onboarding:\n  profile_build: ask\n", encoding="utf-8")
    monkeypatch.setenv("KEPRIX_HOME", str(home))

    history = [{"role": "user", "content": "prior"}]
    assert first_message_system_suffix(history=history, config_path=cfg_path) == ""
