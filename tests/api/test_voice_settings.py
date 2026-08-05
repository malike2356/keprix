from __future__ import annotations

from pathlib import Path

import pytest

from keprix.api.voice_settings import update_voice_settings, voice_settings_snapshot


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "stt:\n  enabled: true\n  provider: local\n  local:\n    model: base\n"
        "voice:\n  max_recording_seconds: 120\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KEPRIX_CONFIG", str(config_path))
    # Point load/save_config at this file when possible
    monkeypatch.setattr(
        "keprix_cli.config.get_config_path",
        lambda: config_path,
        raising=False,
    )


def test_voice_settings_snapshot_and_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Prefer direct save/load patch for reliability across config helpers
    state = {
        "stt": {"enabled": True, "provider": "local", "local": {"model": "base", "language": ""}},
        "voice": {"max_recording_seconds": 120, "auto_tts": False, "beep_enabled": True},
    }

    def load_config():
        return state

    def save_config(cfg):
        state.clear()
        state.update(cfg)

    monkeypatch.setattr("keprix_cli.config.load_config", load_config)
    monkeypatch.setattr("keprix_cli.config.save_config", save_config)
    monkeypatch.setattr("keprix.api.voice_settings.persist_env_value", lambda *a, **k: None)
    monkeypatch.setattr("keprix.api.voice_settings.remove_env_value", lambda *a, **k: None)
    monkeypatch.setattr("keprix.api.stt_config._load_config", load_config)

    snap = voice_settings_snapshot()
    assert snap["enabled"] is True
    assert snap["configured_provider"] == "local"
    assert any(item["id"] == "groq" for item in snap["catalog"])

    updated = update_voice_settings(
        {
            "enabled": True,
            "provider": "groq",
            "maxRecordingSeconds": 90,
            "groqModel": "whisper-large-v3",
        }
    )
    assert updated["configured_provider"] == "groq"
    assert updated["max_recording_seconds"] == 90
    assert state["stt"]["provider"] == "groq"
    assert state["voice"]["max_recording_seconds"] == 90

    with pytest.raises(ValueError):
        update_voice_settings({"provider": "not-a-provider"})
