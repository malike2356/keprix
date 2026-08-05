"""Tests for TUI voice capture helpers (Prompt 206)."""

from __future__ import annotations

import base64

import pytest

from keprix.tui.voice import VoiceCaptureError, VoiceRecorder, voice_backend_available


def test_voice_backend_available_without_deps(monkeypatch) -> None:
    monkeypatch.setattr("keprix.tui.voice.shutil.which", lambda _name: None)
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", None)
    assert voice_backend_available() is False


def test_voice_recorder_start_requires_backend(monkeypatch) -> None:
    monkeypatch.setattr("keprix.tui.voice._sounddevice_ready", lambda: False)
    monkeypatch.setattr("keprix.tui.voice.shutil.which", lambda _name: None)
    recorder = VoiceRecorder()
    with pytest.raises(VoiceCaptureError):
        recorder.start()


def test_encode_wav_roundtrip(monkeypatch, tmp_path) -> None:
    fake = tmp_path / "arecord"
    fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake.chmod(0o755)

    class _Proc:
        def terminate(self) -> None:
            return None

        def wait(self, timeout=None) -> int:
            _ = timeout
            return 0

    recorder = VoiceRecorder()
    recorder._recording = True
    recorder._process = _Proc()
    wav_path = tmp_path / "sample.wav"
    wav_path.write_bytes(b"RIFFxxxxWAVEfmt ")
    recorder._temp_path = str(wav_path)

    result = recorder._stop_subprocess()
    assert result.mime_type == "audio/wav"
    assert result.data_url.startswith("data:audio/wav;base64,")
    payload = result.data_url.split(",", 1)[1]
    assert base64.b64decode(payload) == b"RIFFxxxxWAVEfmt "


@pytest.mark.asyncio
async def test_transcribe_client_contract() -> None:
    class _Client:
        async def transcribe_audio(self, data_url: str, *, mime_type: str) -> str:
            assert data_url.startswith("data:audio/wav;base64,")
            assert mime_type == "audio/wav"
            return "hello world"

    client = _Client()
    text = await client.transcribe_audio("data:audio/wav;base64,abcd", mime_type="audio/wav")
    assert text == "hello world"
