"""Web voice chat composer surface guards."""

from __future__ import annotations

from pathlib import Path

from keprix.ui_contract import build_ui_contract

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"


def test_chat_input_bar_imports_voice_recorder_hook() -> None:
    source = (FRONTEND / "components" / "workspace" / "ChatInputBar.tsx").read_text(encoding="utf-8")
    assert "useWebVoiceRecorder" in source


def test_audio_api_client_exists() -> None:
    assert (FRONTEND / "lib" / "audio-api.ts").is_file()


def test_voice_settings_page_exists() -> None:
    assert (FRONTEND / "app" / "(workspace)" / "settings" / "voice" / "page.tsx").is_file()


def test_ui_contract_voice_input_follows_stt_enabled(monkeypatch) -> None:
    monkeypatch.setattr("keprix.ui_contract.stt_enabled", lambda: True)
    assert build_ui_contract({"role": "user"})["feature_flags"]["voice_input"] is True
    monkeypatch.setattr("keprix.ui_contract.stt_enabled", lambda: False)
    assert build_ui_contract({"role": "user"})["feature_flags"]["voice_input"] is False
